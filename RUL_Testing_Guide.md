# RUL优化充电策略测试指南

## 📋 测试概述

这套测试程序专门用于验证Battery LSTM项目中的RUL（剩余使用寿命）优化充电策略功能是否正常工作。

## 🎯 测试目标

- ✅ 验证RUL模型是否正确加载和激活
- ✅ 测试RUL预测功能是否准确
- ✅ 验证充电参数是否根据RUL动态调整
- ✅ 测试不同RUL条件下的策略切换
- ✅ 检查前后端集成是否正常
- ✅ 评估系统性能和稳定性

## 📁 测试脚本说明

### 1. `quick_rul_test.py` - 快速功能测试
**用途**: 快速验证核心功能是否正常
**测试项目**:
- 后端连接测试
- RUL模型状态检查
- RUL预测功能测试
- 充电参数优化测试
- 策略逻辑验证

**使用方法**:
```bash
python quick_rul_test.py [backend_url]
```

### 2. `test_charging_strategy_switch.py` - 策略切换测试
**用途**: 专门测试不同RUL条件下的充电策略切换
**测试场景**:
- 新电池（高RUL） → 标准充电模式
- 正常使用（中等RUL） → 经济充电模式
- 老化电池（低RUL） → 延寿充电模式
- 高温环境 → 保护性充电
- 高SOC状态 → 渐进式充电

**使用方法**:
```bash
python test_charging_strategy_switch.py [backend_url]
```

### 3. `test_rul_optimization_system.py` - 完整系统测试
**用途**: 全面的系统集成测试
**测试范围**:
- 模型训练和激活流程
- WebSocket实时通信
- REST API轮询备用方案
- 性能和并发测试
- 错误处理和容错性

**使用方法**:
```bash
python test_rul_optimization_system.py --backend-url http://localhost:8001
```

### 4. `run_rul_tests.py` - 测试运行器
**用途**: 统一的测试入口，自动运行所有测试并生成报告

**使用方法**:
```bash
# 运行所有测试
python run_rul_tests.py

# 只运行必需测试
python run_rul_tests.py --skip-optional

# 运行特定测试
python run_rul_tests.py --test quick
python run_rul_tests.py --test strategy
python run_rul_tests.py --test full

# 指定后端地址
python run_rul_tests.py --backend-url http://localhost:8001
```

## 🚀 快速开始

### 前提条件
1. **后端服务运行**: 确保Battery LSTM后端服务在 `http://localhost:8001` 运行
2. **前端服务运行**: 确保前端服务在 `http://localhost:5111` 运行
3. **Python环境**: Python 3.8+ 
4. **依赖包**: `pip install requests aiohttp`

### 一键测试
```bash
# 方法1: 使用测试运行器（推荐）
python run_rul_tests.py

# 方法2: 快速验证
python quick_rul_test.py

# 方法3: 详细策略测试
python test_charging_strategy_switch.py
```

## 📊 测试结果解读

### 通过标准
- ✅ **所有测试通过**: 系统工作完美，可以正常使用
- 👍 **核心测试通过**: 基本功能正常，可投入使用
- ⚠️ **部分测试失败**: 需要修复特定问题
- ❌ **大部分测试失败**: 系统存在重要问题

### 常见问题排查

#### 1. 后端连接失败
```
❌ 连接失败: Connection refused
```
**解决方案**:
- 检查后端服务是否运行: `python battery-charging-simulator/backend/server.py`
- 确认端口号是否正确（默认8001）
- 检查防火墙设置

#### 2. RUL模型未激活
```
❌ RUL模型未激活 (available: False, count: 0)
```
**解决方案**:
- 检查模型文件是否存在: `battery-charging-simulator/backend/models/`
- 运行模型训练: `python test_train_pipeline.py`
- 检查TensorFlow安装: `pip install tensorflow`

#### 3. 充电参数未调整
```
❌ 充电参数未调整
```
**解决方案**:
- 确认RUL优化已启用
- 检查是否在充电状态
- 验证RUL预测值是否正常

#### 4. WebSocket连接失败
```
❌ WebSocket连接失败
```
**解决方案**:
- 系统会自动降级到REST API轮询
- 检查Socket.IO配置
- 确认CORS设置正确

## 📈 性能基准

### 预期性能指标
- **API响应时间**: < 1秒
- **RUL预测速度**: < 2秒
- **参数调整延迟**: < 0.5秒
- **WebSocket延迟**: < 100ms
- **并发支持**: 10个并发请求

### 资源使用
- **内存占用**: < 2GB
- **CPU使用率**: < 50%
- **网络带宽**: < 1MB/s

## 🔧 自定义测试

### 添加新的测试场景
在 `test_charging_strategy_switch.py` 中添加新场景:
```python
{
    'name': '自定义场景',
    'rul': 75,
    'temp': 28,
    'soc': 45,
    'expected_strategy': 'standard',
    'expected_cc_range': (0.8, 1.0),
    'expected_max_soc': 100
}
```

### 修改测试参数
编辑各个测试脚本中的配置参数:
- 超时时间
- 重试次数
- 测试间隔
- 验证阈值

## 📄 测试报告

### 自动生成报告
测试完成后会自动生成以下报告:
- `rul_optimization_test_report.txt`: 详细测试日志
- `rul_test_report_YYYYMMDD_HHMMSS.txt`: 带时间戳的完整报告

### 报告内容
- 测试执行时间
- 每个测试项的详细结果
- 错误信息和堆栈跟踪
- 性能统计数据
- 改进建议

## 🚨 故障排除

### 调试模式
添加详细日志输出:
```bash
export PYTHONPATH="."
python -m pdb test_script.py
```

### 检查日志
查看相关日志文件:
- `rul_optimization_test.log`: 测试日志
- `battery-charging-simulator/backend/server.log`: 后端日志

### 环境验证
```bash
# 检查Python版本
python --version

# 检查依赖包
pip list | grep -E "(requests|aiohttp|tensorflow|fastapi)"

# 检查端口占用
netstat -an | grep 8001
```

## 📞 技术支持

如果遇到问题，请按以下顺序排查:
1. 查看错误信息和日志
2. 检查网络连接和服务状态
3. 验证环境配置和依赖
4. 参考本文档的故障排除部分
5. 提交Issue或寻求技术支持

---

**🔋 祝您测试顺利，RUL优化充电策略工作完美！**