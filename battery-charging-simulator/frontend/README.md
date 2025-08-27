# 电池充电仿真模拟器 - 前端

## 项目概述

基于Vue.js构建的电池充电仿真模拟器前端界面，用于模拟比亚迪秦L EV电池的充放电过程。

主要功能：
- 电池充电与放电过程的实时可视化
- 直观展示电池SOC、电压、电流、温度等参数
- 支持手动调整电池内阻和温度参数
- 基于CNN+LSTM模型的RUL预测和充电策略优化
- 记录和展示充电过程各阶段的参数（恒流时间、恒压时间、涓流大小等）

## 技术栈

- Vue.js 3.x
- Socket.io-client (WebSocket实时通信)
- Chart.js (数据可视化)
- SVG (电池动画绘制)
- Vite (前端构建工具)

## 项目结构

```
frontend/
├── public/               # 静态资源
├── src/
│   ├── assets/           # 样式和资源文件
│   ├── components/       # Vue组件
│   │   ├── TopBarMenu.vue       # 顶部导航栏
│   │   ├── SimulationDashboard.vue # 仿真主页视图
│   │   ├── StatisticsView.vue   # 充电统计视图
│   │   ├── RecordsManagementView.vue # 记录管理视图
│   │   ├── HealthAnalysisView.vue  # 健康分析视图
│   │   ├── BatteryView.vue      # 电池可视化组件
│   │   ├── ControlPanel.vue     # 控制面板组件
│   │   └── ChargingStats.vue    # 充电统计图表
│   ├── services/         # API服务
│   │   └── api.js        # WebSocket通信模块
│   ├── App.vue           # 主应用组件
│   └── main.js           # 入口文件
├── index.html            # HTML入口
├── package.json          # 项目依赖
└── vite.config.js        # Vite配置
```

## 安装与运行

### 安装依赖

```bash
npm install
```

### 开发模式运行

```bash
npm run dev
```

应用将在 http://localhost:5111 运行。

### 构建生产版本

```bash
npm run build
```

构建的文件将输出到 `dist` 目录。

## 架构与组件说明

应用采用模块化设计，通过 `TopBarMenu` 导航栏在不同的功能视图间切换，取代了原有的单页长滚动布局。

### 主要视图组件

- **SimulationDashboard**: 仿真主页，集成了电池可视化、控制面板和实时状态显示。
- **StatisticsView**: 充电统计视图，展示历史充电数据的图表。
- **RecordsManagementView**: 记录管理视图，用于浏览和管理充电记录。
- **HealthAnalysisView**: 电池健康分析视图，显示RUL预测和健康状态。

### 核心UI组件

- **BatteryView**: 电池可视化组件，使用SVG绘制电池图像，实时展示SOC、充放电状态等。
- **ControlPanel**: 控制面板组件，提供充电/放电按钮和参数调节滑块。
- **ChargingStats**: 充电统计图表组件，展示充电记录、各充电阶段的时长和参数等统计数据。

## 通信协议

前端通过WebSocket与后端实时通信，主要交互包括：

- 接收电池状态更新 (`battery_state` 事件)
- 接收充电记录 (`charging_records` 事件)
- 发送充电/放电命令
- 发送参数更新请求

## 后端依赖

此前端应用需要连接到对应的后端服务才能正常工作。后端服务需要提供以下功能：

- WebSocket实时通信
- 电池模型模拟
- 充放电控制逻辑
- RUL预测模型接口 