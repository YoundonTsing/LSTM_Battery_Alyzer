# 电池充电仿真模拟器

基于比亚迪秦L EV电池参数的充电/放电模拟器，包含电池特性建模、多阶段充电控制以及剩余寿命(RUL)预测功能。

## 项目结构

该项目由前端和后端两部分组成：

```
battery-charging-simulator/
├── frontend/                # Vue.js前端项目
│   ├── src/                 # 源代码
│   │   ├── components/      # Vue组件
│   │   ├── services/        # API服务
│   │   └── assets/          # 静态资源
│   ├── public/              # 公共文件
│   └── ...                  # 其他配置文件
│
├── backend/                 # Python后端项目
│   ├── models/              # 电池模型和RUL预测模型
│   ├── config.py            # 配置文件
│   ├── server.py            # 主服务器程序
│   └── ...                  # 其他文件
│
└── docs/                    # 文档
```

## 主要功能

- **电池状态可视化**：实时显示SOC、电压、电流、温度等参数
- **多阶段充电控制**：恒流(CC)、恒压(CV)和涓流充电阶段的自动切换
- **放电模拟**：模拟电池放电过程
- **参数调整**：支持调整内阻、温度等参数
- **RUL预测**：基于CNN+LSTM深度学习模型的电池剩余寿命预测
- **充电统计**：记录和展示充电过程各阶段的数据

## 技术栈

### 前端
- Vue.js 3.x
- Socket.IO Client
- Chart.js
- SVG动画

### 后端
- Python 3.8+
- FastAPI
- Socket.IO
- TensorFlow/Keras
- NumPy/Pandas

## 安装与运行

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 http://localhost:5111 运行。

### 后端

```bash
cd backend
pip install -r requirements.txt
python server.py
```

后端服务将在 http://localhost:8000 运行。

## 开发者

此项目是电动汽车电池管理系统(BMS)研究的一部分，旨在探索优化充电策略和提高电池寿命的方法。

## 许可证

MIT 