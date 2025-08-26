# 电池充电仿真模拟器 - 后端

## 项目概述

基于Python FastAPI和Socket.IO构建的电池充电仿真模拟器后端服务，提供电池模型模拟、充放电控制和RUL预测功能。

主要功能：
- 电池物理特性模拟（SOC、电压、电流、温度等）
- 多阶段充电控制（恒流CC、恒压CV、涓流充电）
- 实时WebSocket通信
- 基于CNN+LSTM深度学习的RUL（剩余寿命）预测
- 充电记录和参数统计

## 技术栈

- Python 3.8+
- FastAPI (Web框架)
- Socket.IO (WebSocket通信)
- NumPy/Pandas (数据处理)
- TensorFlow/Keras (深度学习)
- Uvicorn (ASGI服务器)

## 项目结构

```
backend/
├── config.py              # 配置文件
├── requirements.txt       # 依赖文件
├── server.py              # 主服务器程序
├── models/
│   ├── battery_model.py   # 电池模型
│   └── rul_model.py       # RUL预测模型
```

## 安装与运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行服务器

```bash
python server.py
```

服务器将在 http://localhost:8000 运行。

## API接口

### REST API

- `GET /` - 获取服务器信息
- `GET /api/status` - 获取服务器状态

### WebSocket事件

客户端可接收的事件：
- `battery_state` - 电池状态更新
- `charging_records` - 充电记录更新
- `error` - 错误信息

客户端可发送的事件：
- `message` - 发送控制命令

#### 控制命令

可用的控制命令：
- `start_charging` - 开始充电
- `start_discharging` - 开始放电
- `stop` - 停止充放电
- `update_params` - 更新电池参数
- `get_charging_records` - 获取充电记录
- `reset` - 重置电池状态

## 电池模型

后端实现了一个基于物理规律的电池模型，模拟比亚迪秦L EV电池的特性：

- 电压与SOC的关系建模
- 热效应模拟
- 内阻变化与温度的关联
- 三阶段充电控制策略
- 电池寿命与循环次数的关系

## RUL预测模型

使用CNN+LSTM混合深度学习模型来预测电池的剩余使用寿命：

- CNN层提取电池数据的空间特征
- LSTM层捕获时间序列变化模式
- 同时考虑循环次数等静态特征
- 输出0-100%的RUL预测值

## 前端依赖

此后端服务需要配合对应的前端应用一起使用，前端通过WebSocket与后端进行实时通信。 