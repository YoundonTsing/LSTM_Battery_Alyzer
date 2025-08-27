#!/usr/bin/env python3
"""
400V平台电压转换验证测试
验证整包电压与单体电池电压的转换逻辑
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "battery-charging-simulator", "backend"))

from config import BATTERY_CONFIG
from models.cnn_lstm_rul_model import CNNLSTM_RULModel

def test_voltage_conversion():
    """测试电压转换功能"""
    print("=" * 60)
    print("🔋 400V平台电压转换验证测试")
    print("=" * 60)
    
    # 创建RUL模型实例
    rul_model = CNNLSTM_RULModel()
    
    # 测试用例：整包电压 → 单体电压
    test_voltages = [
        290,   # 最低电压
        330,   # 低电量
        375,   # 标称电压
        395,   # CC-CV切换
        400,   # 最高电压
        410    # 过充保护
    ]
    
    print(f"\n📊 电池串联配置:")
    print(f"   串联节数: {BATTERY_CONFIG['cell_count_series']}节")
    print(f"   单体标称电压: {BATTERY_CONFIG['cell_nominal_voltage']}V")
    print(f"   单体最大电压: {BATTERY_CONFIG['cell_max_voltage']}V")
    
    print(f"\n🔄 电压转换测试:")
    print(f"{'整包电压(V)':<12} {'单体电压(V)':<12} {'状态描述':<15}")
    print("-" * 50)
    
    for pack_voltage in test_voltages:
        cell_voltage = rul_model.convert_pack_to_cell_voltage(pack_voltage)
        
        # 判断状态
        if cell_voltage < 2.9:
            status = "⚠️  深度放电"
        elif cell_voltage < 3.3:
            status = "🔴 低电量"
        elif cell_voltage < 3.8:
            status = "🟡 正常"
        elif cell_voltage < 4.0:
            status = "🟢 高电量"
        elif cell_voltage <= 4.0:
            status = "🔵 满电"
        else:
            status = "⚠️  过充风险"
            
        print(f"{pack_voltage:<12} {cell_voltage:<12.3f} {status}")
    
    # 反向转换测试
    print(f"\n🔄 反向转换测试:")
    test_cell_voltages = [2.9, 3.3, 3.75, 3.95, 4.0, 4.1]
    print(f"{'单体电压(V)':<12} {'整包电压(V)':<12} {'策略建议':<15}")
    print("-" * 50)
    
    for cell_voltage in test_cell_voltages:
        pack_voltage = rul_model.convert_cell_to_pack_voltage(cell_voltage)
        
        # 充电策略建议
        if cell_voltage < 3.3:
            strategy = "快速充电"
        elif cell_voltage < 3.8:
            strategy = "标准充电"
        elif cell_voltage < 4.0:
            strategy = "慢充保护"
        else:
            strategy = "停止充电"
            
        print(f"{cell_voltage:<12.3f} {pack_voltage:<12.0f} {strategy}")

def test_rul_strategy_with_400v():
    """测试RUL策略在400V平台下的工作"""
    print(f"\n🎯 RUL策略400V平台测试:")
    print("-" * 40)
    
    rul_model = CNNLSTM_RULModel()
    
    # 模拟不同电压状态下的电池
    test_scenarios = [
        {"voltage": 375, "soc": 50, "temp": 25, "rul": 85, "desc": "标称状态"},
        {"voltage": 395, "soc": 80, "temp": 30, "rul": 60, "desc": "接近满充"},
        {"voltage": 400, "soc": 95, "temp": 35, "rul": 40, "desc": "满充状态"},
        {"voltage": 410, "soc": 100, "temp": 40, "rul": 20, "desc": "过充风险"}
    ]
    
    for scenario in test_scenarios:
        print(f"\n📋 场景: {scenario['desc']}")
        print(f"   整包电压: {scenario['voltage']}V")
        
        battery_state = {
            "voltage": scenario['voltage'],
            "soc": scenario['soc'], 
            "temperature": scenario['temp'],
            "current": 0,
            "internal_resistance": 0.1
        }
        
        try:
            adjusted_params = rul_model.adjust_charging_parameters(battery_state, scenario['rul'])
            
            print(f"   → 充电策略: {adjusted_params['charging_strategy']}")
            print(f"   → CV电压: {adjusted_params['cv_voltage']:.1f}V")
            print(f"   → CC电流: {adjusted_params['cc_current']:.2f}C")
            print(f"   → 最大SOC: {adjusted_params['max_soc']}%")
            
        except Exception as e:
            print(f"   ❌ 策略计算失败: {e}")

if __name__ == "__main__":
    test_voltage_conversion()
    test_rul_strategy_with_400v()
    print("\n" + "=" * 60)
    print("✅ 400V平台转换测试完成")
    print("=" * 60)