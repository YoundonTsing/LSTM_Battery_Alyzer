"""
测试端口修复后的连接状态
"""
import requests
import time

def test_port_availability():
    """测试端口可用性"""
    print("🔧 端口冲突修复验证")
    print("="*50)
    
    # 检查8000端口（旧端口，应该被其他服务占用）
    try:
        resp = requests.get('http://localhost:8000/api/status', timeout=2)
        print("⚠️  端口8000仍有服务响应（其他项目）")
        print(f"   响应状态: {resp.status_code}")
    except Exception as e:
        print(f"❌ 端口8000连接失败（预期行为）: {e}")
    
    # 检查8001端口（新端口，我们的服务）
    print("\n检查新端口8001...")
    try:
        resp = requests.get('http://localhost:8001/api/status', timeout=2)
        if resp.status_code == 200:
            print("✅ 端口8001服务正常运行")
            print("✅ 端口冲突问题已解决")
            return True
        else:
            print(f"⚠️  端口8001响应异常: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 端口8001连接失败: {e}")
        print("💡 需要启动后端服务器:")
        print("   cd battery-charging-simulator/backend && python server.py")
        return False

def test_cors_fix():
    """测试CORS修复"""
    print("\n🌐 CORS配置测试")
    print("-"*30)
    
    try:
        # 使用OPTIONS请求测试CORS预检
        resp = requests.options('http://localhost:8001/api/status', 
                              headers={'Origin': 'http://localhost:5111'}, 
                              timeout=2)
        print(f"OPTIONS预检请求状态: {resp.status_code}")
        
        # 检查CORS头
        cors_headers = {
            'Access-Control-Allow-Origin': resp.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': resp.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': resp.headers.get('Access-Control-Allow-Headers')
        }
        
        print("CORS响应头:")
        for header, value in cors_headers.items():
            if value:
                print(f"  {header}: {value}")
                
        # 检查是否有重复的Origin头
        origin_header = resp.headers.get('Access-Control-Allow-Origin', '')
        if ',' in origin_header:
            print("❌ 发现重复的Access-Control-Allow-Origin头")
            return False
        else:
            print("✅ CORS配置正常，无重复头部")
            return True
            
    except Exception as e:
        print(f"❌ CORS测试失败: {e}")
        return False

def main():
    """主测试"""
    print("🔍 端口冲突和CORS问题修复验证")
    print("="*60)
    
    # 等待一下，给服务器启动时间
    print("等待3秒，给后端服务器启动时间...")
    time.sleep(3)
    
    port_ok = test_port_availability()
    cors_ok = test_cors_fix() if port_ok else False
    
    print("\n" + "="*60)
    print("📋 修复验证结果:")
    print(f"  端口冲突修复: {'✅ 成功' if port_ok else '❌ 失败'}")
    print(f"  CORS配置修复: {'✅ 成功' if cors_ok else '❌ 失败/未测试'}")
    
    if port_ok and cors_ok:
        print("\n🎉 所有问题已修复，前端应该能正常连接！")
        print("💡 可以启动前端测试:")
        print("   cd battery-charging-simulator/frontend && npm run dev")
    else:
        print("\n⚠️  仍有问题需要解决")
        if not port_ok:
            print("   - 确保后端服务器在8001端口运行")
        if port_ok and not cors_ok:
            print("   - 检查CORS配置")

if __name__ == "__main__":
    main()