# 🔋 LSTM Battery Analyzer

**基于数字孪生技术的电动车电池算法研究平台**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Vue.js 3.x](https://img.shields.io/badge/vue.js-3.x-green.svg)](https://vuejs.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange.svg)](https://tensorflow.org/)

> 一个集成了CNN+LSTM深度学习模型的电池剩余使用寿命(RUL)预测与智能充电优化系统，实时仿真、动态参数调控和充电策略智能优化。

## 🎯 项目概述

**LSTM Battery Analyzer** 是一个基于数字孪生技术的电动车电池管理研究平台，专门用于：

- 🧠 **智能RUL预测**：基于CNN+LSTM混合深度学习模型预测电池剩余使用寿命
- ⚡ **动态充电优化**：根据电池健康状态实时调整充电参数
- 🔬 **电池行为仿真**：高精度电池充放电过程数字化建模
- 📊 **数据可视化分析**：实时监控电池状态并生成详细分析报告
- 🚀 **算法研究平台**：为电池管理算法研究提供完整的实验环境

## ✨ 核心特性

### 🤖 智能预测系统
- **多模态深度学习**：CNN提取充电曲线空间特征，LSTM捕获时序依赖关系
- **多模型集成**：K折交叉验证生成的多个模型提高预测准确性
- **实时健康评估**：基于电压、电流、温度、容量等多维数据的健康状态评估

### ⚡ 动态充电控制
- **多阶段充电管理**：恒流(CC) → 恒压(CV) → 涓流充电的智能切换
- **参数自适应调节**：根据RUL预测结果动态调整充电电流和电压
- **充电策略优化**：支持保守、平衡、激进等多种充电策略

### 🔋 高精度电池建模
- **400V高压平台适配**：支持现代电动车高压电池系统
- **戴维南等效模型**：包含内阻、极化效应的高精度电池物理模型
- **热管理仿真**：考虑温度对电池性能的影响

### 📊 全方位数据分析
- **实时状态监控**：SOC、电压、电流、温度等关键参数实时显示
- **充电记录管理**：详细记录每次充电过程的各阶段数据
- **统计分析报告**：生成充电效率、电池健康等分析报告

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vue.js)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Dashboard   │ │ Statistics  │ │ Health      │           │
│  │ 实时监控      │ │ 数据分析     │ │ 健康评估     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket + REST API
┌─────────────────────┴───────────────────────────────────────┐
│                  Backend (FastAPI)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Battery     │ │ RUL         │ │ Charging    │           │
│  │ Model       │ │ Predictor   │ │ Controller  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Database    │ │ API         │ │ WebSocket   │           │
│  │ (SQLite)    │ │ Handler     │ │ Handler     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```



<img width="1099" height="878" alt="wechat_2025-08-28_151956_198" src="https://github.com/user-attachments/assets/4f4fef38-24eb-4129-9b61-a2f75bae743b" />








<img width="1024" height="888" alt="wechat_2025-08-28_162912_418" src="https://github.com/user-attachments/assets/5927afec-7dce-4add-8c8a-eb03df845b7b" />








<img width="1081" height="886" alt="wechat_2025-08-28_162948_225" src="https://github.com/user-attachments/assets/4f57cfcd-2c24-485c-a697-5c757e45648a" />







## 🛠️ 技术栈

### 前端技术
- **框架**: Vue.js 3.x + Vite
- **UI组件**: 自定义组件库
- **数据可视化**: Chart.js + Vue-Chartjs
- **实时通信**: Socket.IO Client
- **样式**: CSS3 + 响应式设计

### 后端技术
- **Web框架**: FastAPI
- **异步处理**: Uvicorn + AsyncIO
- **实时通信**: Python-SocketIO
- **机器学习**: TensorFlow/Keras + PyTorch
- **数据处理**: NumPy + Pandas + Scikit-learn
- **数据存储**: SQLite

### 核心算法
- **深度学习模型**: CNN+LSTM混合神经网络
- **电池模型**: 戴维南等效电路模型
- **优化算法**: 动态参数调控算法
- **信号处理**: 时序数据预处理和特征提取

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 14+
- Git

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/LSTM_Battery_Analyzer.git
cd LSTM_Battery_Analyzer
```

### 2. 后端设置
```bash
# 创建虚拟环境
python -m venv battery_env
source battery_env/bin/activate  # Windows: battery_env\Scripts\activate

# 安装依赖
cd battery-charging-simulator/backend
pip install -r requirements.txt

# 启动后端服务
python server.py
```
后端服务运行在: `http://localhost:8001`

### 3. 前端设置
```bash
# 安装依赖
cd battery-charging-simulator/frontend
npm install

# 启动开发服务器
npm run dev
```
前端服务运行在: `http://localhost:5111`

### 4. 访问应用
打开浏览器访问 `http://localhost:5111`，您将看到电池仿真器界面。

## 📖 使用指南

### 🔥 基础操作

1. **启动仿真**
   - 访问仪表板页面
   - 观察实时电池状态（SOC、电压、电流、温度）
   - 系统默认启用RUL优化充电

2. **开始充电**
   - 点击"开始充电"按钮
   - 观察充电过程的三个阶段切换
   - 实时查看优化的充电参数

3. **查看数据分析**
   - 切换到"充电统计"页面
   - 查看详细的充电记录和阶段分析
   - 分析充电效率和电池健康状况

### 🧠 RUL模型训练

1. **数据准备**
   ```
   data/
   ├── charge/
   │   ├── train/  # 训练集充电数据 (CSV格式)
   │   └── test/   # 测试集充电数据
   └── discharge/
       ├── train/  # 训练集放电数据 (容量信息)
       └── test/   # 测试集放电数据
   ```

2. **模型训练**
   ```bash
   cd RUL_prediction/train
   python MC-SCNN+LSTM.py  # 运行混合CNN-LSTM模型训练
   ```

3. **模型激活**
   - 训练完成后，模型自动保存到 `models/` 目录
   - 系统自动加载最新模型用于RUL预测
   - 前端显示模型激活状态

### ⚙️ 高级配置

#### 电池参数配置 (`backend/config.py`)
```python
BATTERY_CONFIG = {
    "capacity": 80.0,              # 电池容量 (Ah)
    "max_voltage": 400.0,          # 最大电压 (V)
    "max_charging_current": 80.0,  # 最大充电电流 (A)
    "cell_count_series": 100,      # 串联电池节数
    # ... 更多参数
}
```

#### 训练参数配置 (`RUL_prediction/train/param_*.py`)
```python
params = {
    'lr': 0.001,           # 学习率
    'batch_size': 32,      # 批次大小
    'epochs': 100,         # 训练轮数
    'seq_len_lstm': 20,    # LSTM序列长度
    'seq_len_cnn': 100,    # CNN序列长度
}
```

## 🔌 API 文档

### REST API

#### 电池状态
```http
GET /api/status
```
获取当前电池状态和RUL预测结果

#### 充电控制
```http
POST /api/charge/start
POST /api/charge/stop
```
开始/停止充电

#### RUL优化
```http
POST /api/simulator/rul-optimization
Content-Type: application/json

{
  "enable": true
}
```

### WebSocket 事件

#### 订阅电池状态更新
```javascript
socket.on('battery_state_update', (data) => {
  console.log('电池状态:', data);
});
```

#### 充电控制
```javascript
socket.emit('charging_control', {
  action: 'start_charging'
});
```

更多API详情请参考 `docs/api.md`

## 📊 性能指标

### 模型性能
- **RUL预测精度**: MAE < 5%
- **实时处理能力**: < 100ms响应时间
- **模型大小**: < 50MB

### 系统性能
- **并发用户**: 支持10+并发连接
- **数据更新频率**: 1Hz实时更新
- **内存占用**: < 500MB

## 🧪 测试

### 运行测试套件
```bash
# RUL优化系统测试
python test_rul_optimization_system.py

# 充电统计功能测试
python test_rul_auto_enable.py

# 400V平台转换测试
python test_400v_platform_conversion.py
```

### 测试覆盖
- ✅ RUL模型激活和预测
- ✅ 充电参数动态调控
- ✅ 策略切换逻辑
- ✅ WebSocket实时通信
- ✅ 数据库操作
- ✅ 前端状态同步

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范
- 遵循 PEP 8 Python代码规范
- 前端代码遵循 Vue.js 官方风格指南
- 提交前运行测试套件
- 添加必要的单元测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- NASA电池数据集提供的研究数据支持
- TensorFlow/Keras社区的深度学习框架支持
- Vue.js社区的前端框架支持
- 电池管理系统研究领域的相关学术工作

## 📞 联系方式

- **项目维护者**: [YoundonTsing]
- **邮箱**: 1939194239@qq.com
- **项目主页**: https://github.com/YoundonTsing/LSTM_Battery_Analyzer

## 🗺️ 路线图

### v2.0 计划功能
- [ ] 多电池包并联仿真
- [ ] 云端模型训练平台
- [ ] 移动端应用支持
- [ ] 更多电池化学类型支持
- [ ] 集成更多机器学习算法

### v1.1 即将发布
- [x] RUL优化充电自动启用
- [x] 400V高压平台适配
- [x] 充电统计数据完善
- [x] 前端数据可视化增强

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！

🔬 **让我们一起推动电池技术的发展！**
