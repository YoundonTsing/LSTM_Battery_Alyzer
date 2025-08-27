# 🚀 安装指南

本文档提供了 LSTM Battery Analyzer 项目的详细安装说明。

## 📋 系统要求

### 最低要求
- **Python**: 3.8 或更高版本
- **内存**: 4GB RAM（推荐 8GB+）
- **存储**: 2GB 可用空间
- **操作系统**: Windows 10+, macOS 10.14+, 或 Linux

### 推荐配置
- **Python**: 3.9 或 3.10
- **内存**: 16GB RAM
- **GPU**: NVIDIA GPU（支持CUDA 11.2+）用于模型训练加速
- **存储**: SSD，5GB+ 可用空间

## 🛠️ 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/LSTM_Battery_Analyzer.git
cd LSTM_Battery_Analyzer
```

### 2. 创建虚拟环境
```bash
# 使用 venv
python -m venv battery_env

# 激活虚拟环境
# Windows:
battery_env\Scripts\activate
# macOS/Linux:
source battery_env/bin/activate
```

### 3. 升级pip
```bash
python -m pip install --upgrade pip
```

### 4. 安装依赖包

#### 基础安装（仅运行项目）
```bash
pip install -r requirements.txt
```

#### 开发环境安装（包含测试和开发工具）
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

#### GPU支持安装（可选）
如果您有NVIDIA GPU并希望加速模型训练：
```bash
# 首先安装CUDA和cuDNN（访问NVIDIA官网下载）
# 然后安装GPU版本的TensorFlow
pip install tensorflow-gpu>=2.13.0
```

### 5. 验证安装
```bash
# 检查Python版本
python --version

# 检查关键包安装
python -c "import tensorflow as tf; print('TensorFlow版本:', tf.__version__)"
python -c "import fastapi; print('FastAPI安装成功')"
python -c "import numpy as np; print('NumPy版本:', np.__version__)"
```

## 🏃 运行项目

### 启动后端服务
```bash
cd battery-charging-simulator/backend
python server.py
```
服务将在 `http://localhost:8001` 启动

### 启动前端服务
```bash
cd battery-charging-simulator/frontend
npm install
npm run dev
```
前端将在 `http://localhost:5111` 启动

### 访问应用
打开浏览器访问: `http://localhost:5111`

## 🧪 运行测试

### 快速功能测试
```bash
# 测试RUL优化功能
python test_rul_auto_enable.py

# 测试系统集成
python test_rul_optimization_system.py
```

### 完整测试套件（开发环境）
```bash
pytest tests/ -v --cov=battery-charging-simulator
```

## 🐛 常见问题

### TensorFlow安装问题

**问题**: TensorFlow安装失败
```bash
# 解决方案1：使用conda安装
conda install tensorflow

# 解决方案2：使用特定版本
pip install tensorflow==2.13.0

# 解决方案3：使用CPU版本
pip install tensorflow-cpu
```

**问题**: GPU未被识别
```bash
# 检查GPU支持
python -c "import tensorflow as tf; print('GPU可用:', tf.config.list_physical_devices('GPU'))"

# 如果为空，检查CUDA安装
nvidia-smi
```

### 内存不足问题

**问题**: 训练时内存不足
```python
# 在训练脚本中添加内存限制
import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    tf.config.experimental.set_memory_growth(gpus[0], True)
```

### 端口冲突问题

**问题**: 端口8001或5111被占用
```bash
# 检查端口使用
netstat -ano | findstr :8001  # Windows
lsof -i :8001                 # macOS/Linux

# 修改配置文件中的端口号
# backend/config.py: SERVER_PORT = 8002
# frontend/vite.config.js: port: 5112
```

### 依赖版本冲突

**问题**: 包版本不兼容
```bash
# 创建新的虚拟环境
python -m venv fresh_env
source fresh_env/bin/activate  # or fresh_env\Scripts\activate

# 重新安装
pip install -r requirements.txt
```

## 🔧 开发环境设置

### VSCode配置
1. 安装推荐扩展：
   - Python
   - Vue Language Features (Volar)
   - Pylance

2. 配置工作区设置 (`.vscode/settings.json`)：
```json
{
    "python.defaultInterpreterPath": "./battery_env/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black"
}
```

### Git钩子设置
```bash
# 安装pre-commit钩子
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

## 📦 Docker部署（可选）

### 构建Docker镜像
```bash
# 后端
docker build -t battery-analyzer-backend ./battery-charging-simulator/backend

# 前端
docker build -t battery-analyzer-frontend ./battery-charging-simulator/frontend
```

### 使用Docker Compose
```bash
docker-compose up -d
```

## 🆘 获取帮助

如果遇到安装问题：

1. **检查系统要求**：确保满足最低系统要求
2. **查看日志**：检查安装过程中的错误信息
3. **搜索Issues**：在GitHub仓库中搜索类似问题
4. **提交Issue**：提供详细的错误信息和系统配置

**联系方式**:
- GitHub Issues: [项目Issues页面]
- 邮箱: your.email@example.com

---

🎉 **安装完成后，您就可以开始探索电池管理算法的世界了！**