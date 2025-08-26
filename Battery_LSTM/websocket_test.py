import socketio
import asyncio
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("websocket-test")

# 测试配置
SERVER_URL = "http://localhost:5111"  # 服务器地址
SOCKET_PATH = "/ws/"  # Socket.IO 路径

async def test_socketio_connection():
    """测试 Socket.IO 连接"""
    logger.info(f"开始测试 Socket.IO 连接: {SERVER_URL}, 路径: {SOCKET_PATH}")
    
    # 创建 Socket.IO 客户端
    sio = socketio.AsyncClient(logger=True, engineio_logger=True)
    
    # 注册事件处理函数
    @sio.event
    async def connect():
        logger.info("已成功连接到服务器！")
        
    @sio.event
    async def disconnect():
        logger.info("已断开与服务器的连接")
        
    @sio.event
    async def battery_state(data):
        logger.info(f"收到电池状态: {data}")
        
    @sio.event
    async def charging_records(data):
        logger.info(f"收到充电记录: {len(data)} 条记录")
    
    # 尝试连接
    try:
        logger.info(f"尝试连接到 {SERVER_URL} 的 Socket.IO 服务器...")
        await sio.connect(SERVER_URL, socketio_path=SOCKET_PATH.strip('/'))
        logger.info("连接成功！等待接收数据...")
        
        # 发送测试消息
        await sio.emit('message', {'action': 'get_charging_records'})
        logger.info("已发送获取充电记录请求")
        
        # 等待一段时间接收数据
        await asyncio.sleep(5)
        
        # 断开连接
        await sio.disconnect()
        logger.info("测试完成")
        return True
        
    except Exception as e:
        logger.error(f"连接失败: {e}")
        return False

async def test_direct_websocket():
    """测试直接使用 WebSocket 连接"""
    import websockets
    
    # 尝试直接连接 WebSocket
    ws_url = f"ws://localhost:5111/ws/?EIO=4&transport=websocket"
    logger.info(f"尝试直接连接 WebSocket: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("WebSocket 连接成功！")
            await asyncio.sleep(2)
            logger.info("WebSocket 测试完成")
            return True
    except Exception as e:
        logger.error(f"WebSocket 连接失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("====== 开始 WebSocket 连接测试 ======")
    
    # 测试 Socket.IO 连接
    socketio_result = await test_socketio_connection()
    
    # 测试直接 WebSocket 连接
    websocket_result = await test_direct_websocket()
    
    # 输出测试结果
    logger.info("\n====== 测试结果汇总 ======")
    logger.info(f"Socket.IO 连接测试: {'成功' if socketio_result else '失败'}")
    logger.info(f"直接 WebSocket 连接测试: {'成功' if websocket_result else '失败'}")
    
    if not socketio_result and not websocket_result:
        logger.info("\n可能的问题:")
        logger.info("1. 后端服务器未运行")
        logger.info("2. 端口 5111 未开放或被占用")
        logger.info("3. WebSocket 路径配置不正确")
        logger.info("\n建议检查:")
        logger.info("- 确认后端服务器已启动")
        logger.info("- 检查 server.py 中的 socketio_path 设置")
        logger.info("- 检查前端 Socket.IO 客户端的路径配置")

if __name__ == "__main__":
    asyncio.run(main()) 