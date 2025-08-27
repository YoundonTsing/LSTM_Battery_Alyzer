import os
import io
import sys
import time
import zipfile
import argparse
import requests
import socketio

def zip_dir_to_bytes(src_dir: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for f in files:
                fp = os.path.join(root, f)
                # 相对路径写入压缩包
                arc = os.path.relpath(fp, start=src_dir)
                zf.write(fp, arcname=arc)
    buf.seek(0)
    return buf.read()

def upload_dataset(base_url: str, dataset_id: str, dataset_path: str):
    print(f"[upload] dataset_id={dataset_id}, path={dataset_path}")
    data = {'datasetId': dataset_id}
    zip_bytes = zip_dir_to_bytes(dataset_path)
    files = {
        'file': ('dataset.zip', zip_bytes, 'application/zip')
    }
    # 添加CORS头
    headers = {'Origin': 'http://localhost:5111'}
    resp = requests.post(f"{base_url}/api/rul/dataset/upload", data=data, files=files, headers=headers, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"upload failed {resp.status_code}: {resp.text}")
    print(f"[upload] ok -> {resp.json()}")
    return resp.json()

def trigger_train(base_url: str, dataset_id: str):
    print(f"[train] trigger with datasetId={dataset_id}")
    payload = {
        "datasetId": dataset_id
    }
    # 添加CORS头
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:5111'
    }
    resp = requests.post(f"{base_url}/api/rul/train", json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"train trigger failed {resp.status_code}: {resp.text}")
    j = resp.json()
    job_id = j.get("jobId")
    print(f"[train] queued jobId={job_id}")
    return job_id

def run_ws_progress(base_url: str, timeout_s: int = 3600):
    # 连接 Socket.IO: 路径为 /ws
    sio = socketio.Client()
    done = {"completed": False}

    @sio.event
    def connect():
        print("[ws] connected")

    @sio.on("train_progress")
    def on_progress(data):
        # data: {"jobId": "...", "message": "...", "progress": 10?}
        msg = data.get("message", "")
        prog = data.get("progress", None)
        if prog is not None:
            print(f"[progress] {prog}% | {msg}")
        else:
            print(f"[progress] {msg}")

    @sio.on("train_completed")
    def on_completed(data):
        success = data.get("success", False)
        if success:
            print(f"[completed] success, modelCount={data.get('modelCount')}, durationSec={data.get('durationSec')}")
        else:
            print(f"[completed] failed: {data.get('error')}")
        done["completed"] = True
        # 让 main 循环去关闭连接

    @sio.event
    def disconnect():
        print("[ws] disconnected")

    # 注意：socketio_path 使用 '/ws'，并添加fallback机制
    try:
        sio.connect(base_url, socketio_path='/ws', transports=['websocket'], headers={'Origin': 'http://localhost:5111'})
        print("[ws] 使用WebSocket连接")
    except Exception as e:
        print(f"[ws] WebSocket连接失败: {e}")
        try:
            sio.connect(base_url, socketio_path='/ws', transports=['polling'], headers={'Origin': 'http://localhost:5111'})
            print("[ws] 降级到Polling连接")
        except Exception as e2:
            print(f"[ws] Polling连接也失败: {e2}")
            print("[ws] 将使用REST API轮询监控训练状态")
            return False
    start = time.time()
    try:
        while not done["completed"]:
            time.sleep(1.0)
            if time.time() - start > timeout_s:
                print("[ws] timeout waiting for train_completed")
                break
    finally:
        if sio.connected:
            sio.disconnect()
    
    return True  # WebSocket连接成功

def poll_training_status(base_url: str, job_id: str, timeout_s: int = 3600):
    """REST API轮询训练状态"""
    print(f"[polling] 开始轮询训练状态，jobId={job_id}")
    start = time.time()
    
    while time.time() - start < timeout_s:
        try:
            headers = {'Origin': 'http://localhost:5111'}
            resp = requests.get(f"{base_url}/api/rul/train/{job_id}/status", headers=headers, timeout=10)
            if resp.status_code == 200:
                status = resp.json()
                print(f"[polling] 状态: {status.get('status', 'unknown')}")
                
                # 检查是否完成
                if status.get('status') == 'completed':
                    print(f"[polling] 训练完成! 模型数量: {status.get('modelCount', 0)}")
                    return True
                elif status.get('status') == 'failed':
                    print(f"[polling] 训练失败: {status.get('error', 'unknown error')}")
                    return False
                    
            time.sleep(3)  # 3秒轮询间隔
        except Exception as e:
            print(f"[polling] 查询状态失败: {e}")
            time.sleep(5)  # 错误时等待更长时间
    
    print("[polling] 轮询超时")
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001", help="backend base url")
    parser.add_argument("--dataset-id", required=True, help="dataset id to use (e.g., test1)")
    parser.add_argument("--dataset-path", required=True, help="local dataset dir containing csvs")
    args = parser.parse_args()

    print(f"🔧 RUL训练管道测试 (后端: {args.base_url})")
    print("=" * 50)

    # 1) 上传数据集
    print("📤 步骤1: 上传数据集")
    try:
        upload_dataset(args.base_url, args.dataset_id, args.dataset_path)
        print("✅ 数据集上传成功")
    except Exception as e:
        print(f"❌ 数据集上传失败: {e}")
        return

    # 2) 触发训练
    print("\n🚀 步骤2: 触发训练")
    try:
        job_id = trigger_train(args.base_url, args.dataset_id)
        print(f"✅ 训练已启动，作业ID: {job_id}")
    except Exception as e:
        print(f"❌ 训练启动失败: {e}")
        return

    # 3) 监控训练进度
    print("\n📊 步骤3: 监控训练进度")
    ws_success = run_ws_progress(args.base_url)
    
    if not ws_success:
        # WebSocket失败，使用REST API轮询
        print("🔄 使用REST API轮询模式...")
        poll_success = poll_training_status(args.base_url, job_id)
        if poll_success:
            print("✅ 训练完成 (REST API监控)")
        else:
            print("❌ 训练失败或超时 (REST API监控)")
    else:
        print("✅ 训练完成 (WebSocket监控)")
    
    print("\n" + "=" * 50)
    print("🎉 RUL训练管道测试完成!")

if __name__ == "__main__":
    main()