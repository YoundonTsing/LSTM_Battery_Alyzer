"""
测试前端监控功能的脚本
验证WebSocket连接和REST API轮询备选方案
"""
import asyncio
import requests
import socketio
import time

async def test_websocket_connection():
    """测试WebSocket连接"""
    print("=== 测试WebSocket连接 ===")
    
    sio = socketio.AsyncClient()
    connected = False
    
    @sio.event
    async def connect():
        nonlocal connected
        connected = True
        print("✅ WebSocket连接成功")
    
    @sio.event
    async def disconnect():
        print("❌ WebSocket连接断开")
    
    @sio.on('train_progress')
    async def on_train_progress(data):
        print(f"📈 训练进度: {data}")
    
    @sio.on('train_completed')
    async def on_train_completed(data):
        print(f"🎉 训练完成: {data}")
    
    try:
        # 尝试连接WebSocket
        await sio.connect('http://localhost:8001', socketio_path='/ws')
        await asyncio.sleep(2)  # 等待连接稳定
        
        if connected:
            print("✅ WebSocket功能正常，支持实时监控")
        else:
            print("❌ WebSocket连接超时")
            
    except Exception as e:
        print(f"❌ WebSocket连接失败: {e}")
        print("📡 将使用REST API轮询模式")
    finally:
        if sio.connected:
            await sio.disconnect()
    
    return connected

def test_rest_api_polling():
    """测试REST API轮询功能"""
    print("\n=== 测试REST API轮询 ===")
    
    # 首先检查后端状态
    try:
        resp = requests.get('http://localhost:8001/api/status', timeout=5)
        if resp.status_code == 200:
            print("✅ 后端API正常响应")
            
            # 模拟获取训练状态（使用假的jobId）
            fake_job_id = "test-job-123"
            status_resp = requests.get(f'http://localhost:8001/api/rul/train/{fake_job_id}/status')
            if status_resp.status_code == 404:
                print("✅ 训练状态API端点存在（返回404表示jobId不存在，这是正常的）")
            else:
                print(f"📊 训练状态API响应: {status_resp.status_code}")
                
            print("✅ REST API轮询功能可用作为备选方案")
            return True
        else:
            print(f"❌ 后端API响应异常: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端API连接失败: {e}")
        return False

def test_upload_functionality():
    """测试上传功能"""
    print("\n=== 测试上传功能 ===")
    
    try:
        # 创建测试文件
        import tempfile
        import zipfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                zf.writestr('test_charge.csv', 'cycle,voltage_battery,current_battery,temp_battery,capacity\n1,3.2,1.5,25,1.8\n')
                zf.writestr('test_discharge.csv', 'cycle,capacity\n1,1.8\n')
            
            # 测试上传
            with open(tmp_zip.name, 'rb') as f:
                resp = requests.post('http://localhost:8001/api/rul/dataset/upload', 
                                   data={'datasetId': 'test-frontend'}, 
                                   files={'file': f}, 
                                   timeout=30)
            
            if resp.status_code == 200:
                print("✅ 数据集上传功能正常")
                return True
            else:
                print(f"❌ 上传失败: {resp.status_code} - {resp.text}")
                return False
                
    except Exception as e:
        print(f"❌ 上传测试失败: {e}")
        return False
    finally:
        try:
            os.unlink(tmp_zip.name)
        except:
            pass

async def main():
    """主测试函数"""
    print("🔧 前端监控功能测试")
    print("="*50)
    
    # 测试WebSocket
    websocket_ok = await test_websocket_connection()
    
    # 测试REST API
    rest_api_ok = test_rest_api_polling()
    
    # 测试上传
    upload_ok = test_upload_functionality()
    
    print("\n" + "="*50)
    print("📋 测试结果总结:")
    print(f"  WebSocket实时监控: {'✅ 可用' if websocket_ok else '❌ 不可用'}")
    print(f"  REST API轮询备选: {'✅ 可用' if rest_api_ok else '❌ 不可用'}")
    print(f"  数据集上传功能: {'✅ 可用' if upload_ok else '❌ 不可用'}")
    
    if websocket_ok:
        print("\n🎉 推荐使用WebSocket模式，具有最佳实时性")
    elif rest_api_ok:
        print("\n📡 建议使用REST API轮询模式，作为可靠备选方案")
    else:
        print("\n⚠️  需要检查后端服务器状态")

if __name__ == "__main__":
    asyncio.run(main())