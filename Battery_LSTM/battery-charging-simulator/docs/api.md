# 电池充电仿真模拟器 API 文档

本文档详细描述了电池充电仿真模拟器的API接口，包括WebSocket事件和REST接口。

## REST API

### 获取服务器信息

```
GET /
```

返回服务器基本信息。

**响应示例:**

```json
{
  "message": "电池充电仿真模拟器后端API"
}
```

### 获取服务器状态

```
GET /api/status
```

返回服务器当前状态，包括连接客户端数量、模拟器状态和电池状态。

**响应示例:**

```json
{
  "status": "running",
  "connected_clients": 1,
  "simulator_running": true,
  "battery_state": {
    "soc": 85.2,
    "voltage": 380.5,
    "current": 60.0,
    "temperature": 32.4,
    "internal_resistance": 0.15,
    "is_charging": true,
    "is_discharging": false,
    "charging_mode": "cc",
    "charging_current": 60.0,
    "charging_voltage": 380.5,
    "cycle_count": 12.5,
    "health": 98.2,
    "estimated_rul": 95.6,
    "ambient_temperature": 25.0
  }
}
```

## WebSocket 事件

客户端与服务器通过WebSocket通信，交换实时数据和控制命令。

### 服务器发送的事件

#### battery_state

电池状态更新事件，当电池状态发生变化时服务器会广播此事件。

**数据格式:**

```json
{
  "soc": 85.2,             // 荷电状态百分比
  "voltage": 380.5,        // 端电压 (V)
  "current": 60.0,         // 电流 (A)
  "temperature": 32.4,     // 电池温度 (°C)
  "internal_resistance": 0.15, // 内阻 (Ω)
  "is_charging": true,     // 是否充电
  "is_discharging": false, // 是否放电
  "charging_mode": "cc",   // 充电模式: none, cc, cv, trickle
  "charging_current": 60.0, // 充电电流 (A)
  "charging_voltage": 380.5, // 充电电压 (V)
  "cycle_count": 12.5,     // 循环次数
  "health": 98.2,          // 健康状态 (%)
  "estimated_rul": 95.6,   // 估计剩余寿命 (%)
  "ambient_temperature": 25.0 // 环境温度 (°C)
}
```

#### charging_records

充电记录更新事件，包含所有充电记录的列表。

**数据格式:**

```json
[
  {
    "start_time": "2023-07-15T12:30:45.123456",
    "end_time": "2023-07-15T14:15:23.654321",
    "initial_soc": 20.5,
    "final_soc": 90.2,
    "initial_temperature": 25.0,
    "final_temperature": 35.6,
    "charging_phases": [
      {
        "phase": "cc",
        "start_time": "2023-07-15T12:30:45.123456",
        "end_time": "2023-07-15T13:45:12.345678",
        "initial_soc": 20.5,
        "initial_temperature": 25.0,
        "cc_current": 80.0
      },
      {
        "phase": "cv",
        "start_time": "2023-07-15T13:45:12.345678",
        "end_time": "2023-07-15T14:10:30.987654",
        "initial_soc": 85.3,
        "initial_temperature": 34.2,
        "cv_voltage": 395.0
      },
      {
        "phase": "trickle",
        "start_time": "2023-07-15T14:10:30.987654",
        "end_time": "2023-07-15T14:15:23.654321",
        "initial_soc": 89.8,
        "initial_temperature": 35.4,
        "trickle_current": 2.5,
        "trickle_voltage": 405.0
      }
    ]
  }
]
```

#### error

错误事件，当服务器处理请求过程中发生错误时发送。

**数据格式:**

```json
{
  "message": "错误信息内容"
}
```

### 客户端发送的事件

客户端通过 `message` 事件发送控制命令给服务器。

#### 开始充电

```json
{
  "action": "start_charging"
}
```

#### 开始放电

```json
{
  "action": "start_discharging"
}
```

#### 停止充放电

```json
{
  "action": "stop"
}
```

#### 更新电池参数

```json
{
  "action": "update_params",
  "params": {
    "internal_resistance": 0.18,
    "temperature": 30.0,
    "ambient_temperature": 28.0
  }
}
```

#### 获取充电记录

```json
{
  "action": "get_charging_records"
}
```

#### 重置电池状态

```json
{
  "action": "reset"
}
```

## WebSocket 连接

前端通过以下方式连接WebSocket服务：

```javascript
import { io } from 'socket.io-client';

const socket = io(`/ws/${clientId}`, {
  path: '/ws',
  transports: ['websocket'],
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
});

// 监听电池状态更新
socket.on('battery_state', (data) => {
  console.log('Battery state updated:', data);
});

// 监听充电记录更新
socket.on('charging_records', (data) => {
  console.log('Charging records updated:', data);
});

// 发送控制命令
socket.emit('message', JSON.stringify({
  action: 'start_charging'
}));
```