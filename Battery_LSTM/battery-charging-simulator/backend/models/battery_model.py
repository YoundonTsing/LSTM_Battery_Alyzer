import time
import math
import json
import numpy as np
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入配置和模型
from config import BATTERY_CONFIG, SIMULATOR_CONFIG
from models.dynamic_charging_controller import DynamicChargingController
# 从本地models目录导入database模块
from models.database import add_charging_record, update_charging_record, get_all_charging_records

class BatteryModel:
    """比亚迪秦L EV电池模型类，用于模拟电池物理特性和状态变化"""
    
    def __init__(self):
        """初始化电池模型参数"""
        # 基本参数
        self.capacity = BATTERY_CONFIG["capacity"]  # 电池容量 (Ah)
        self.nominal_voltage = BATTERY_CONFIG["nominal_voltage"]  # 标称电压 (V)
        self.max_voltage = BATTERY_CONFIG["max_voltage"]  # 最大电压 (V)
        self.min_voltage = BATTERY_CONFIG["min_voltage"]  # 最小电压 (V)
        self.max_charging_current = BATTERY_CONFIG["max_charging_current"]  # 最大充电电流 (A)
        self.max_discharging_current = BATTERY_CONFIG["max_discharging_current"]  # 最大放电电流 (A)
        
        # 充电参数
        self.cc_to_cv_voltage = BATTERY_CONFIG["cc_to_cv_voltage"]  # CC到CV切换电压 (V)
        self.cv_to_trickle_current = BATTERY_CONFIG["cv_to_trickle_current"]  # CV到涓流切换电流 (A)
        self.trickle_current = BATTERY_CONFIG["trickle_current"]  # 涓流充电电流 (A)
        self.trickle_voltage = BATTERY_CONFIG["trickle_voltage"]  # 涓流充电电压 (V)
        
        # 热特性参数
        self.thermal_capacity = BATTERY_CONFIG["thermal_capacity"]  # 热容量 (J/K)
        self.thermal_resistance = BATTERY_CONFIG["thermal_resistance"]  # 热阻 (K/W)
        self.temperature_coefficient = BATTERY_CONFIG["temperature_coefficient"]  # 温度影响系数
        
        # 戴维南等效电路模型参数
        self.internal_resistance = BATTERY_CONFIG["default_internal_resistance"]  # 欧姆内阻 R0 (Ω)
        self.polarization_resistance = BATTERY_CONFIG["polarization_resistance"]  # 极化电阻 R1 (Ω)
        self.polarization_capacitance = BATTERY_CONFIG["polarization_capacitance"]  # 极化电容 C1 (F)
        self.polarization_voltage = 0.0  # 极化电压 (V) - RC电路上的电压
        
        # 效率参数
        self.charging_efficiency = SIMULATOR_CONFIG["charging_efficiency"]  # 充电效率
        self.discharging_efficiency = SIMULATOR_CONFIG["discharging_efficiency"]  # 放电效率
        self.self_discharge_rate = SIMULATOR_CONFIG["self_discharge_rate"]  # 自放电率 (%/小时)
        
        # 可调节参数
        # self.internal_resistance = BATTERY_CONFIG["default_internal_resistance"]  # 内阻 (Ω) # This line is now redundant
        
        # 状态变量
        self.soc = 100.0  # 荷电状态 (%)
        self.voltage = self.nominal_voltage  # 当前电压 (V)
        self.current = 0.0  # 当前电流 (A)，正为充电，负为放电
        self.temperature = BATTERY_CONFIG["ambient_temperature"]  # 当前温度 (°C)
        self.ambient_temperature = BATTERY_CONFIG["ambient_temperature"]  # 环境温度 (°C)
        self.is_charging = False  # 是否正在充电
        self.is_discharging = False  # 是否正在放电
        self.charging_mode = "none"  # 充电模式：none, cc, cv, trickle
        
        # 健康状态
        self.cycle_count = SIMULATOR_CONFIG["default_cycle_count"]  # 循环次数
        self.health = 100.0  # 健康状态 (%)
        self.estimated_rul = 100.0  # 估计剩余寿命 (%)
        
        # 充电记录
        self.current_charging_record_id = None  # 当前充电记录ID
        self.current_charging_record = None  # 当前充电记录（内存中的副本）
        self.current_charging_phase = None  # 当前充电阶段
        
        # 电池历史数据
        self.battery_history = []  # 电池历史数据
        self.max_history_length = 100  # 最大历史数据长度
        
        # RUL 优化充电
        self.rul_optimized_charging = False  # 默认禁用 RUL 优化充电
        
        # 动态充电控制器
        self.dynamic_charging_controller = DynamicChargingController()
        
        # 上次更新时间
        self.last_update_time = time.time()
        
    def update(self, elapsed_time=None):
        """更新电池状态
        
        参数:
            elapsed_time: 经过的时间(秒)，如果为None则自动计算
        """
        # 计算经过的时间
        current_time = time.time()
        if elapsed_time is None:
            elapsed_time = current_time - self.last_update_time
            
        # 应用时间加速因子
        elapsed_time = elapsed_time * SIMULATOR_CONFIG["time_acceleration_factor"]
            
        self.last_update_time = current_time
        
        # 充电或放电逻辑
        if self.is_charging:
            self._update_charging(elapsed_time)
        elif self.is_discharging:
            self._update_discharging(elapsed_time)
        else:
            # 待机状态，考虑自放电
            self._update_idle(elapsed_time)
        
        # 更新电压和温度
        self._update_voltage()
        self._update_temperature(elapsed_time)
        
        # 检查电池状态边界
        self._check_boundaries()
        
        # 记录电池历史数据
        self._record_history()
        
        return self.get_state()
    
    def _record_history(self):
        """记录电池历史数据"""
        # 获取当前状态
        state = self.get_state()
        
        # 添加到历史数据
        self.battery_history.append({
            "timestamp": time.time(),
            "soc": state["soc"],
            "voltage": state["voltage"],
            "current": state["current"],
            "temperature": state["temperature"],
            "charging_mode": state["charging_mode"]
        })
        
        # 限制历史数据长度
        if len(self.battery_history) > self.max_history_length:
            self.battery_history = self.battery_history[-self.max_history_length:]
    
    def _update_charging(self, elapsed_time):
        """更新充电状态"""
        # 获取当前状态
        battery_state = self.get_state()
        
        # 根据不同的充电模式计算充电电流
        if self.charging_mode == "cc":  # 恒流充电
            # 使用动态充电控制器调整恒流充电参数
            if self.rul_optimized_charging:
                cc_params = self.dynamic_charging_controller.adjust_cc_parameters(battery_state, self.battery_history)
                self.current = cc_params["current"]
            else:
                self.current = self.max_charging_current
            
            # 检查是否需要切换到恒压充电
            if self.voltage >= self.cc_to_cv_voltage:
                self._switch_charging_mode("cv")
                
        elif self.charging_mode == "cv":  # 恒压充电
            # 使用动态充电控制器调整恒压充电参数
            if self.rul_optimized_charging:
                cv_params = self.dynamic_charging_controller.adjust_cv_parameters(battery_state, self.battery_history)
                cv_voltage = cv_params["voltage"]
            else:
                cv_voltage = self.max_voltage
            
            # 使用欧姆定律计算电流: I = (V_cv - V_oc) / R
            ocv = self._calculate_ocv_from_soc(self.soc)
            self.current = (cv_voltage - ocv) / self.internal_resistance
            self.current = max(0, min(self.current, self.max_charging_current))
            
            # 当充电电流低于3A时，切换到涓流充电
            if self.current < 3.0:
                self._switch_charging_mode("trickle")
                
        elif self.charging_mode == "trickle":  # 涓流充电
            # 使用动态充电控制器调整涓流充电参数
            if self.rul_optimized_charging:
                trickle_params = self.dynamic_charging_controller.adjust_trickle_parameters(battery_state, self.battery_history)
                self.current = trickle_params["current"]
            else:
                self.current = self.trickle_current
            
            # 如果SOC接近100%，减小涓流电流
            if self.soc > 99.0:
                self.current = self.current * (100 - self.soc) / 1.0
                
            # 如果SOC达到100%，停止充电
            if self.soc >= 99.99:
                self.stop_charging()
                return
        else:
            # 如果没有充电模式，默认进入恒流模式
            self._switch_charging_mode("cc")
            return
        
        # 计算充电能量
        energy = self.current * self.voltage * elapsed_time  # 焦耳
        
        # 更新SOC
        soc_increment = (self.current * elapsed_time / 3600) / self.capacity * 100 * self.charging_efficiency
        self.soc = min(100, self.soc + soc_increment)
        
        # 更新当前充电记录
        self._update_current_charging_record()
    
    def _update_discharging(self, elapsed_time):
        """更新放电状态"""
        # 计算放电电流 (负值表示放电)
        self.current = -self.max_discharging_current
        
        # 计算放电能量
        energy = abs(self.current) * self.voltage * elapsed_time  # 焦耳
        
        # 更新SOC
        soc_decrement = (abs(self.current) * elapsed_time / 3600) / self.capacity * 100 / self.discharging_efficiency
        self.soc = max(0, self.soc - soc_decrement)
        
        # 如果SOC过低，停止放电
        if self.soc <= 5:
            self.stop_discharging()
            
    def _update_idle(self, elapsed_time):
        """更新待机状态"""
        # 计算自放电
        hours = elapsed_time / 3600
        soc_decrement = self.self_discharge_rate * hours
        self.soc = max(0, self.soc - soc_decrement)
        self.current = 0
    
    def _update_voltage(self):
        """更新电池电压"""
        # 根据SOC计算开路电压
        ocv = self._calculate_ocv_from_soc(self.soc)
        
        # 计算时间步长 (秒)
        dt = time.time() - self.last_update_time
        if dt <= 0:
            dt = 0.1  # 防止除零错误，设置一个默认值
        
        # 更新极化电压 (RC电路动态响应)
        # 使用RC电路的微分方程解: dV/dt = (I*R1 - V)/R1C1
        # 离散化后: V(t+dt) = V(t)*exp(-dt/(R1*C1)) + R1*I*(1-exp(-dt/(R1*C1)))
        rc_time_constant = self.polarization_resistance * self.polarization_capacitance
        exp_factor = math.exp(-dt / rc_time_constant)
        
        # 计算新的极化电压
        self.polarization_voltage = self.polarization_voltage * exp_factor + \
                                   self.current * self.polarization_resistance * (1 - exp_factor)
        
        # 计算端电压 = 开路电压 + 欧姆压降 + 极化电压
        if self.is_charging:
            self.voltage = ocv + self.current * self.internal_resistance + self.polarization_voltage
        elif self.is_discharging:
            self.voltage = ocv + self.current * self.internal_resistance + self.polarization_voltage  # current是负的
        else:
            self.voltage = ocv + self.polarization_voltage  # 无电流时只有极化电压
        
        # 限制电压范围
        self.voltage = max(self.min_voltage, min(self.voltage, self.max_voltage))
    
    def _update_temperature(self, elapsed_time):
        """更新电池温度"""
        # 计算焦耳热 (包括欧姆内阻和极化电阻的热量)
        joule_heat = (self.current ** 2) * (self.internal_resistance + self.polarization_resistance * 0.5) * elapsed_time
        
        # 计算散热
        heat_dissipation = (self.temperature - self.ambient_temperature) / self.thermal_resistance * elapsed_time
        
        # 计算温度变化
        temperature_change = (joule_heat - heat_dissipation) / self.thermal_capacity
        
        # 更新温度
        self.temperature += temperature_change
        
        # 温度对内阻的影响
        temp_factor = 1 + self.temperature_coefficient * (self.temperature - 25)
        self.internal_resistance = BATTERY_CONFIG["default_internal_resistance"] * temp_factor
        self.polarization_resistance = BATTERY_CONFIG["polarization_resistance"] * temp_factor
    
    def _check_boundaries(self):
        """检查电池状态边界"""
        # SOC边界
        self.soc = max(0, min(self.soc, 100))
        
        # 电压边界
        self.voltage = max(self.min_voltage, min(self.voltage, self.max_voltage))
        
        # 电流边界
        if self.is_charging:
            self.current = max(0, min(self.current, self.max_charging_current))
        elif self.is_discharging:
            self.current = max(-self.max_discharging_current, min(self.current, 0))
    
    def _calculate_ocv_from_soc(self, soc):
        """根据SOC计算开路电压
        
        使用简化的分段线性模型
        """
        # 将SOC限制在0-100之间
        soc = max(0, min(soc, 100))
        
        # 分段线性模型
        if soc <= 10:
            # 低SOC区域
            return self.min_voltage + (self.nominal_voltage - self.min_voltage) * soc / 10
        elif soc <= 90:
            # 中SOC区域
            return self.nominal_voltage + (self.cc_to_cv_voltage - self.nominal_voltage) * (soc - 10) / 80
        else:
            # 高SOC区域
            return self.cc_to_cv_voltage + (self.max_voltage - self.cc_to_cv_voltage) * (soc - 90) / 10
    
    def _switch_charging_mode(self, mode):
        """切换充电模式
        
        参数:
            mode: 充电模式，可选值为 "none", "cc", "cv", "trickle"
        """
        # 如果是相同模式，不做改变
        if self.charging_mode == mode:
            return
        
        # 结束当前充电阶段
        if self.current_charging_phase:
            self.current_charging_phase["end_time"] = datetime.now().isoformat()
        
        # 更新充电模式
        self.charging_mode = mode
        
        # 如果不是充电状态，不创建新充电阶段
        if not self.is_charging:
            return
            
        # 创建新的充电阶段
        new_phase = {
            "phase": mode,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "initial_soc": self.soc,
            "initial_temperature": self.temperature
        }
        
        # 根据充电模式添加特定参数
        if mode == "cc":
            new_phase["cc_current"] = self.max_charging_current
        elif mode == "cv":
            new_phase["cv_voltage"] = self.cc_to_cv_voltage
        elif mode == "trickle":
            new_phase["trickle_current"] = self.trickle_current
            new_phase["trickle_voltage"] = self.trickle_voltage
            
        # 将新阶段添加到当前充电记录中
        if self.current_charging_record:
            if "charging_phases" not in self.current_charging_record:
                self.current_charging_record["charging_phases"] = []
            self.current_charging_record["charging_phases"].append(new_phase)
            self.current_charging_phase = new_phase
    
    def start_charging(self):
        """开始充电"""
        if self.is_charging:
            return None
        
        # 停止可能的放电
        if self.is_discharging:
            self.stop_discharging()
        
        # 设置充电状态
        self.is_charging = True
        
        # 创建新的充电记录
        self.current_charging_record = {
            "start_time": datetime.now().isoformat(),
            "initial_soc": self.soc,
            "initial_temperature": self.temperature,
            "initial_internal_resistance": self.internal_resistance,
            "initial_polarization_resistance": self.polarization_resistance,
            "charging_phases": []
        }
        
        # 将记录添加到数据库
        self.current_charging_record_id = add_charging_record(self.current_charging_record)
        
        # 切换到恒流充电模式
        self._switch_charging_mode("cc")
        
        return self.current_charging_record_id
    
    def stop_charging(self):
        """停止充电"""
        if not self.is_charging:
            return False
        
        # 设置充电状态
        self.is_charging = False
        self.current = 0
        
        # 结束当前充电阶段
        if self.current_charging_phase:
            self.current_charging_phase["end_time"] = datetime.now().isoformat()
            
        # 更新数据库中的充电记录
        self._update_current_charging_record(is_final=True)
        self.current_charging_record_id = None
        
        # 切换到待机模式
        self.charging_mode = "none"
        
        return True
    
    def start_discharging(self):
        """开始放电"""
        if self.is_discharging:
            return False
        
        # 停止可能的充电
        if self.is_charging:
            self.stop_charging()
        
        # 设置放电状态
        self.is_discharging = True
        self.charging_mode = "none"
        
        return True
    
    def stop_discharging(self):
        """停止放电"""
        if not self.is_discharging:
            return False
        
        # 设置放电状态
        self.is_discharging = False
        self.current = 0
        
        return True
    
    def _update_health(self):
        """更新电池健康状态"""
        # 根据循环次数计算健康状态
        cycle_degradation = SIMULATOR_CONFIG["health_degradation_per_cycle"] * self.cycle_count
        
        # 根据温度计算额外退化
        temp_degradation = 0
        if self.temperature > 45:
            temp_degradation = SIMULATOR_CONFIG["aging_model"]["temperature_aging_factor"] * (self.temperature - 45)
        
        # 计算总健康状态
        self.health = max(0, 100 - cycle_degradation - temp_degradation)
        
        # 估计RUL (简化模型，实际应使用CNN+LSTM模型)
        self.estimated_rul = self.health
    
    def update_params(self, params):
        """更新电池参数"""
        if "capacity" in params:
            self.capacity = params["capacity"]
        if "nominal_voltage" in params:
            self.nominal_voltage = params["nominal_voltage"]
        if "max_voltage" in params:
            self.max_voltage = params["max_voltage"]
        if "min_voltage" in params:
            self.min_voltage = params["min_voltage"]
        if "max_charging_current" in params:
            self.max_charging_current = params["max_charging_current"]
        if "max_discharging_current" in params:
            self.max_discharging_current = params["max_discharging_current"]
        if "internal_resistance" in params:
            self.internal_resistance = params["internal_resistance"]
        if "ambient_temperature" in params:
            self.ambient_temperature = params["ambient_temperature"]
    
    def update_charging_params(self, params):
        """更新充电参数，基于 RUL 预测结果
        
        参数:
            params: 充电参数字典
                cc_current: 恒流充电电流 (C-rate)
                cv_voltage: 恒压充电电压 (V)
                trickle_current: 涓流充电电流 (C-rate)
                termination_current: 终止电流 (C-rate)
        """
        if "cc_current" in params:
            # 将 C-rate 转换为实际电流值
            self.max_charging_current = params["cc_current"] * self.capacity
        
        if "cv_voltage" in params:
            # 更新恒压充电电压和涓流充电电压
            self.cc_to_cv_voltage = params["cv_voltage"] * 0.98  # 略低于恒压充电电压
            self.max_voltage = params["cv_voltage"]
        
        if "trickle_current" in params:
            # 更新涓流充电电流
            self.trickle_current = params["trickle_current"] * self.capacity
        
        if "termination_current" in params:
            # 更新恒压充电终止电流
            self.cv_to_trickle_current = params["termination_current"] * self.capacity
    
    def get_state(self):
        """获取电池状态"""
        # 获取时间加速因子
        time_acceleration_factor = SIMULATOR_CONFIG["time_acceleration_factor"]
        
        # 计算显示电流和电压
        display_current = self.current
        display_voltage = self.voltage
        
        # 如果是充电或放电状态，调整显示电流以反映时间加速因子
        if self.is_charging or self.is_discharging:
            display_current = self.current * time_acceleration_factor
            
            # 如果是恒压充电模式，电压保持不变
            if not (self.is_charging and self.charging_mode == "cv"):
                # 计算因电流变化导致的额外电压变化
                r_total = self.internal_resistance + self.polarization_resistance * 0.5
                delta_v = (display_current - self.current) * r_total
                display_voltage = self.voltage + delta_v
        
        return {
            "soc": self.soc,
            "voltage": self.voltage,
            "current": self.current,
            "temperature": self.temperature,
            "internal_resistance": self.internal_resistance,
            "is_charging": self.is_charging,
            "is_discharging": self.is_discharging,
            "charging_mode": self.charging_mode,
            "charging_current": max(0, self.current) if self.is_charging else 0,  # 充电电流
            "discharging_current": abs(min(0, self.current)) if self.is_discharging else 0,  # 放电电流
            "charging_voltage": self.voltage if self.is_charging else 0,
            "cycle_count": self.cycle_count,
            "health": self.health,
            "estimated_rul": self.estimated_rul,
            "ambient_temperature": self.ambient_temperature,
            
            # 添加充电控制所需参数
            "max_charging_current": self.max_charging_current,
            "cc_to_cv_voltage": self.cc_to_cv_voltage,
            "max_voltage": self.max_voltage,
            "trickle_current": self.trickle_current,
            "trickle_voltage": self.trickle_voltage,
            "polarization_resistance": self.polarization_resistance,
            "polarization_capacitance": self.polarization_capacitance,
            "polarization_voltage": self.polarization_voltage,
            
            # 添加显示电流和电压（考虑时间加速因子）
            "display_current": display_current,
            "display_voltage": display_voltage,
            "time_acceleration_factor": time_acceleration_factor,
            
            # 添加RUL优化充电状态
            "rul_optimized_charging": self.rul_optimized_charging
        }
    
    def get_charging_records(self):
        """获取充电记录"""
        return get_all_charging_records()
    
    def reset(self):
        """重置电池状态"""
        self.soc = 20.0  # 初始SOC设为20%
        self.voltage = self.nominal_voltage
        self.current = 0.0
        self.temperature = BATTERY_CONFIG["ambient_temperature"]
        self.is_charging = False
        self.is_discharging = False
        self.charging_mode = "none"
        self.internal_resistance = BATTERY_CONFIG["default_internal_resistance"]
        self.polarization_resistance = BATTERY_CONFIG["polarization_resistance"]
        self.polarization_voltage = 0.0  # 重置极化电压
        self.last_update_time = time.time()
        
        return True 

    def _update_current_charging_record(self, is_final=False):
        """更新当前充电记录到数据库"""
        if not self.current_charging_record_id:
            return

        # 获取完整的充电记录
        records = get_all_charging_records()
        current_record = next((r for r in records if r['id'] == self.current_charging_record_id), None)
        
        if not current_record:
            return

        # 更新记录
        updates = {
            'end_time': datetime.now().isoformat(),
            'final_soc': self.soc,
            'final_temperature': self.temperature,
            'charging_phases': current_record['charging_phases']
        }
        
        # 更新当前充电阶段
        if self.current_charging_phase:
            # 查找并更新阶段
            for phase in updates['charging_phases']:
                if phase['phase'] == self.current_charging_phase['phase'] and phase['end_time'] is None:
                    phase.update(self.current_charging_phase)
                    break
        
        update_charging_record(self.current_charging_record_id, updates)

        if is_final:
            # 更新循环次数和健康状态
            if updates["final_soc"] - current_record["initial_soc"] > 5:
                delta_soc = updates["final_soc"] - current_record["initial_soc"]
                self.cycle_count += delta_soc / 100
                self._update_health() 