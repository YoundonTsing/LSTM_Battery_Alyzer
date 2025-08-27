# 400V电池平台串联架构转换方案

## 1. 系统架构分析

### 当前配置
- **整包电压**: 290V - 400V
- **标称电压**: 375V  
- **电池容量**: 80Ah
- **充电电流**: 80A

### 单体电池规格（推算）
- **单体电压范围**: 2.9V - 4.0V
- **单体标称电压**: 3.75V
- **串联节数**: 375V ÷ 3.75V = **100节串联**
- **单体容量**: 80Ah（串联不改变容量）

## 2. 电压转换公式

### 核心转换关系
```
单体等效电压 = 整包电压 ÷ 串联节数
串联节数 = 100节（固定）
```

### 关键电压点转换
| 整包电压 | 单体等效电压 | 充电阶段 |
|---------|-------------|----------|
| 290V | 2.90V | 深度放电 |
| 330V | 3.30V | 低电量 |
| 375V | 3.75V | 标称电压 |
| 395V | 3.95V | CC→CV切换 |
| 400V | 4.00V | 满充电压 |

## 3. RUL策略适配方案

### 方案A：电压转换法（推荐）
在RUL策略算法中加入转换层：
```python
def convert_pack_to_cell_voltage(pack_voltage, cell_count=100):
    """将整包电压转换为单体电池等效电压"""
    return pack_voltage / cell_count

def adjust_charging_parameters(self, battery_state, rul_percentage):
    # 获取整包电压
    pack_voltage = battery_state.get("voltage", 375.0)
    
    # 转换为单体等效电压进行策略判断
    cell_voltage = convert_pack_to_cell_voltage(pack_voltage)
    
    # 使用单体电压进行RUL策略决策
    if cell_voltage > 4.1:  # 对应410V整包
        voltage_factor = 0.8
    elif cell_voltage > 4.0:  # 对应400V整包  
        voltage_factor = 0.9
```

### 方案B：参数重新校准法
直接修改策略参数适配400V：
```python
default_params = {
    "cv_voltage": 400.0,      # 恒压充电 400V (整包)
    "cc_to_cv_voltage": 395.0 # CC-CV切换 395V
}

# 电压因子判断（400V范围）
if voltage > 410:  # 高电压保护
    voltage_factor = 0.8
elif voltage > 400:  # 接近满充
    voltage_factor = 0.9
```

## 4. 实施建议

### 推荐：方案A（电压转换法）
**优势**：
- 保持RUL模型训练数据的一致性
- CNN+LSTM模型仍基于单体电池特征
- 便于未来支持不同串联配置

**实施步骤**：
1. 在配置中定义串联节数
2. 创建电压转换工具函数  
3. 修改RUL策略算法调用转换函数
4. 更新参数生成逻辑返回整包电压值

### 配置增强
```python
BATTERY_CONFIG = {
    # ... 现有配置 ...
    
    # 新增串联架构参数
    "cell_count_series": 100,        # 串联节数
    "cell_nominal_voltage": 3.75,    # 单体标称电压
    "cell_max_voltage": 4.0,         # 单体最大电压
    "cell_min_voltage": 2.9,         # 单体最小电压
}
```