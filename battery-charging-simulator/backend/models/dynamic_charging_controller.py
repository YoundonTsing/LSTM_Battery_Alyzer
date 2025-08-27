import os
import numpy as np
import logging

# 添加TensorFlow导入的异常处理
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError as e:
    logging.getLogger("battery-simulator").warning(f"TensorFlow 导入失败: {e}，将使用简单估计方法")
    TF_AVAILABLE = False

import pandas as pd

logger = logging.getLogger("battery-simulator")

class DynamicChargingController:
    """动态充电控制器，基于CNN+LSTM模型的学习结果调整充电参数"""
    
    def __init__(self, model_path=None):
        """初始化动态充电控制器
        
        参数:
            model_path: 预训练模型路径
        """
        self.model = None
        self.model_path = model_path or os.path.join("C:", "Projects", "Battery_LSTM", 
                                                    "RUL_prediction", "saved", "fusion", 
                                                    "new_prep", "V_CNN+C_LSTM_5_B05_k1", 
                                                    "saved_model_and_weight.keras")
        
        # 特征缩放器
        self.scalers = {
            "voltage": None,
            "current": None,
            "soc": None,
            "temperature": None
        }
        
        # 序列长度
        self.seq_len = 5
        
        # 加载模型
        if TF_AVAILABLE:
            self._load_model()
        else:
            logger.warning("TensorFlow不可用，将使用简单估计方法进行充电控制")
    
    def _load_model(self):
        """加载预训练模型"""
        if not TF_AVAILABLE:
            logger.warning("TensorFlow不可用，无法加载模型")
            return
            
        try:
            if os.path.exists(self.model_path):
                self.model = load_model(self.model_path)
                logger.info(f"成功加载动态充电控制模型: {self.model_path}")
            else:
                logger.warning(f"模型文件不存在: {self.model_path}")
        except Exception as e:
            logger.error(f"加载动态充电控制模型失败: {e}")
    
    def adjust_cc_parameters(self, battery_state, battery_history):
        """调整恒流充电参数
        
        参数:
            battery_state: 电池当前状态
            battery_history: 电池历史数据
            
        返回:
            adjusted_params: 调整后的恒流充电参数
        """
        # 默认参数
        default_params = {
            "current": battery_state["max_charging_current"],
        }
        
        # 如果没有足够的历史数据或模型未加载，返回默认参数
        if len(battery_history) < self.seq_len or self.model is None:
            return default_params
        
        try:
            # 提取特征
            soc = battery_state["soc"]
            
            # 根据SOC动态调整充电电流
            # 在SOC较低时使用较大电流，SOC较高时逐渐降低电流
            if soc < 20:
                # SOC较低，使用最大充电电流
                current = default_params["current"]
            elif soc < 80:
                # SOC中等，线性降低充电电流
                current = default_params["current"] * (1.0 - (soc - 20) / 60 * 0.3)
            else:
                # SOC较高，使用较小充电电流
                current = default_params["current"] * 0.7
            
            # 根据温度进一步调整电流
            temperature = battery_state["temperature"]
            if temperature > 40:
                # 温度过高，降低充电电流
                # 当温度从 40°C 上升到 60°C 时，电流从 100% 线性降低到 10%
                # 超过 60°C 后，电流保持在 10%
                reduction_factor = (temperature - 40) / 20.0
                # 将电流降低到最低 10%，而不是完全降为0
                temp_factor = max(0.1, 1.0 - reduction_factor * 0.9)
                current *= temp_factor
            
            # 增加阶梯变换：将电流值量化到最接近的整数安培
            current = round(current)
            
            return {"current": current}
            
        except Exception as e:
            logger.error(f"调整恒流充电参数失败: {e}")
            return default_params
    
    def adjust_cv_parameters(self, battery_state, battery_history):
        """调整恒压充电参数
        
        参数:
            battery_state: 电池当前状态
            battery_history: 电池历史数据
            
        返回:
            adjusted_params: 调整后的恒压充电参数
        """
        # 默认参数
        default_params = {
            "voltage": battery_state["max_voltage"],
        }
        
        # 如果没有足够的历史数据或模型未加载，返回默认参数
        if len(battery_history) < self.seq_len or self.model is None:
            return default_params
        
        try:
            # 提取特征
            soc = battery_state["soc"]
            health = battery_state["health"]
            
            # 根据电池健康状态调整恒压充电电压
            # 健康状态越差，恒压充电电压越低
            base_voltage = default_params["voltage"]
            health_factor = health / 100.0
            
            # 调整电压，健康状态越低，电压越低
            adjusted_voltage = base_voltage * (0.95 + 0.05 * health_factor)
            
            # 确保电压不超过最大安全电压
            adjusted_voltage = min(adjusted_voltage, battery_state["max_voltage"] * 0.98)
            
            return {"voltage": adjusted_voltage}
            
        except Exception as e:
            logger.error(f"调整恒压充电参数失败: {e}")
            return default_params
    
    def adjust_trickle_parameters(self, battery_state, battery_history):
        """调整涓流充电参数
        
        参数:
            battery_state: 电池当前状态
            battery_history: 电池历史数据
            
        返回:
            adjusted_params: 调整后的涓流充电参数
        """
        # 默认参数
        default_params = {
            "current": battery_state["trickle_current"],
            "voltage": battery_state["trickle_voltage"]
        }
        
        # 如果没有足够的历史数据或模型未加载，返回默认参数
        if len(battery_history) < self.seq_len or self.model is None:
            return default_params
        
        try:
            # 提取特征
            soc = battery_state["soc"]
            health = battery_state["health"]
            
            # 根据SOC和健康状态调整涓流充电电流
            base_current = default_params["current"]
            
            # SOC越高，涓流电流越小
            soc_factor = 1.0 - (soc - 98) / 2 * 0.5  # 98%-100%范围内
            soc_factor = max(0.5, min(1.0, soc_factor))
            
            # 健康状态越差，涓流电流越小
            health_factor = health / 100.0
            
            adjusted_current = base_current * soc_factor * (0.8 + 0.2 * health_factor)
            
            return {
                "current": adjusted_current,
                "voltage": default_params["voltage"]
            }
            
        except Exception as e:
            logger.error(f"调整涓流充电参数失败: {e}")
            return default_params 