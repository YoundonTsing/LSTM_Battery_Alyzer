"""
简单的WebSocket连接测试
"""
import requests
import time

def test_api_endpoints():
    """测试API端点的CORS"""
    print("🔧 测试API端点CORS")
    print("-" * 30)
    
    try:
        # 测试状态端点
        response = requests.get('http://localhost:8001/api/status', 
                              headers={'Origin': 'http://localhost:5111'})
        print(f"API状态端点: {response.status_code}")
        
        # 检查CORS头
        origin_header = response.headers.get('Access-Control-Allow-Origin', '')
        print(f"Access-Control-Allow-Origin: {origin_header}")
        
        if response.status_code == 200 and 'localhost:5111' in origin_header:
            print("✅ API CORS正常")
            return True
        else:
            print("❌ API CORS异常")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def test_websocket_endpoint():
    """测试WebSocket端点的CORS"""
    print("\n🔌 测试WebSocket端点CORS")
    print("-" * 30)
    
    try:
        # 测试Socket.IO轮询端点
        response = requests.get('http://localhost:8001/ws/?EIO=4&transport=polling', 
                              headers={'Origin': 'http://localhost:5111'})
        print(f"WebSocket轮询端点: {response.status_code}")
        
        # 检查CORS头
        origin_header = response.headers.get('Access-Control-Allow-Origin', '')
        print(f"Access-Control-Allow-Origin: {origin_header}")
        
        # 检查响应内容
        content = response.text if response.status_code == 200 else "N/A"
        print(f"响应内容长度: {len(content)}")
        
        if response.status_code == 200 and origin_header:
            print("✅ WebSocket CORS正常")
            return True
        else:
            print("❌ WebSocket CORS异常")
            print("详细响应头:")
            for header, value in response.headers.items():
                if 'access-control' in header.lower():
                    print(f"  {header}: {value}")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
        return False

def main():
    """主测试"""
    print("🔧 WebSocket CORS修复验证")
    print("=" * 40)
    
    # 等待后端启动
    print("等待后端服务器...")
    time.sleep(2)
    
    # 测试API端点
    api_ok = test_api_endpoints()
    
    # 测试WebSocket端点
    ws_ok = test_websocket_endpoint()
    
    print("\n" + "=" * 40)
    print("📋 测试结果:")
    print(f"  API CORS: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"  WebSocket CORS: {'✅ 正常' if ws_ok else '❌ 异常'}")
    
    if api_ok and ws_ok:
        print("\n🎉 CORS问题已修复！")
        print("💡 前端WebSocket连接应该可以正常工作")
    else:
        print("\n⚠️  仍有CORS问题需要解决")

if __name__ == "__main__":
    main()