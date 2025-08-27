// 前端 WebSocket 连接测试脚本
const { io } = require('socket.io-client');

// 日志函数
function log(message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${message}`);
}

// 测试配置
const SERVER_URL = 'http://localhost:5111';
const SOCKET_PATH = '/ws';

// 测试 Socket.IO 连接
async function testSocketIOConnection() {
  log('====== 测试前端 Socket.IO 连接 ======');
  log(`尝试连接到 ${SERVER_URL}，路径: ${SOCKET_PATH}`);

  // 创建 Socket.IO 客户端 - 使用与前端相同的配置
  const socket = io(SERVER_URL, {
    path: SOCKET_PATH,
    transports: ['websocket'],
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
  });

  // 设置超时
  const timeout = setTimeout(() => {
    log('连接超时！');
    socket.disconnect();
  }, 10000);

  return new Promise((resolve) => {
    // 监听连接成功事件
    socket.on('connect', () => {
      log('WebSocket 连接成功！');
      log(`Socket ID: ${socket.id}`);
      
      // 发送测试消息
      log('发送获取充电记录请求...');
      socket.emit('message', JSON.stringify({
        action: 'get_charging_records'
      }));
    });

    // 监听断开连接事件
    socket.on('disconnect', (reason) => {
      log(`WebSocket 断开连接: ${reason}`);
      clearTimeout(timeout);
      resolve(false);
    });

    // 监听错误事件
    socket.on('error', (error) => {
      log(`WebSocket 错误: ${error}`);
    });

    // 监听连接错误事件
    socket.on('connect_error', (error) => {
      log(`连接错误: ${error.message}`);
      if (error.message.includes('xhr poll error')) {
        log('可能是服务器未运行或路径配置错误');
      }
    });

    // 监听电池状态更新
    socket.on('battery_state', (data) => {
      log(`收到电池状态: SOC=${data.soc}%, 电压=${data.voltage}V`);
      // 测试成功，断开连接
      setTimeout(() => {
        log('测试完成，断开连接');
        socket.disconnect();
        clearTimeout(timeout);
        resolve(true);
      }, 2000);
    });

    // 监听充电记录更新
    socket.on('charging_records', (data) => {
      log(`收到充电记录: ${data.length} 条记录`);
    });
  });
}

// 测试不同的路径配置
async function testDifferentPaths() {
  log('\n====== 测试不同的路径配置 ======');
  
  const pathOptions = [
    { url: SERVER_URL, path: '/ws' },
    { url: SERVER_URL, path: '/ws/' },
    { url: SERVER_URL, path: 'ws' },
    { url: SERVER_URL, path: '/socket.io' }
  ];
  
  for (const option of pathOptions) {
    log(`\n尝试连接: ${option.url}, 路径: ${option.path}`);
    
    const socket = io(option.url, {
      path: option.path,
      transports: ['websocket'],
      reconnectionAttempts: 1,
      reconnectionDelay: 500,
      timeout: 3000
    });
    
    await new Promise((resolve) => {
      let resolved = false;
      
      socket.on('connect', () => {
        log(`✅ 成功! 路径 ${option.path} 可以连接!`);
        socket.disconnect();
        if (!resolved) {
          resolved = true;
          resolve();
        }
      });
      
      socket.on('connect_error', (error) => {
        log(`❌ 失败! 路径 ${option.path} 连接错误: ${error.message}`);
        socket.disconnect();
        if (!resolved) {
          resolved = true;
          resolve();
        }
      });
      
      // 设置超时
      setTimeout(() => {
        if (!resolved) {
          log(`⏱️ 超时! 路径 ${option.path} 连接超时`);
          socket.disconnect();
          resolved = true;
          resolve();
        }
      }, 5000);
    });
  }
}

// 打印诊断信息
function printDiagnostics() {
  log('\n====== 诊断信息 ======');
  log(`Node.js 版本: ${process.version}`);
  log(`Socket.IO 客户端版本: ${require('socket.io-client/package.json').version}`);
  log(`操作系统: ${process.platform} ${process.arch}`);
}

// 主函数
async function main() {
  log('开始 WebSocket 连接测试');
  printDiagnostics();
  
  // 测试主连接
  const result = await testSocketIOConnection();
  
  // 如果主连接失败，尝试不同的路径配置
  if (!result) {
    await testDifferentPaths();
  }
  
  log('\n====== 测试完成 ======');
  log('建议:');
  log('1. 确认后端服务器已启动');
  log('2. 检查 server.py 中的 socketio_path 设置 (当前应为 "ws")');
  log('3. 检查前端 api.js 中的 path 设置 (当前应为 "/ws")');
  log('4. 确保端口 5111 未被其他程序占用');
}

// 运行测试
main().catch(error => {
  log(`测试过程中发生错误: ${error.message}`);
}); 