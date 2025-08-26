import os

# 比亚迪秦L EV电池参数配置

# 服务器配置
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 电池基本参数
BATTERY_CONFIG = {
    # 电池容量 (Ah)
    "capacity": 80.0,
    
    # 电池标称电压 (V)
    "nominal_voltage": 375.0,
    
    # 电池满充电压 (V)
    "max_voltage": 400.0,
    
    # 电池截止电压 (V)
    "min_voltage": 290.0,
    
    # 最大充电电流 (A)
    "max_charging_current": 80.0,
    
    # 最大放电电流 (A)
    "max_discharging_current": 100.0,
    
    # 默认内阻 (Ω) - 戴维南模型的R0
    "default_internal_resistance": 0.100,
    
    # 极化电阻 (Ω) - 戴维南模型的R1
    "polarization_resistance": 0.050,
    
    # 极化电容 (F) - 戴维南模型的C1
    "polarization_capacitance": 1000.0,
    
    # 恒流充电阶段截止电压 (V)
    "cc_to_cv_voltage": 395.0,
    
    # 恒压充电阶段截止电流 (A)
    "cv_to_trickle_current": 5.0,
    
    # 涓流充电电流 (A)
    "trickle_current": 2.5,
    
    # 涓流充电电压 (V)
    "trickle_voltage": 400.0,
    
    # 热特性参数
    # 热容量 (J/K)
    "thermal_capacity": 1500.0,
    
    # 热阻 (K/W)
    "thermal_resistance": 0.05,
    
    # 环境温度 (°C)
    "ambient_temperature": 25.0,
    
    # 温度影响系数
    "temperature_coefficient": 0.005,
}

# 模拟器配置
SIMULATOR_CONFIG = {
    # 模拟更新间隔 (秒)
    "update_interval": 1.0,
    
    # 时间加速因子 (默认为1，表示实时模拟)
    "time_acceleration_factor": 1.0,
    
    # 充电效率
    "charging_efficiency": 0.95,
    
    # 放电效率
    "discharging_efficiency": 0.95,
    
    # 自放电率 (%/小时)
    "self_discharge_rate": 0.01,
    
    # 健康状态退化率 (%/循环)
    "health_degradation_per_cycle": 0.02,
    
    # RUL预测模型路径
    "rul_model_path": "models/battery_rul_model.h5",
    
    # 默认循环数
    "default_cycle_count": 0,
    
    # 电池老化模型参数
    "aging_model": {
        "calendar_aging_factor": 0.001,  # 日历老化因子 (%/日)
        "cycle_aging_factor": 0.005,     # 循环老化因子 (%/满循环)
        "temperature_aging_factor": 0.01  # 温度老化因子 (%/°C > 25°C)
    }
}

# WebSocket配置
WEBSOCKET_CONFIG = {
    "path": "/ws",
    "ping_interval": 25,
    "ping_timeout": 60,
    "max_clients": 50
}

# 数据库配置 (如果需要)
DATABASE_CONFIG = {
    "url": os.path.join(BASE_DIR, "backend", "db", "battery_data.db"),
    "connect_args": {"check_same_thread": False}
} 
