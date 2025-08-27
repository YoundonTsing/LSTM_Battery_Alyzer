import os
import json
import time
import asyncio
import logging
import uuid
import shutil
import zipfile
import subprocess
from pathlib import Path as SysPath
import sys
from concurrent.futures import ThreadPoolExecutor
import socketio
import uvicorn
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Path, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# 导入配置和模型
from config import SERVER_HOST, SERVER_PORT, WEBSOCKET_CONFIG, SIMULATOR_CONFIG
from models.battery_model import BatteryModel
from models.rul_model import BatteryRULModel
from models.cnn_lstm_rul_model import CNNLSTM_RULModel
from models.database import (
    init_db, get_all_charging_records, get_charging_record_by_id,
    get_recent_charging_records, get_charging_records_by_date_range,
    search_charging_records, delete_charging_record, delete_charging_records_by_ids,
    delete_all_charging_records, get_charging_statistics, get_charging_phases_statistics,
    export_charging_records_to_json, import_charging_records_from_json,
    update_all_charging_record_durations
)

# 设置更详细的日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("battery-simulator")

# 创建控制台处理器，增加日志可见性
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# 记录服务器启动信息
logger.info("=========== 电池充电仿真模拟器启动 ===========")
logger.info(f"服务器配置: 主机={SERVER_HOST}, 端口={SERVER_PORT}")

# 创建FastAPI应用
app = FastAPI(title="电池充电仿真模拟器后端")

# 配置允许的源
ALLOWED_ORIGINS = [
    "http://localhost:5111",  # Vue dev server
    "http://localhost:3000",  # 可能的其他前端端口
    "http://127.0.0.1:5111",
    "http://127.0.0.1:3000"
]

# 自定义CORS中间件，避免处理Socket.IO路径
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 如果是Socket.IO相关路径，跳过CORS处理
        if request.url.path.startswith("/ws"):
            return await call_next(request)
        
        # 检查是否是预检请求
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:5111"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        # 处理正常请求
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:5111"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

# 添加自定义CORS中间件
app.add_middleware(CustomCORSMiddleware)
logger.info("CORS中间件已配置")

# 创建Socket.IO服务器 - 重新启用CORS但避免与FastAPI冲突
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ALLOWED_ORIGINS,  # 使用相同的来源列表
    cors_credentials=True,
    ping_interval=WEBSOCKET_CONFIG["ping_interval"],
    ping_timeout=WEBSOCKET_CONFIG["ping_timeout"]
)
logger.info(f"Socket.IO服务器已配置: ping_interval={WEBSOCKET_CONFIG['ping_interval']}, ping_timeout={WEBSOCKET_CONFIG['ping_timeout']}")

# 将Socket.IO应用与FastAPI集成
socket_app = socketio.ASGIApp(sio, app, socketio_path='ws')

# 电池模型和RUL模型
battery_model = BatteryModel()
rul_model = BatteryRULModel()
cnn_lstm_rul_model = CNNLSTM_RULModel()
logger.info("电池模型和RUL模型已初始化")

# 初始化数据库
init_db()

# 更新所有充电记录的时长
updated_count = update_all_charging_record_durations()
logger.info(f"启动时更新了 {updated_count} 条充电记录的时长")

# 创建电池模型实例
battery_model = BatteryModel()

# 连接的客户端
connected_clients = {}

# 模拟器状态
simulator_running = False
simulator_task = None

# 历史数据收集
battery_history = []
MAX_HISTORY_LENGTH = 1000  # 最大历史数据长度
logger.info(f"历史数据最大长度设置为: {MAX_HISTORY_LENGTH}")

# 数据类型转换函数，解决numpy.float32等类型无法JSON序列化的问题
def convert_numpy_types(obj):
    """递归转换NumPy类型为Python原生类型，解决JSON序列化问题"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif hasattr(obj, 'item'):  # NumPy scalar types have .item() method
        return obj.item()  # Convert numpy scalar to Python scalar
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy array to Python list
    elif hasattr(obj, 'numpy'):  # TensorFlow tensor
        return obj.numpy().tolist()
    else:
        return obj

# =============================
# 训练作业管理与后台执行
# =============================

# 作业状态存储
train_jobs: Dict[str, Dict[str, Any]] = {}

# 线程池用于后台训练，避免阻塞事件循环
executor = ThreadPoolExecutor(max_workers=1)

# 路径常量
PROJECT_ROOT = SysPath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
RUL_ROOT = PROJECT_ROOT / "RUL_prediction"
RUL_DATA_DIR = RUL_ROOT / "data"
RUL_NASA_DIR = RUL_DATA_DIR / "NASA"
RUL_UPLOADS_DIR = RUL_DATA_DIR / "uploads"
RUL_SAVED_DIR = RUL_ROOT / "saved" / "fusion" / "new_prep"
BACKEND_MODELS_DIR = SysPath(os.path.abspath(os.path.join(os.path.dirname(__file__), "models")))

def _safe_mkdir(p: SysPath):
    p.mkdir(parents=True, exist_ok=True)

def _extract_zip_to(zip_file: SysPath, target_dir: SysPath):
    _safe_mkdir(target_dir)
    with zipfile.ZipFile(zip_file, 'r') as zf:
        zf.extractall(target_dir)

def _copytree(src: SysPath, dst: SysPath):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def _ensure_dir(p: SysPath):
    p.mkdir(parents=True, exist_ok=True)

def _normalize_nasa_layout(nasa_root: SysPath):
    """Ensure dataset layout matches RUL scripts expectation:
    NASA/
      charge/train/*.csv
      charge/test/*.csv
      discharge/train/*.csv
      discharge/test/*.csv
    If CSV files are directly under charge/ or discharge/, split by battery id: last id -> test, others -> train.
    """
    charge_dir = nasa_root / "charge"
    discharge_dir = nasa_root / "discharge"
    # 如果缺少目录，尝试从任意层级聚合CSV到标准结构
    if not charge_dir.exists() and not discharge_dir.exists():
        # 收集所有CSV
        all_csv = list(nasa_root.rglob('*.csv')) + list(nasa_root.rglob('*.CSV'))
        if all_csv:
            _ensure_dir(charge_dir)
            _ensure_dir(discharge_dir)
            def classify_csv_by_header(fp: SysPath) -> str:
                try:
                    with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as fh:
                        header = fh.readline().strip().lower()
                except Exception:
                    header = ''
                # 判定
                if any(k in header for k in ['voltage_battery', 'current_battery', 'temp_battery']):
                    return 'charge'
                if 'capacity' in header:
                    return 'discharge'
                # 回退：根据文件名
                name = fp.name.lower()
                if 'charge' in name:
                    return 'charge'
                if 'discharge' in name:
                    return 'discharge'
                return 'unknown'

            for f in all_csv:
                cls = classify_csv_by_header(f)
                if cls == 'charge':
                    shutil.move(str(f), str(charge_dir / f.name))
                elif cls == 'discharge':
                    shutil.move(str(f), str(discharge_dir / f.name))
            # 清理空目录（可选）
        else:
            # 无法规范化，保持原样
            pass

    charge_train = charge_dir / "train"
    charge_test = charge_dir / "test"
    discharge_train = discharge_dir / "train"
    discharge_test = discharge_dir / "test"
    for d in [charge_train, charge_test, discharge_train, discharge_test]:
        _ensure_dir(d)

    # If there are CSVs directly under charge/ or discharge/, split them
    direct_charge = list(charge_dir.glob("*.csv")) + list(charge_dir.glob("*.CSV"))
    direct_discharge = list(discharge_dir.glob("*.csv")) + list(discharge_dir.glob("*.CSV"))
    if direct_charge or direct_discharge:
        # Derive battery ids from filenames like B0005_charge.csv / B0005_discharge.csv
        ids = set()
        for f in direct_charge:
            name = f.name
            if "_" in name:
                ids.add(name.split("_")[0])
        for f in direct_discharge:
            name = f.name
            if "_" in name:
                ids.add(name.split("_")[0])
        if ids:
            sorted_ids = sorted(ids)
            # put last id into test, others into train
            test_ids = {sorted_ids[-1]}
            train_ids = set(sorted_ids[:-1]) if len(sorted_ids) > 1 else set()

            # Move files accordingly
            for f in direct_charge:
                bid = f.name.split("_")[0] if "_" in f.name else None
                if bid in test_ids:
                    shutil.move(str(f), str(charge_test / f.name))
                else:
                    shutil.move(str(f), str(charge_train / f.name))
            for f in direct_discharge:
                bid = f.name.split("_")[0] if "_" in f.name else None
                if bid in test_ids:
                    shutil.move(str(f), str(discharge_test / f.name))
                else:
                    shutil.move(str(f), str(discharge_train / f.name))

    # 若仍旧没有任何train/test文件，但存在子目录中的csv，做一次递归搬运
    if not any(charge_train.glob('*.csv')) and list(charge_dir.rglob('*.csv')):
        # 将所有非 train/test 下的CSV移动到 charge 根，再按上面的逻辑分配
        for f in charge_dir.rglob('*.csv'):
            if f.parent.name not in ("train", "test"):
                shutil.move(str(f), str(charge_dir / f.name))
        # 重新分配
        direct_charge = list(charge_dir.glob('*.csv')) + list(charge_dir.glob('*.CSV'))
        if direct_charge:
            ids = sorted({f.name.split('_')[0] for f in direct_charge if '_' in f.name})
            test_ids = {ids[-1]} if ids else set()
            for f in direct_charge:
                bid = f.name.split('_')[0] if '_' in f.name else None
                dst = charge_test if bid in test_ids else charge_train
                shutil.move(str(f), str(dst / f.name))

    if not any(discharge_train.glob('*.csv')) and list(discharge_dir.rglob('*.csv')):
        for f in discharge_dir.rglob('*.csv'):
            if f.parent.name not in ("train", "test"):
                shutil.move(str(f), str(discharge_dir / f.name))
        direct_discharge = list(discharge_dir.glob('*.csv')) + list(discharge_dir.glob('*.CSV'))
        if direct_discharge:
            ids = sorted({f.name.split('_')[0] for f in direct_discharge if '_' in f.name})
            test_ids = {ids[-1]} if ids else set()
            for f in direct_discharge:
                bid = f.name.split('_')[0] if '_' in f.name else None
                dst = discharge_test if bid in test_ids else discharge_train
                shutil.move(str(f), str(dst / f.name))

async def _emit_progress(job_id: str, message: str, progress: int = None):
    payload = {"jobId": job_id, "message": message}
    if progress is not None:
        payload["progress"] = progress
    await sio.emit('train_progress', payload)

def _find_trained_models() -> List[SysPath]:
    if not RUL_SAVED_DIR.exists():
        return []
    found: List[SysPath] = []
    for root, _, files in os.walk(RUL_SAVED_DIR):
        for f in files:
            if f.endswith('.keras'):
                found.append(SysPath(root) / f)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found

def _activate_latest_models(max_k: int = 3) -> int:
    models = _find_trained_models()
    if not models:
        return 0
    _safe_mkdir(BACKEND_MODELS_DIR)
    count = 0
    for mpath in models:
        if count >= max_k:
            break
        target = BACKEND_MODELS_DIR / f"cnn_lstm_rul_model_k{count+1}.keras"
        try:
            shutil.copy2(mpath, target)
            count += 1
        except Exception as e:
            logger.error(f"复制模型失败: {mpath} -> {target}: {e}")
    try:
        cnn_lstm_rul_model._load_or_create_model()
    except Exception as e:
        logger.error(f"重载在线RUL模型失败: {e}")
    return count

def _run_training_job(job_id: str, dataset_dir: SysPath, hyper: Dict[str, Any]):
    start_ts = time.time()
    try:
        train_jobs[job_id]["status"] = "running"
        # 直接使用上传数据目录（若存在unzipped优先）
        candidate_dir = dataset_dir / "unzipped" if (dataset_dir / "unzipped").exists() else dataset_dir

        # 启动训练子进程
        script = str(RUL_ROOT / "train" / "SC-CNN+LSTM.py")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # 确保子进程使用与后端相同的解释器与模块搜索路径
        py_exe = sys.executable or "python"
        # 追加 PYTHONPATH，帮助脚本内的相对导入
        add_paths = [str(RUL_ROOT), str(RUL_ROOT / "train")]
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([p for p in [existing_pp] + add_paths if p])
        # 传递数据集目录
        env["DATASET_DIR"] = str(candidate_dir)
        proc = subprocess.Popen(
            [py_exe, script],
            cwd=str(RUL_ROOT / "train"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )

        # 读取stdout并通过事件循环推送进度
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode(errors='ignore').rstrip()
            try:
                loop.run_until_complete(_emit_progress(job_id, line))
            except Exception:
                pass
        code = proc.wait()
        if code != 0:
            train_jobs[job_id]["status"] = "failed"
            train_jobs[job_id]["error"] = f"trainer exit code {code}"
            try:
                loop.run_until_complete(sio.emit('train_completed', {"jobId": job_id, "success": False, "error": train_jobs[job_id]["error"]}))
            except Exception:
                pass
            return

        cnt = _activate_latest_models(max_k=3)
        train_jobs[job_id]["status"] = "completed"
        train_jobs[job_id]["modelCount"] = cnt
        train_jobs[job_id]["durationSec"] = int(time.time() - start_ts)
        try:
            loop.run_until_complete(sio.emit('train_completed', {"jobId": job_id, "success": True, "modelCount": cnt, "durationSec": train_jobs[job_id]["durationSec"]}))
        except Exception:
            pass
    except Exception as e:
        train_jobs[job_id]["status"] = "failed"
        train_jobs[job_id]["error"] = str(e)
        logger.error(f"训练作业失败: {e}", exc_info=True)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(sio.emit('train_completed', {"jobId": job_id, "success": False, "error": str(e)}))
        except Exception:
            pass

# REST API 的数据模型
class SearchParams(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_soc: Optional[float] = None
    max_soc: Optional[float] = None
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0

# =============================
# 后端API: 上传/触发训练/查询状态
# =============================

class TrainRequest(BaseModel):
    datasetId: str
    k: Optional[int] = None
    epochs: Optional[int] = None
    batchSize: Optional[int] = None

@app.post("/api/rul/dataset/upload")
async def upload_dataset(datasetId: str = Form(...), file: UploadFile = File(...)):
    """上传数据集（建议提供包含 NASA 目录结构的 zip）。"""
    try:
        ds_root = RUL_UPLOADS_DIR / datasetId
        ds_root.mkdir(parents=True, exist_ok=True)
        tmp_path = ds_root / file.filename
        with open(tmp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        target_dir = ds_root
        lower_name = str(tmp_path).lower()
        if lower_name.endswith('.zip'):
            target_dir = ds_root / "unzipped"
            _extract_zip_to(tmp_path, target_dir)
        elif lower_name.endswith('.7z'):
            # 尝试解压 7z
            try:
                import py7zr  # type: ignore
            except Exception:
                raise HTTPException(status_code=400, detail="缺少对7z的支持，请先在后端安装: pip install py7zr")
            target_dir = ds_root / "unzipped"
            _safe_mkdir(target_dir)
            try:
                with py7zr.SevenZipFile(tmp_path, mode='r') as z:
                    z.extractall(path=target_dir)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"解压7z失败: {e}")
        return {"datasetId": datasetId, "storedAt": str(target_dir)}
    except Exception as e:
        logger.error(f"上传数据集失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/rul/train")
async def trigger_train(req: TrainRequest):
    ds_dir = RUL_UPLOADS_DIR / req.datasetId
    if (ds_dir / "unzipped").exists():
        ds_dir = ds_dir / "unzipped"
    if not ds_dir.exists():
        raise HTTPException(status_code=404, detail=f"datasetId {req.datasetId} not found")
    job_id = uuid.uuid4().hex
    train_jobs[job_id] = {"status": "queued", "datasetId": req.datasetId, "createdAt": int(time.time())}
    hyper = {"k": req.k, "epochs": req.epochs, "batch": req.batchSize}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_training_job, job_id, ds_dir, hyper)
    await _emit_progress(job_id, "job queued", 0)
    return {"jobId": job_id, "status": "queued"}

@app.get("/api/rul/train/{jobId}/status")
async def train_status(jobId: str):
    job = train_jobs.get(jobId)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job

# REST API 端点
@app.get("/api/charging-records", response_model=Dict)
async def api_get_charging_records(
    limit: int = Query(10, description="返回记录的最大数量"),
    offset: int = Query(0, description="分页偏移量")
):
    """获取充电记录，带分页功能"""
    logger.info(f"REST API: 获取充电记录，limit={limit}, offset={offset}")
    search_result = search_charging_records({"limit": limit, "offset": offset})
    return search_result

@app.get("/api/status", response_model=Dict)
async def api_status():
    """提供当前后端状态，供前端获取RUL开关与时间加速等。"""
    try:
        # 获取基本电池状态
        battery_state = battery_model.get_state()
        
        # 生成完整的电池状态信息（包括健康信息和充电优化）
        battery_state = await _generate_complete_battery_state(battery_state)
        
        # 检查模型可用性和数量
        model_available = False
        model_count = 0
        try:
            if hasattr(cnn_lstm_rul_model, 'models') and cnn_lstm_rul_model.models:
                model_available = True
                model_count = len(cnn_lstm_rul_model.models)
            elif hasattr(cnn_lstm_rul_model, 'is_trained') and cnn_lstm_rul_model.is_trained:
                model_available = True
                model_count = 1
        except Exception:
            model_available = False
            model_count = 0
            
        status = {
            "battery_state": convert_numpy_types(battery_state),
            "time_acceleration_factor": SIMULATOR_CONFIG.get("time_acceleration_factor", 1),
            "rul_model_available": model_available,
            "rul_model_count": model_count,
            "simulator_running": simulator_running,
            "connected_clients_count": len(connected_clients)
        }
        return status
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charging-records/recent", response_model=List)
async def api_get_recent_charging_records(
    limit: int = Query(10, description="返回记录的最大数量")
):
    """获取最近的充电记录"""
    logger.info(f"REST API: 获取最近{limit}条充电记录")
    records = get_recent_charging_records(limit)
    return records

@app.get("/api/charging-records/{record_id}", response_model=Dict)
async def api_get_charging_record_by_id(
    record_id: int = Path(..., description="充电记录ID")
):
    """根据ID获取单条充电记录"""
    logger.info(f"REST API: 获取充电记录 ID={record_id}")
    record = get_charging_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"充电记录 ID {record_id} 不存在")
    return record

@app.post("/api/charging-records/search", response_model=Dict)
async def api_search_charging_records(search_params: SearchParams):
    """搜索充电记录"""
    logger.info(f"REST API: 搜索充电记录，参数: {search_params}")
    search_result = search_charging_records(search_params.dict())
    return search_result

@app.delete("/api/charging-records/{record_id}", response_model=Dict)
async def api_delete_charging_record(
    record_id: int = Path(..., description="要删除的充电记录ID")
):
    """删除单条充电记录"""
    logger.info(f"REST API: 删除充电记录 ID={record_id}")
    success = delete_charging_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"充电记录 ID {record_id} 不存在或删除失败")
    
    # 广播更新，通知所有客户端充电记录已更改
    await broadcast_charging_records()
    
    return {"success": True, "message": f"已删除充电记录 ID: {record_id}"}

@app.delete("/api/charging-records", response_model=Dict)
async def api_delete_charging_records(
    record_ids: List[int] = Body(..., description="要删除的充电记录ID列表")
):
    """批量删除充电记录"""
    logger.info(f"REST API: 批量删除充电记录，IDs={record_ids}")
    deleted_count = delete_charging_records_by_ids(record_ids)
    
    # 广播更新，通知所有客户端充电记录已更改
    await broadcast_charging_records()
    
    return {"success": True, "message": f"已删除 {deleted_count} 条充电记录", "deleted_count": deleted_count}

@app.delete("/api/charging-records/all", response_model=Dict)
async def api_delete_all_charging_records():
    """删除所有充电记录"""
    logger.info(f"REST API: 删除所有充电记录")
    success = delete_all_charging_records()
    if not success:
        raise HTTPException(status_code=500, detail="删除所有充电记录失败")
    
    # 广播更新，通知所有客户端充电记录已更改
    await broadcast_charging_records()
    
    return {"success": True, "message": "已删除所有充电记录"}

@app.get("/api/charging-statistics", response_model=Dict)
async def api_get_charging_statistics():
    """获取充电统计信息"""
    logger.info(f"REST API: 获取充电统计信息")
    statistics = get_charging_statistics()
    return statistics

@app.get("/api/charging-phases-statistics", response_model=Dict)
async def api_get_charging_phases_statistics():
    """获取充电阶段统计信息"""
    logger.info(f"REST API: 获取充电阶段统计信息")
    statistics = get_charging_phases_statistics()
    return statistics

@app.get("/api/charging-records/export", response_model=Dict)
async def api_export_charging_records_to_json(
    record_ids: Optional[List[int]] = Body(None, description="要导出的充电记录ID列表，留空导出所有")
):
    """导出充电记录到JSON文件"""
    logger.info(f"REST API: 导出充电记录到JSON，IDs={record_ids}")
    file_path = f"exports/charging_records_{int(time.time())}.json"
    success = export_charging_records_to_json(file_path, record_ids)
    if not success:
        raise HTTPException(status_code=500, detail="导出充电记录失败")
    return {"success": True, "file_path": file_path}

@app.post("/api/charging-records/import", response_model=Dict)
async def api_import_charging_records_from_json(
    file_path: str = Body(..., description="要导入的JSON文件路径")
):
    """从JSON文件导入充电记录"""
    logger.info(f"REST API: 从 {file_path} 导入充电记录")
    result = import_charging_records_from_json(file_path)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"导入充电记录失败: {result.get('message', '未知错误')}")
    await broadcast_charging_records()
    return result

@app.post("/api/simulator/time-acceleration")
async def set_time_acceleration(acceleration_factor: float = Body(..., description="时间加速因子，1.0表示实时，大于1表示加速")):
    """设置模拟器时间加速因子"""
    if acceleration_factor <= 0:
        raise HTTPException(status_code=400, detail="时间加速因子必须大于0")
    
    # 更新配置
    SIMULATOR_CONFIG["time_acceleration_factor"] = acceleration_factor
    logger.info(f"设置时间加速因子为: {acceleration_factor}")
    
    return {"success": True, "message": f"时间加速因子已设置为 {acceleration_factor}", "time_acceleration_factor": acceleration_factor}

@app.post("/api/simulator/rul-optimization")
async def set_rul_optimization(enable: bool = Body(..., description="是否启用RUL优化充电")):
    """设置RUL优化充电功能
    
    参数:
        enable: 是否启用RUL优化充电
    
    返回:
        dict: 包含操作结果和当前状态
    """
    global battery_model
    
    try:
        # 检查模型是否可用
        if enable:
            # 验证CNN+LSTM模型是否可用
            if not hasattr(cnn_lstm_rul_model, "predict_rul") or not callable(getattr(cnn_lstm_rul_model, "predict_rul")):
                return {
                    "success": False, 
                    "message": "RUL预测模型不可用，无法启用优化充电", 
                    "rul_optimized_charging": False
                }
        
        # 设置优化充电状态
        battery_model.rul_optimized_charging = enable
        logger.info(f"RUL优化充电已{'启用' if enable else '禁用'}")
        
        return {
            "success": True,
            "message": f"RUL优化充电已{'启用' if enable else '禁用'}",
            "rul_optimized_charging": battery_model.rul_optimized_charging
        }
    except Exception as e:
        logger.error(f"设置RUL优化充电失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"设置失败: {str(e)}",
            "rul_optimized_charging": battery_model.rul_optimized_charging
        }

@app.post("/api/rul-optimization/enable")
async def enable_rul_optimization():
    """启用RUL优化充电 - 测试兼容性API"""
    try:
        battery_model.rul_optimized_charging = True
        logger.info("RUL优化充电已启用")
        return {
            "success": True,
            "message": "RUL优化充电已启用",
            "rul_optimized_charging": True
        }
    except Exception as e:
        logger.error(f"启用RUL优化充电失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"启用失败: {str(e)}",
            "rul_optimized_charging": battery_model.rul_optimized_charging
        }

@app.post("/api/charge/start")
async def start_charging_api():
    """开始充电 - REST API"""
    try:
        record_id = battery_model.start_charging()
        if record_id:
            logger.info(f"充电已开始，记录ID: {record_id}")
            return {
                "success": True,
                "message": "充电已开始",
                "charging_record_id": record_id
            }
        else:
            return {
                "success": False,
                "message": "启动充电失败"
            }
    except Exception as e:
        logger.error(f"启动充电失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"启动充电失败: {str(e)}"
        }

@app.post("/api/charge/stop")
async def stop_charging_api():
    """停止充电 - REST API"""
    try:
        success = battery_model.stop_charging()
        if success:
            logger.info("充电已停止")
            return {
                "success": True,
                "message": "充电已停止"
            }
        else:
            return {
                "success": False,
                "message": "停止充电失败，可能当前未在充电"
            }
    except Exception as e:
        logger.error(f"停止充电失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"停止充电失败: {str(e)}"
        }

@app.get("/")
async def root():
    """根路径处理函数"""
    logger.info("访问根路径API")
    return {"message": "电池充电仿真模拟器后端API"}

@app.get("/api/status")
async def get_status():
    """获取服务器状态"""
    logger.info("获取服务器状态API被调用")
    status = {
        "status": "running",
        "connected_clients": len(connected_clients),
        "simulator_running": simulator_running,
        "battery_state": battery_model.get_state(),
        "time_acceleration_factor": SIMULATOR_CONFIG["time_acceleration_factor"]
    }
    logger.info(f"当前状态: 连接客户端数={len(connected_clients)}, 模拟器运行状态={simulator_running}")
    return status

@sio.event
async def connect(sid, environ):
    """处理客户端连接"""
    logger.info(f"新客户端连接: {sid}")
    logger.info(f"客户端环境信息: {environ.get('HTTP_USER_AGENT', '未知')}")
    
    connected_clients[sid] = {
        "connected_time": time.time(),
        "last_activity": time.time()
    }
    logger.info(f"当前连接客户端数量: {len(connected_clients)}")
    
    # 发送当前电池状态（包含完整的健康信息和充电优化）
    await broadcast_battery_state(sid)
    
    # 发送充电记录
    await broadcast_charging_records(sid)
    logger.info(f"已发送充电记录到客户端 {sid}")
    
    # 启动模拟器
    await ensure_simulator_running()
    logger.info("确保模拟器运行")

@sio.event
async def disconnect(sid):
    """处理客户端断开连接"""
    logger.info(f"客户端断开连接: {sid}")
    if sid in connected_clients:
        connection_time = time.time() - connected_clients[sid]["connected_time"]
        logger.info(f"客户端 {sid} 连接时长: {connection_time:.2f}秒")
        del connected_clients[sid]
        logger.info(f"剩余连接客户端数量: {len(connected_clients)}")
    
    # 如果没有客户端连接，停止模拟器
    if not connected_clients and simulator_running:
        logger.info("没有客户端连接，准备停止模拟器")
        await stop_simulator()

@sio.event
async def message(sid, data):
    """处理客户端消息"""
    try:
        # 更新客户端活动时间
        if sid in connected_clients:
            connected_clients[sid]["last_activity"] = time.time()
        
        # 解析消息
        if isinstance(data, str):
            data = json.loads(data)
            logger.info(f"解析客户端JSON消息: {data}")
        
        action = data.get('action')
        logger.info(f"收到客户端 {sid} 的操作请求: {action}")
        
        # 处理不同类型的消息
        if action == 'start_charging':
            # 开始充电
            logger.info(f"客户端 {sid} 请求开始充电")
            record_id = battery_model.start_charging()
            if record_id:
                logger.info(f"充电已开始，记录ID: {record_id}")
                await broadcast_battery_state()
            else:
                logger.warning("启动充电失败")

        elif action == 'start_discharging':
            # 开始放电
            logger.info(f"客户端 {sid} 请求开始放电")
            battery_model.start_discharging()
            logger.info(f"放电已开始: 初始SOC={battery_model.get_state()['soc']}%")
            await broadcast_battery_state()
            
        elif action == 'stop':
            # 停止充放电
            logger.info(f"客户端 {sid} 请求停止充放电")
            
            if battery_model.is_charging:
                battery_model.stop_charging()
                logger.info("充电已停止")
            elif battery_model.is_discharging:
                battery_model.stop_discharging()
                logger.info("放电已停止")
            else:
                logger.info("电池当前未处于充电或放电状态")
                
            await broadcast_battery_state()
            await broadcast_charging_records()
            
        elif action == 'update_params':
            # 更新参数
            params = data.get('params', {})
            logger.info(f"客户端 {sid} 请求更新参数: {params}")
            
            # 处理时间加速因子设置
            if 'time_acceleration_factor' in params:
                acceleration_factor = params.pop('time_acceleration_factor')
                if acceleration_factor > 0:
                    SIMULATOR_CONFIG["time_acceleration_factor"] = acceleration_factor
                    logger.info(f"时间加速因子已设置为: {acceleration_factor}")
            
            # 处理 RUL 优化充电设置
            if 'rul_optimized_charging' in params:
                rul_optimized = params.pop('rul_optimized_charging')
                battery_model.rul_optimized_charging = rul_optimized
                logger.info(f"RUL 优化充电已{'启用' if rul_optimized else '禁用'}")
            
            # 更新其他参数
            if params:
                battery_model.update_params(params)
                logger.info("电池参数已更新")
            
            await broadcast_battery_state()
            
        elif action == 'get_charging_records':
            # 获取充电记录
            logger.info(f"客户端 {sid} 请求充电记录")
            await broadcast_charging_records(sid)
            
        elif action == 'reset':
            # 重置电池
            logger.info(f"客户端 {sid} 请求重置电池")
            battery_model.reset()
            logger.info("电池已重置")
            await broadcast_battery_state()
            
        # 添加充电记录相关的消息处理
        elif action == 'get_charging_record_by_id':
            # 获取单条充电记录
            record_id = data.get('record_id')
            logger.info(f"客户端 {sid} 请求充电记录 ID={record_id}")
            record = get_charging_record_by_id(record_id)
            await sio.emit('charging_record', convert_numpy_types(record), room=sid)
            
        elif action == 'get_recent_charging_records':
            # 获取最近充电记录
            limit = data.get('limit', 10)
            logger.info(f"客户端 {sid} 请求最近 {limit} 条充电记录")
            records = get_recent_charging_records(limit)
            await sio.emit('charging_records', convert_numpy_types(records), room=sid)
            
        elif action == 'get_charging_records_by_date_range':
            # 按日期范围获取充电记录
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            logger.info(f"客户端 {sid} 请求日期范围 {start_date} 至 {end_date} 的充电记录")
            records = get_charging_records_by_date_range(start_date, end_date)
            await sio.emit('charging_records', convert_numpy_types(records), room=sid)
            
        elif action == 'search_charging_records':
            # 搜索充电记录
            search_params = data.get('search_params', {})
            request_id = data.get('request_id', None)
            logger.info(f"客户端 {sid} 搜索充电记录: {search_params}, 请求ID: {request_id}")
            
            try:
                search_result = search_charging_records(search_params)
                logger.info(f"搜索结果: 找到 {search_result.get('total_count', 0)} 条记录")
                
                # 添加请求ID到结果中，帮助前端匹配请求和响应
                if request_id:
                    search_result['request_id'] = request_id
                
                await sio.emit('charging_records_search_result', convert_numpy_types(search_result), room=sid)
                logger.info(f"已发送搜索结果到客户端 {sid}")
            except Exception as e:
                logger.error(f"搜索充电记录时出错: {e}", exc_info=True)
                error_result = {
                    "error": str(e),
                    "request_id": request_id,
                    "records": [],
                    "total_count": 0
                }
                await sio.emit('charging_records_search_result', error_result, room=sid)
                logger.info(f"已发送错误结果到客户端 {sid}")
            
        elif action == 'delete_charging_record':
            # 删除单条充电记录
            record_id = data.get('record_id')
            logger.info(f"客户端 {sid} 请求删除充电记录 ID={record_id}")
            success = delete_charging_record(record_id)
            await broadcast_charging_records()
            await sio.emit('charging_record_deleted', {"success": success, "record_id": record_id}, room=sid)
            
        elif action == 'delete_charging_records_by_ids':
            # 批量删除充电记录
            record_ids = data.get('record_ids', [])
            logger.info(f"客户端 {sid} 请求批量删除充电记录: {record_ids}")
            deleted_count = delete_charging_records_by_ids(record_ids)
            await broadcast_charging_records()
            await sio.emit('charging_records_deleted', {"success": True, "deleted_count": deleted_count}, room=sid)
            
        elif action == 'delete_all_charging_records':
            # 删除所有充电记录
            logger.info(f"客户端 {sid} 请求删除所有充电记录")
            success = delete_all_charging_records()
            await broadcast_charging_records()
            await sio.emit('all_charging_records_deleted', {"success": success}, room=sid)
            
        elif action == 'get_charging_statistics':
            # 获取充电统计信息
            logger.info(f"客户端 {sid} 请求充电统计信息")
            statistics = get_charging_statistics()
            await sio.emit('charging_statistics', convert_numpy_types(statistics), room=sid)
            
        elif action == 'get_charging_phases_statistics':
            # 获取充电阶段统计信息
            logger.info(f"客户端 {sid} 请求充电阶段统计信息")
            statistics = get_charging_phases_statistics()
            await sio.emit('charging_phases_statistics', convert_numpy_types(statistics), room=sid)
            
        elif action == 'export_charging_records_to_json':
            # 导出充电记录
            record_ids = data.get('record_ids')
            file_path = f"exports/charging_records_{int(time.time())}.json"
            logger.info(f"客户端 {sid} 请求导出充电记录: {record_ids}")
            success = export_charging_records_to_json(file_path, record_ids)
            await sio.emit('charging_records_exported', {"success": success, "file_path": file_path}, room=sid)
            
        elif action == 'import_charging_records_from_json':
            # 导入充电记录
            file_path = data.get('file_path')
            logger.info(f"客户端 {sid} 请求从 {file_path} 导入充电记录")
            result = import_charging_records_from_json(file_path)
            await broadcast_charging_records()
            await sio.emit('charging_records_imported', convert_numpy_types(result), room=sid)
        
        elif action == 'set_rul_optimization':
            # 设置RUL优化充电
            enable = data.get('enable', False)
            request_id = data.get('request_id')
            logger.info(f"客户端 {sid} 请求{'启用' if enable else '禁用'}RUL优化充电")
            
            try:
                # 检查模型是否可用
                if enable:
                    # 验证CNN+LSTM模型是否可用
                    if not hasattr(cnn_lstm_rul_model, "predict_rul") or not callable(getattr(cnn_lstm_rul_model, "predict_rul")):
                        response = {
                            "success": False, 
                            "message": "RUL预测模型不可用，无法启用优化充电", 
                            "rul_optimized_charging": False,
                            "request_id": request_id
                        }
                        await sio.emit('rul_optimization_response', convert_numpy_types(response), room=sid)
                        return
                
                # 设置优化充电状态
                battery_model.rul_optimized_charging = enable
                logger.info(f"RUL优化充电已{'启用' if enable else '禁用'}")
                
                # 发送响应
                response = {
                    "success": True,
                    "message": f"RUL优化充电已{'启用' if enable else '禁用'}",
                    "rul_optimized_charging": battery_model.rul_optimized_charging,
                    "request_id": request_id
                }
                await sio.emit('rul_optimization_response', convert_numpy_types(response), room=sid)
                
                # 广播更新后的电池状态
                await broadcast_battery_state()
                
            except Exception as e:
                logger.error(f"设置RUL优化充电失败: {e}", exc_info=True)
                response = {
                    "success": False,
                    "message": f"设置失败: {str(e)}",
                    "rul_optimized_charging": battery_model.rul_optimized_charging,
                    "request_id": request_id
                }
                await sio.emit('rul_optimization_response', convert_numpy_types(response), room=sid)
        
        else:
            logger.warning(f"未知操作: {action}")
            
    except Exception as e:
        logger.error(f"处理客户端消息时出错: {e}", exc_info=True)
        await sio.emit('error', {"message": str(e)}, room=sid)
        logger.info(f"已发送错误信息到客户端 {sid}")

async def _generate_complete_battery_state(battery_state):
    """生成完整的电池状态信息，包括RUL预测、健康信息和充电优化"""
    # 更新RUL估计 - 确保提供RUL预测和健康信息
    rul_percentage = battery_model.health  # 默认使用电池健康状态作为RUL
    health_info = None
    adjusted_params = None
    
    # 准备静态特征
    avg_temp = battery_state.get("temperature", 25)
    if len(battery_history) > 0:
        # 如果有历史数据，计算平均温度
        temp_data = [h.get("temperature", 25) for h in battery_history[-100:]]
        avg_temp = np.mean(temp_data) if temp_data else 25
    
    static_features = np.array([
        battery_model.cycle_count,
        battery_model.health,
        avg_temp
    ])
    
    if len(battery_history) >= 5:  # 需要足够的历史数据进行预测
        # 预测RUL
        try:
            # 使用 CNN+LSTM 模型预测 RUL
            raw_rul = cnn_lstm_rul_model.predict_rul(battery_history, static_features)
            
            # 将循环数转换为百分比，假设最大寿命为 1000 循环
            max_life_cycles = 1000
            rul_percentage = min(100, max(0, (raw_rul / max_life_cycles) * 100))
            logger.debug(f"CNN+LSTM RUL预测结果: {raw_rul} 循环 -> {rul_percentage:.1f}%")
            
        except Exception as e:
            logger.error(f"CNN+LSTM RUL预测失败: {e}", exc_info=True)
            # 使用简单估计
            try:
                raw_rul = rul_model.predict_rul(static_features, static_features)
                max_life_cycles = 1000
                rul_percentage = min(100, max(0, (raw_rul / max_life_cycles) * 100))
                logger.debug(f"备选 RUL 预测结果: {raw_rul} 循环 -> {rul_percentage:.1f}%")
            except Exception as e2:
                logger.error(f"备选RUL预测也失败: {e2}")
                # 使用电池健康状态作为RUL
                rul_percentage = battery_model.health
    else:
        # 没有足够历史数据，使用基于健康状态的简单估计
        logger.debug("历史数据不足，使用健康状态估计RUL")
        rul_percentage = battery_model.health
    
    # 设置RUL值
    battery_state["estimated_rul"] = rul_percentage
    
    # 生成健康评估信息（无论是否有足够的历史数据）
    try:
        # 如果历史数据不足，创建最小数据集
        history_for_eval = battery_history if len(battery_history) >= 5 else [
            {
                "voltage": battery_state.get("voltage", 3.7),
                "current": battery_state.get("current", 0),
                "temperature": battery_state.get("temperature", 25),
                "soc": battery_state.get("soc", 50),
                "internal_resistance": battery_state.get("internal_resistance", 0.1)
            }
        ] * 5  # 复制当前状态作为历史数据
        
        health_info = cnn_lstm_rul_model.evaluate_battery_health(
            history_for_eval, static_features, rul_percentage)
        battery_state["health_info"] = health_info
        logger.debug(f"健康评估完成: {health_info.get('status', 'N/A')}")
        
    except Exception as e:
        logger.error(f"健康评估失败: {e}", exc_info=True)
        # 提供默认健康信息
        battery_state["health_info"] = {
            "status": "无法评估",
            "grade": "N/A", 
            "score": battery_model.health,
            "rul_percentage": rul_percentage,
            "estimated_remaining_cycles": int(1000 * rul_percentage / 100),
            "health_percentage": battery_model.health,
            "recommendations": ["系统启动中，健康评估功能暂不可用"],
            "last_evaluation_time": time.time()
        }
    
    # 根据 RUL 调整充电参数（总是计算，以供显示）
    try:
        adjusted_params = cnn_lstm_rul_model.adjust_charging_parameters(battery_state, rul_percentage)
        
        # 总是提供充电优化信息，enabled状态基于rul_optimized_charging设置
        battery_state["charging_optimization"] = {
            "enabled": battery_model.rul_optimized_charging,
            "adjusted_params": adjusted_params if battery_model.rul_optimized_charging else None,
            "rul_percentage": rul_percentage,
            "charging_advice": adjusted_params.get("charging_advice", []) if battery_model.rul_optimized_charging else []
        }
        
        # 如果正在充电且启用了优化，应用参数到电池模型
        if battery_model.is_charging and battery_model.rul_optimized_charging:
            battery_model.update_charging_params(adjusted_params)
            logger.info(f"基于 RUL {rul_percentage:.1f}% 调整了充电参数")
            
    except Exception as e:
        logger.error(f"充电参数调整失败: {e}", exc_info=True)
        # 提供默认优化信息
        battery_state["charging_optimization"] = {
            "enabled": battery_model.rul_optimized_charging,
            "adjusted_params": None,
            "rul_percentage": rul_percentage,
            "charging_advice": ["参数调整功能暂不可用"]
        }
        
    # 添加实时健康监控警告
    warnings = []
    if battery_state["temperature"] > 40:
        warnings.append({
            "type": "temperature",
            "level": "high",
            "message": "电池温度过高，建议降低负载或暂停充电"
        })
    elif battery_state["temperature"] < 5:
        warnings.append({
            "type": "temperature",
            "level": "low",
            "message": "电池温度过低，可能影响充电效率和寿命"
        })
        
    if health_info and health_info.get("internal_resistance_trend", 0) > 0.001:
        warnings.append({
            "type": "internal_resistance",
            "level": "warning",
            "message": "电池内阻上升趋势明显，可能表明电池老化加速"
        })
        
    if battery_state["voltage"] > 4.25:
        warnings.append({
            "type": "voltage",
            "level": "high",
            "message": "电池电压过高，可能损害电池"
        })
        
    battery_state["health_warnings"] = warnings
    
    return battery_state

async def broadcast_battery_state(target_sid=None):
    """广播电池状态
    
    参数:
        target_sid: 目标客户端ID，如果为None则广播给所有客户端
    """
    # 获取基本电池状态
    battery_state = battery_model.get_state()
    
    # 生成完整的电池状态信息（包括健康信息和充电优化）
    battery_state = await _generate_complete_battery_state(battery_state)
    
    # 广播状态
    battery_state = convert_numpy_types(battery_state)  # 转换NumPy类型
    if target_sid:
        await sio.emit('battery_state', battery_state, room=target_sid)
        logger.debug(f"已发送电池状态到客户端 {target_sid}: SOC={battery_state['soc']}%, 电压={battery_state['voltage']}V")
    else:
        await sio.emit('battery_state', battery_state)
        logger.debug(f"已广播电池状态到所有客户端: SOC={battery_state['soc']}%, 电压={battery_state['voltage']}V")

async def broadcast_charging_records(target_sid=None):
    """广播充电记录
    
    参数:
        target_sid: 目标客户端ID，如果为None则广播给所有客户端
    """
    charging_records = get_all_charging_records()
    charging_records = convert_numpy_types(charging_records)  # 转换NumPy类型
    record_count = len(charging_records)
    
    if target_sid:
        await sio.emit('charging_records', charging_records, room=target_sid)
        logger.info(f"已发送充电记录到客户端 {target_sid}: {record_count}条记录")
    else:
        await sio.emit('charging_records', charging_records)
        logger.info(f"已广播充电记录到所有客户端: {record_count}条记录")

async def simulator_loop():
    """电池模拟器主循环"""
    global simulator_running
    update_interval = SIMULATOR_CONFIG["update_interval"]
    
    logger.info(f"启动电池模拟器循环，更新间隔: {update_interval}秒")
    simulator_running = True
    loop_count = 0
    
    try:
        while simulator_running:
            loop_count += 1
            
            # 更新电池状态
            start_time = time.time()
            battery_state = battery_model.update()
            update_time = time.time() - start_time
            
            # 每10次循环记录一次详细状态
            if loop_count % 10 == 0:
                logger.info(f"电池状态更新 #{loop_count}: SOC={battery_state['soc']:.2f}%, 电压={battery_state['voltage']:.2f}V, 电流={battery_state['current']:.2f}A, 温度={battery_state['temperature']:.2f}°C")
                logger.debug(f"状态更新耗时: {update_time*1000:.2f}ms")
            
            # 收集历史数据
            battery_history.append({
                "soc": battery_state["soc"],
                "voltage": battery_state["voltage"],
                "current": battery_state["current"],
                "temperature": battery_state["temperature"],
                "internal_resistance": battery_state["internal_resistance"]
            })
            
            # 限制历史数据长度
            if len(battery_history) > MAX_HISTORY_LENGTH:
                battery_history.pop(0)
            
            # 广播更新后的状态
            await broadcast_battery_state()
            
            # 等待下一次更新
            await asyncio.sleep(update_interval)
            
    except Exception as e:
        logger.error(f"模拟器循环中出错: {e}", exc_info=True)
        simulator_running = False
    finally:
        logger.info(f"电池模拟器循环已停止，共执行了 {loop_count} 次更新")
        simulator_running = False

async def ensure_simulator_running():
    """确保模拟器在运行"""
    global simulator_task, simulator_running
    
    if not simulator_running:
        logger.info("启动电池模拟器任务")
        simulator_task = asyncio.create_task(simulator_loop())
        logger.info("电池模拟器任务已启动")
    else:
        logger.info("电池模拟器已在运行中")

async def stop_simulator():
    """停止模拟器"""
    global simulator_task, simulator_running
    
    if simulator_running:
        logger.info("准备停止电池模拟器")
        simulator_running = False
        if simulator_task:
            try:
                # 等待任务完成
                logger.info("等待模拟器任务完成")
                await asyncio.wait_for(simulator_task, timeout=5.0)
                logger.info("模拟器任务已正常完成")
            except asyncio.TimeoutError:
                # 如果超时，取消任务
                logger.warning("等待模拟器任务超时，强制取消")
                simulator_task.cancel()
                try:
                    await simulator_task
                except asyncio.CancelledError:
                    logger.info("模拟器任务已取消")
            simulator_task = None
            logger.info("电池模拟器任务已停止")

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    logger.info("电池模拟器服务器正在启动")
    init_db()
    
    # 创建模型目录
    os.makedirs("models", exist_ok=True)
    logger.info("已确保模型目录存在")
    
    # 默认启用RUL优化充电
    battery_model.rul_optimized_charging = True
    logger.info("✅ RUL优化充电已自动启用")
    logger.info("🚀 电池充电仿真模拟器完全启动，RUL优化功能已就绪")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的事件"""
    logger.info("电池模拟器服务器正在关闭")
    await stop_simulator()
    logger.info("服务器已完全关闭")

# Socket.IO已集成到FastAPI应用中，无需额外挂载
logger.info("Socket.IO应用已集成到FastAPI应用")

if __name__ == "__main__":
    # 启动服务器
    logger.info(f"准备启动Uvicorn服务器: host={SERVER_HOST}, port={SERVER_PORT}, reload={True}")
    uvicorn.run(
        "server:socket_app",  # 使用集成了Socket.IO的应用
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info"
    )
    logger.info("服务器已退出") 