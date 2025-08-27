"""
测试CORS重复头问题修复
"""
import requests
import socketio
import asyncio
import time

def test_rest_api_cors():
    """测试REST API的CORS配置"""
    print("🌐 测试REST API CORS配置")
    print("-" * 40)
    
    try:
        # 测试预检请求
        response = requests.options(
            'http://localhost:8001/api/status',
            headers={
                'Origin': 'http://localhost:5111',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=5
        )
        
        print(f"OPTIONS请求状态码: {response.status_code}")
        
        # 检查CORS头
        cors_headers = {}
        for header, value in response.headers.items():
            if header.lower().startswith('access-control'):
                cors_headers[header] = value
        
        print("CORS响应头:")
        for header, value in cors_headers.items():
            print(f"  {header}: {value}")
            
        # 检查是否有重复的Origin
        origin_header = response.headers.get('Access-Control-Allow-Origin', '')
        if ',' in origin_header or origin_header.count('http://localhost:5111') > 1:
            print("❌ 发现重复的Access-Control-Allow-Origin")
            return False
        elif origin_header == 'http://localhost:5111' or origin_header == '*':
            print("✅ Access-Control-Allow-Origin配置正常")
            return True
        else:
            print(f"⚠️  意外的Origin值: {origin_header}")
            return False
            
    except Exception as e:
        print(f"❌ REST API CORS测试失败: {e}")
        return False

async def test_websocket_cors():
    """测试WebSocket的CORS配置"""
    print("\n🔌 测试WebSocket CORS配置")
    print("-" * 40)
    
    try:
        sio = socketio.AsyncClient()
        connected = False
        
        @sio.event
        async def connect():
            nonlocal connected
            connected = True
            print("✅ WebSocket连接成功")
        
        @sio.event
        async def connect_error(data):
            print(f"❌ WebSocket连接错误: {data}")
        
        # 尝试连接
        await sio.connect(
            'http://localhost:8001',
            socketio_path='/ws',
            headers={'Origin': 'http://localhost:5111'},
            transports=['polling']  # 先测试polling
        )
        
        # 等待连接稳定
        await asyncio.sleep(2)
        
        if connected:
            print("✅ WebSocket polling连接成功，无CORS错误")
            await sio.disconnect()
            return True
        else:
            print("❌ WebSocket连接超时")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket CORS测试失败: {e}")
        return False

def test_api_functionality():
    """测试API功能是否正常"""
    print("\n🔧 测试API功能")
    print("-" * 40)
    
    try:
        # 测试状态端点
        response = requests.get('http://localhost:8001/api/status', timeout=5)
        print(f"API状态端点: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API响应正常，连接客户端数: {data.get('connected_clients_count', 0)}")
            return True
        else:
            print(f"❌ API响应异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API功能测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🔧 CORS重复头问题修复验证")
    print("=" * 50)
    
    # 等待服务器启动
    print("等待后端服务器启动...")
    time.sleep(3)
    
    # 测试API功能
    api_ok = test_api_functionality()
    
    if not api_ok:
        print("\n⚠️  后端服务器未运行，请先启动:")
        print("   cd battery-charging-simulator/backend && python server.py")
        return
    
    # 测试REST API CORS
    rest_cors_ok = test_rest_api_cors()
    
    # 测试WebSocket CORS
    ws_cors_ok = await test_websocket_cors()
    
    print("\n" + "=" * 50)
    print("📋 CORS修复验证结果:")
    print(f"  后端服务器运行: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"  REST API CORS: {'✅ 正常' if rest_cors_ok else '❌ 异常'}")
    print(f"  WebSocket CORS: {'✅ 正常' if ws_cors_ok else '❌ 异常'}")
    
    if api_ok and rest_cors_ok and ws_cors_ok:
        print("\n🎉 所有CORS问题已修复！")
        print("💡 现在可以正常使用前端:")
        print("   cd battery-charging-simulator/frontend && npm run dev")
    else:
        print("\n⚠️  仍有问题需要解决")
        if not rest_cors_ok:
            print("   - REST API CORS配置有问题")
        if not ws_cors_ok:
            print("   - WebSocket CORS配置有问题")

if __name__ == "__main__":
    asyncio.run(main())