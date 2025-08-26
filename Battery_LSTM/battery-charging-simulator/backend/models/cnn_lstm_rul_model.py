import os
import numpy as np
import logging
import shutil
import time # Added for evaluate_battery_health

# 添加TensorFlow导入的异常处理
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from tensorflow.keras.layers import Dense, LSTM, Conv1D, Flatten, Input, concatenate
    from tensorflow.keras.models import Model
    TF_AVAILABLE = True
except ImportError as e:
    logging.getLogger("battery-simulator").warning(f"TensorFlow 导入失败: {e}，将使用简单估计方法")
    TF_AVAILABLE = False

from sklearn.preprocessing import MinMaxScaler
import pandas as pd

logger = logging.getLogger("battery-simulator")

# 预训练模型路径
PRETRAINED_MODEL_PATHS = [
    "C:/Projects/Battery_LSTM/RUL_prediction/saved/fusion/new_prep/V_CNN+C_LSTM_5_B05_k1/saved_model_and_weight.keras",
    "C:/Projects/Battery_LSTM/RUL_prediction/saved/fusion/new_prep/V_CNN+C_LSTM_5_B05_k2/saved_model_and_weight.keras",
    "C:/Projects/Battery_LSTM/RUL_prediction/saved/fusion/new_prep/V_CNN+C_LSTM_5_B05_k3/saved_model_and_weight.keras"
]

class CNNLSTM_RULModel:
    """CNN+LSTM 混合模型用于电池 RUL 预测"""
    
    def __init__(self, model_path=None):
        """初始化 CNN+LSTM RUL 模型
        
        参数:
            model_path: 预训练模型路径，如果为 None 则尝试使用预定义路径
        """
        self.model = None
        self.models = []  # 用于存储多个模型（K折交叉验证）
        
        # 如果未指定模型路径，使用默认路径
        if model_path is None:
            self.model_path = os.path.join("models", "cnn_lstm_rul_model.keras")
            # 尝试复制预训练模型
            self._copy_pretrained_models()
        else:
            self.model_path = model_path
            
        self.scalers = {
            "voltage": MinMaxScaler(feature_range=(0, 1)),
            "current": MinMaxScaler(feature_range=(0, 1)),
            "temperature": MinMaxScaler(feature_range=(0, 1)),
            "capacity": MinMaxScaler(feature_range=(0, 1))
        }
        self.seq_len_lstm = 5  # 时间步长或历史窗口大小
        self.seq_len_cnn = 5   # CNN 序列长度
        self.is_trained = False
        
        try:
            if TF_AVAILABLE:
                self._load_or_create_model()
            else:
                logger.warning("TensorFlow不可用，将使用简单估计方法")
        except Exception as e:
            logger.error(f"加载 CNN+LSTM RUL 模型失败: {e}")
            logger.warning("将使用简单估计方法代替")
    
    def _copy_pretrained_models(self):
        """复制预训练模型到本地models目录"""
        # 确保models目录存在
        os.makedirs("models", exist_ok=True)
        
        # 尝试复制预训练模型
        for i, model_path in enumerate(PRETRAINED_MODEL_PATHS):
            if os.path.exists(model_path):
                target_path = os.path.join("models", f"cnn_lstm_rul_model_k{i+1}.keras")
                try:
                    shutil.copy2(model_path, target_path)
                    logger.info(f"已复制预训练模型: {model_path} -> {target_path}")
                except Exception as e:
                    logger.error(f"复制预训练模型失败: {e}")
    
    def _load_or_create_model(self):
        """加载已有模型或创建新模型"""
        # 如果TensorFlow不可用，直接返回
        if not TF_AVAILABLE:
            logger.warning("TensorFlow不可用，无法加载或创建模型")
            return
            
        try:
            # 尝试加载多个模型（K折交叉验证）
            models_loaded = False
            
            # 首先尝试从本地models目录加载
            for i in range(1, 4):  # 假设有3个K折模型
                model_path = os.path.join("models", f"cnn_lstm_rul_model_k{i}.keras")
                if os.path.exists(model_path):
                    try:
                        model = load_model(model_path)
                        self.models.append(model)
                        logger.info(f"成功从本地加载 CNN+LSTM RUL 预测模型: {model_path}")
                        models_loaded = True
                    except Exception as e:
                        logger.error(f"加载本地模型 {model_path} 失败: {e}")
            
            # 如果本地加载失败，尝试直接从原始预训练路径加载
            if not models_loaded:
                logger.info("尝试从原始预训练路径加载模型")
                for i, model_path in enumerate(PRETRAINED_MODEL_PATHS):
                    if os.path.exists(model_path):
                        try:
                            model = load_model(model_path)
                            self.models.append(model)
                            # 同时保存到本地
                            target_path = os.path.join("models", f"cnn_lstm_rul_model_k{i+1}.keras")
                            model.save(target_path)
                            logger.info(f"成功从原始路径加载并保存模型: {model_path} -> {target_path}")
                            models_loaded = True
                        except Exception as e:
                            logger.error(f"加载原始模型 {model_path} 失败: {e}")
            
            # 如果成功加载了至少一个模型，设置主模型为第一个
            if models_loaded and self.models:
                self.model = self.models[0]
                self.is_trained = True
                logger.info(f"成功加载了 {len(self.models)} 个模型用于集成预测")
                return
                
            # 如果没有加载到K折模型，尝试加载单个模型
            if os.path.exists(self.model_path):
                # 加载已有模型
                self.model = load_model(self.model_path)
                self.models = [self.model]  # 也添加到模型列表中
                logger.info(f"成功加载 CNN+LSTM RUL 预测模型: {self.model_path}")
                self.is_trained = True
            else:
                # 创建新模型
                self._create_model()
                logger.info(f"创建新的 CNN+LSTM RUL 预测模型")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self._create_model()
    
    def _create_model(self):
        """创建 CNN+LSTM 混合模型用于 RUL 预测"""
        # 如果TensorFlow不可用，直接返回
        if not TF_AVAILABLE:
            logger.warning("TensorFlow不可用，无法创建模型")
            return
            
        # 输入形状: [样本数, 时间步, 特征数]
        seq_len_lstm = self.seq_len_lstm
        seq_len_cnn = self.seq_len_cnn
        
        # 定义输入
        input_CNN = Input(shape=(seq_len_cnn, 1), name="CNN_Input")  # 电压数据
        input_LSTM = Input(shape=(seq_len_lstm, 1), name="LSTM_Input")  # 容量数据
        
        # LSTM 分支处理容量数据
        lstm_layer = LSTM(32, activation='tanh', return_sequences=True, name="LSTM_layer")(input_LSTM)
        
        # CNN 分支处理电压数据
        cnn_layer = Conv1D(32, 5, activation='relu', strides=1, padding="same", name="CNN_layer")(input_CNN)
        
        # 合并两个分支
        concat = concatenate([lstm_layer, cnn_layer])
        
        # 展平并进行预测
        flat = Flatten()(concat)
        hidden = Dense(32, activation='relu', name="predictor")(flat)
        output = Dense(1, name="Output")(hidden)
        
        # 创建模型
        self.model = Model(inputs=[input_LSTM, input_CNN], outputs=[output])
        
        # 编译模型
        self.model.compile(
            optimizer='adam',
            loss='mse'
        )
        
        self.is_trained = False
    
    def _preprocess_data(self, data, scaler_type):
        """预处理数据
        
        参数:
            data: 需要预处理的数据
            scaler_type: 缩放器类型 ('voltage', 'current', 'temperature', 'capacity')
            
        返回:
            scaled_data: 缩放后的数据
        """
        scaler = self.scalers[scaler_type]
        
        # 如果数据是一维的，转换为二维
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        # 如果缩放器未拟合，则进行拟合
        if not hasattr(scaler, 'n_features_in_'):
            scaler.fit(data)
        
        scaled_data = scaler.transform(data)
        return scaled_data
    
    def _prepare_sequence_data(self, voltage_data, capacity_data):
        """准备序列数据用于 CNN+LSTM 模型
        
        参数:
            voltage_data: 电压数据
            capacity_data: 容量数据
            
        返回:
            lstm_input: LSTM 输入序列
            cnn_input: CNN 输入序列
        """
        # 确保数据长度足够
        if len(voltage_data) < self.seq_len_cnn or len(capacity_data) < self.seq_len_lstm:
            raise ValueError("数据长度不足以创建序列")
        
        # 使用最近的数据
        recent_voltage = voltage_data[-self.seq_len_cnn:]
        recent_capacity = capacity_data[-self.seq_len_lstm:]
        
        # 预处理数据
        scaled_voltage = self._preprocess_data(recent_voltage, 'voltage')
        scaled_capacity = self._preprocess_data(recent_capacity, 'capacity')
        
        # 调整维度以匹配模型输入
        lstm_input = np.expand_dims(scaled_capacity, axis=0)  # [1, seq_len_lstm, 1]
        
        # 对于CNN输入，我们需要将其扩展为10个特征
        # 这里我们可以通过复制或者特征工程来实现
        # 方法1：复制同一特征10次
        expanded_voltage = np.repeat(scaled_voltage, 10, axis=1).reshape(1, self.seq_len_cnn, 10)
        
        # 方法2：如果有其他特征可用，可以组合它们
        # 例如，可以使用电压、电流、温度等特征
        # 这里我们使用方法1，简单复制
        cnn_input = expanded_voltage
        
        logger.debug(f"LSTM输入形状: {lstm_input.shape}, CNN输入形状: {cnn_input.shape}")
        
        return lstm_input, cnn_input
    
    def predict_rul(self, battery_data, static_features):
        """预测电池剩余寿命
        
        参数:
            battery_data: 电池历史数据 (电压、电流、温度等)
            static_features: 静态特征 [cycle_count, health, avg_temperature]
            
        返回:
            rul: 预测的剩余寿命 (循环数)
        """
        # 如果TensorFlow不可用或模型未训练，使用简单估计方法
        if not TF_AVAILABLE or not self.is_trained or not self.models:
            logger.warning("模型未训练或不可用，使用简单估计方法")
            return self._simple_estimate(static_features)
        
        try:
            # 从电池历史数据中提取电压和容量
            if len(battery_data) < max(self.seq_len_cnn, self.seq_len_lstm):
                logger.warning("历史数据不足，使用简单估计方法")
                return self._simple_estimate(static_features)
            
            # 提取电压和容量数据
            voltage_data = np.array([data["voltage"] for data in battery_data])
            
            # 由于我们可能没有直接的容量数据，使用 SOC 和电压关系估计
            capacity_data = np.array([data["soc"] / 100.0 for data in battery_data])
            
            # 准备序列数据
            lstm_input, cnn_input = self._prepare_sequence_data(voltage_data, capacity_data)
            
            # 使用所有模型进行预测并取平均值（集成预测）
            predictions = []
            confidence_scores = []
            
            for i, model in enumerate(self.models):
                # 预测
                pred = model.predict([lstm_input, cnn_input], verbose=0)[0][0]
                predictions.append(pred)
                
                # 计算简单的置信度分数 (基于预测值与均值的接近程度)
                if len(predictions) > 1:
                    mean_pred = np.mean(predictions[:-1])  # 不包括当前预测
                    diff = abs(pred - mean_pred)
                    confidence = max(0, 1 - (diff / max(0.1, mean_pred)))  # 避免除以零
                else:
                    confidence = 0.8  # 第一个模型的默认置信度
                
                confidence_scores.append(confidence)
                logger.debug(f"模型 {i+1} 预测值: {pred:.4f}, 置信度: {confidence:.2f}")
            
            # 计算加权平均预测值
            if len(predictions) > 1:
                total_confidence = sum(confidence_scores)
                if total_confidence > 0:
                    # 加权平均
                    avg_prediction = sum(p * c for p, c in zip(predictions, confidence_scores)) / total_confidence
                else:
                    # 简单平均
                    avg_prediction = np.mean(predictions)
            else:
                avg_prediction = predictions[0]
                
            logger.debug(f"集成模型预测值: {predictions}, 加权平均: {avg_prediction:.4f}")
            
            # 反向转换预测结果
            rul_scaled = np.array([[avg_prediction]])
            rul = self.scalers['capacity'].inverse_transform(rul_scaled)[0][0]
            
            # 转换为循环数 (假设满容量为 1.0)
            max_cycles = 1000  # 假设最大寿命为 1000 循环
            remaining_cycles = max_cycles * rul
            
            logger.debug(f"CNN+LSTM 模型预测 RUL: {remaining_cycles:.2f} 循环")
            return remaining_cycles
            
        except Exception as e:
            logger.error(f"RUL 预测出错: {e}")
            return self._simple_estimate(static_features)
    
    def _simple_estimate(self, static_features):
        """简单的 RUL 估计方法
        
        基于循环数和健康状态的简单估计
        
        参数:
            static_features: [cycle_count, health, avg_temperature]
            
        返回:
            estimated_rul: 估计的剩余寿命（循环数）
        """
        cycle_count = static_features[0]
        health = static_features[1]
        
        # 简单线性估计: 假设总寿命为 1000 循环，根据健康状态调整
        max_cycles = 1000 * health
        estimated_rul = max(0, max_cycles - cycle_count)
        
        logger.debug(f"简单 RUL 估计: {estimated_rul} 循环")
        return estimated_rul
    
    def train(self, voltage_data, capacity_data, epochs=100, batch_size=32):
        """训练模型
        
        参数:
            voltage_data: 电压数据序列，形状 [样本数, 时间步]
            capacity_data: 容量数据序列，形状 [样本数, 时间步]
            epochs: 训练轮数
            batch_size: 批次大小
            
        返回:
            history: 训练历史
        """
        if len(voltage_data) < self.seq_len_cnn + 1 or len(capacity_data) < self.seq_len_lstm + 1:
            raise ValueError("训练数据长度不足")
        
        # 准备训练数据
        X_voltage = []
        X_capacity = []
        y = []
        
        for i in range(len(capacity_data) - self.seq_len_lstm):
            X_capacity.append(capacity_data[i:i+self.seq_len_lstm])
            X_voltage.append(voltage_data[i:i+self.seq_len_cnn])
            y.append(capacity_data[i+self.seq_len_lstm])
        
        X_voltage = np.array(X_voltage)
        X_capacity = np.array(X_capacity)
        y = np.array(y)
        
        # 预处理数据
        X_voltage_scaled = self._preprocess_data(X_voltage.reshape(-1, 1), 'voltage').reshape(X_voltage.shape)
        X_capacity_scaled = self._preprocess_data(X_capacity.reshape(-1, 1), 'capacity').reshape(X_capacity.shape)
        y_scaled = self._preprocess_data(y.reshape(-1, 1), 'capacity')
        
        # 训练模型
        history = self.model.fit(
            [X_capacity_scaled, X_voltage_scaled],
            y_scaled,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=1
        )
        
        self.is_trained = True
        
        # 保存模型
        self._save_model()
        
        return history
    
    def _save_model(self):
        """保存模型"""
        if self.model is not None and self.is_trained:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            logger.info(f"模型已保存到: {self.model_path}")
    
    def adjust_charging_parameters(self, battery_state, rul_percentage):
        """基于 RUL 预测调整充电参数
        
        参数:
            battery_state: 电池状态信息
            rul_percentage: RUL 百分比 (0-100)
            
        返回:
            adjusted_params: 调整后的充电参数
        """
        # 获取电池当前状态
        soc = battery_state.get("soc", 50)
        temperature = battery_state.get("temperature", 25)
        voltage = battery_state.get("voltage", 3.7)
        current = battery_state.get("current", 0)
        internal_resistance = battery_state.get("internal_resistance", 0.1)
        
        # 默认参数 - 基于比亚迪秦L EV电池规格
        default_params = {
            "cc_current": 0.5,  # 恒流充电电流 (C-rate)
            "cv_voltage": 4.2,  # 恒压充电电压 (V)
            "trickle_current": 0.05,  # 涓流充电电流 (C-rate)
            "termination_current": 0.05,  # 终止电流 (C-rate)
            "max_temperature": 45,  # 最高允许温度 (°C)
            "min_temperature": 0,   # 最低允许温度 (°C)
            "max_soc": 100,         # 最大充电SOC (%)
            "charging_strategy": "standard"  # 充电策略: standard, eco, longevity
        }
        
        # 根据 RUL 和温度调整参数
        # 创建一个连续的调整因子，而不是离散的阈值
        rul_factor = min(1.0, max(0.2, rul_percentage / 100))  # 将RUL映射到0.2-1.0范围
        
        # 温度调整因子：温度越高，充电参数越保守
        # 使用更精细的温度调整曲线
        if temperature >= 45:
            temp_factor = 0.5  # 接近极限温度，大幅降低
        elif temperature >= 40:
            temp_factor = 0.6 + (45 - temperature) * 0.02  # 40-45°C 范围内线性变化
        elif temperature >= 35:
            temp_factor = 0.7 + (40 - temperature) * 0.02  # 35-40°C 范围内线性变化
        elif temperature >= 30:
            temp_factor = 0.8 + (35 - temperature) * 0.02  # 30-35°C 范围内线性变化
        elif temperature >= 25:
            temp_factor = 0.9 + (30 - temperature) * 0.02  # 25-30°C 范围内线性变化
        elif temperature >= 10:
            temp_factor = 1.0  # 理想温度范围
        elif temperature >= 5:
            temp_factor = 0.9  # 稍低温度
        elif temperature >= 0:
            temp_factor = 0.8  # 低温
        else:
            temp_factor = 0.6  # 极低温
            
        # SOC调整因子：SOC越高，充电电流越小（尤其是在高SOC区域）
        # 使用分段函数更精确地调整SOC因子
        if soc >= 90:
            soc_factor = 0.6 + (100 - soc) * 0.01  # 90-100% 范围内线性变化
        elif soc >= 80:
            soc_factor = 0.7 + (90 - soc) * 0.01  # 80-90% 范围内线性变化
        elif soc >= 60:
            soc_factor = 0.8 + (80 - soc) * 0.005  # 60-80% 范围内线性变化
        elif soc >= 20:
            soc_factor = 1.0  # 中等SOC，最佳充电效率
        else:
            soc_factor = 0.9  # 低SOC，稍微降低以保护电池
        
        # 内阻调整因子：内阻越高，充电电流越小
        # 假设正常内阻为0.1欧姆
        ir_factor = 1.0
        if internal_resistance > 0.2:
            ir_factor = 0.8  # 内阻较高
        elif internal_resistance > 0.15:
            ir_factor = 0.9  # 内阻稍高
            
        # 电压调整因子：接近充满时更保守
        voltage_factor = 1.0
        if voltage > 4.1:
            voltage_factor = 0.8  # 接近充满电压
        elif voltage > 4.0:
            voltage_factor = 0.9  # 较高电压
            
        # 综合调整因子
        combined_factor = rul_factor * temp_factor * soc_factor * ir_factor * voltage_factor
        
        # 选择充电策略
        charging_strategy = "standard"
        if rul_percentage < 30:
            charging_strategy = "longevity"  # 电池寿命较低时，使用延寿策略
        elif temperature > 35 or rul_percentage < 60:
            charging_strategy = "eco"  # 温度高或RUL中等时，使用经济模式
            
        # 根据充电策略进一步调整参数
        strategy_factors = {
            "standard": {"cc": 1.0, "cv": 1.0, "trickle": 1.0, "term": 1.0, "max_soc": 100},
            "eco": {"cc": 0.9, "cv": 0.98, "trickle": 0.9, "term": 1.1, "max_soc": 90},
            "longevity": {"cc": 0.7, "cv": 0.95, "trickle": 0.8, "term": 1.2, "max_soc": 80}
        }
        
        strategy = strategy_factors[charging_strategy]
        
        # 应用调整因子
        adjusted_params = {
            "cc_current": default_params["cc_current"] * combined_factor * strategy["cc"],
            "cv_voltage": default_params["cv_voltage"] * (0.95 + 0.05 * rul_factor) * strategy["cv"],
            "trickle_current": default_params["trickle_current"] * combined_factor * strategy["trickle"],
            "termination_current": default_params["termination_current"] * (0.9 + 0.1 * rul_factor) * strategy["term"],
            "max_temperature": default_params["max_temperature"],
            "min_temperature": default_params["min_temperature"],
            "max_soc": strategy["max_soc"],
            "charging_strategy": charging_strategy
        }
        
        # 生成充电建议
        charging_advice = []
        if temperature > 40:
            charging_advice.append("电池温度过高，建议降低充电电流或暂停充电")
        elif temperature < 5:
            charging_advice.append("电池温度过低，建议在温暖环境中充电")
            
        if rul_percentage < 30:
            charging_advice.append("电池寿命较低，建议限制充电至80%以延长使用寿命")
        elif rul_percentage < 60:
            charging_advice.append("电池健康状况一般，建议避免频繁快充")
            
        if internal_resistance > 0.15:
            charging_advice.append("电池内阻较高，建议降低充电电流")
            
        # 添加充电建议到参数中
        adjusted_params["charging_advice"] = charging_advice
        
        # 记录详细的调整过程
        logger.info(f"充电参数调整详情:")
        logger.info(f"  - RUL: {rul_percentage:.1f}% (因子: {rul_factor:.2f})")
        logger.info(f"  - 温度: {temperature:.1f}°C (因子: {temp_factor:.2f})")
        logger.info(f"  - SOC: {soc:.1f}% (因子: {soc_factor:.2f})")
        logger.info(f"  - 内阻: {internal_resistance:.3f}Ω (因子: {ir_factor:.2f})")
        logger.info(f"  - 电压: {voltage:.2f}V (因子: {voltage_factor:.2f})")
        logger.info(f"  - 综合因子: {combined_factor:.2f}")
        logger.info(f"  - 充电策略: {charging_strategy}")
        logger.info(f"  - 调整后参数: {adjusted_params}")
        
        return adjusted_params 

    def evaluate_battery_health(self, battery_data, static_features, rul_percentage):
        """评估电池健康状态并提供详细信息
        
        参数:
            battery_data: 电池历史数据
            static_features: 静态特征 [cycle_count, health, avg_temperature]
            rul_percentage: RUL百分比
            
        返回:
            health_info: 健康状态信息字典
        """
        cycle_count = static_features[0]
        health = static_features[1]
        avg_temp = static_features[2]
        
        # 确保health值在0-1之间（表示百分比的小数形式）
        if health > 1:
            health = health / 100.0
        
        # 提取最近的电压和电流数据
        recent_data = battery_data[-20:] if len(battery_data) >= 20 else battery_data
        
        # 计算电压波动性
        if len(recent_data) > 5:
            voltages = [data["voltage"] for data in recent_data]
            voltage_stability = np.std(voltages)
        else:
            voltage_stability = 0
        
        # 计算内阻趋势
        if len(recent_data) > 5 and "internal_resistance" in recent_data[0]:
            resistances = [data["internal_resistance"] for data in recent_data]
            resistance_trend = np.mean(np.diff(resistances)) if len(resistances) > 1 else 0
            avg_resistance = np.mean(resistances)
        else:
            resistance_trend = 0
            avg_resistance = 0.1  # 默认值
        
        # 计算温度稳定性
        if len(recent_data) > 5:
            temperatures = [data["temperature"] for data in recent_data]
            temp_stability = np.std(temperatures)
            max_temp = np.max(temperatures)
            avg_temp = np.mean(temperatures)
        else:
            temp_stability = 0
            max_temp = avg_temp
        
        # 计算充放电效率 (如果数据中有充放电电流)
        charge_efficiency = 0
        if len(recent_data) > 10:
            try:
                # 简化的充放电效率计算
                charge_currents = [abs(data["current"]) for data in recent_data if data["current"] > 0]
                discharge_currents = [abs(data["current"]) for data in recent_data if data["current"] < 0]
                
                if charge_currents and discharge_currents:
                    avg_charge = np.mean(charge_currents)
                    avg_discharge = np.mean(discharge_currents)
                    # 理想情况下比率接近1
                    charge_efficiency = min(1.0, avg_discharge / (avg_charge + 0.001))
            except:
                charge_efficiency = 0
        
        # 确定健康状态类别和等级
        if rul_percentage >= 85:
            health_status = "良好"
            health_grade = "A"
            health_score = 90 + min(10, (rul_percentage - 85) / 1.5)
            recommendations = [
                "可以使用标准充电模式",
                "定期检查电池状态",
                "无需特殊维护"
            ]
            maintenance_schedule = "每3-6个月检查一次电池状态"
        elif rul_percentage >= 70:
            health_status = "正常"
            health_grade = "B+"
            health_score = 80 + (rul_percentage - 70) / 1.5
            recommendations = [
                "建议使用温和充电模式",
                "避免频繁快充",
                "定期完整充放电循环",
                "保持电池在20%-80%的SOC范围内"
            ]
            maintenance_schedule = "每2-3个月检查一次电池状态"
        elif rul_percentage >= 50:
            health_status = "一般"
            health_grade = "B"
            health_score = 60 + (rul_percentage - 50) / 1
            recommendations = [
                "使用优化充电模式",
                "避免极端温度环境",
                "减少深度放电",
                "考虑进行容量校准",
                "避免长时间存放在高SOC状态"
            ]
            maintenance_schedule = "每1-2个月检查一次电池状态"
        elif rul_percentage >= 30:
            health_status = "较差"
            health_grade = "C"
            health_score = 40 + (rul_percentage - 30) / 1
            recommendations = [
                "仅使用低电流充电",
                "避免充满电",
                "避免电池过热",
                "考虑未来更换电池",
                "避免深度放电",
                "使用温度管理系统"
            ]
            maintenance_schedule = "每月检查电池状态"
        else:
            health_status = "需更换"
            health_grade = "D"
            health_score = max(10, 30 * rul_percentage / 30)
            recommendations = [
                "建议更换电池",
                "限制充电至80%",
                "避免深度放电",
                "避免快充",
                "使用最低充电电流",
                "密切监控电池温度"
            ]
            maintenance_schedule = "持续监控电池状态"
        
        # 根据内阻趋势添加额外建议
        if resistance_trend > 0.001:
            recommendations.append("内阻呈上升趋势，可能表明电池老化加速")
        
        # 根据温度稳定性添加额外建议
        if temp_stability > 3:
            recommendations.append("电池温度波动较大，建议检查散热系统")
        
        if max_temp > 40:
            recommendations.append("电池最高温度过高，建议改善散热条件")
        
        # 根据电压稳定性添加额外建议
        if voltage_stability > 0.1:
            recommendations.append("电压波动较大，可能表明电池单体不平衡")
        
        # 估计剩余循环次数和使用寿命
        estimated_remaining_cycles = int(1000 * rul_percentage / 100)
        
        # 估计剩余使用时间 (假设每天1个循环)
        estimated_remaining_days = estimated_remaining_cycles
        estimated_remaining_months = estimated_remaining_days / 30
        
        # 使用模式建议
        if rul_percentage >= 70:
            usage_pattern = "正常使用"
        elif rul_percentage >= 50:
            usage_pattern = "适度使用，避免高负荷"
        elif rul_percentage >= 30:
            usage_pattern = "轻度使用，避免深度充放电"
        else:
            usage_pattern = "最小化使用，准备更换"
        
        # 构建健康状态信息
        health_info = {
            "status": health_status,
            "grade": health_grade,
            "score": round(health_score, 1),
            "rul_percentage": rul_percentage,
            "estimated_remaining_cycles": estimated_remaining_cycles,
            "estimated_remaining_months": round(estimated_remaining_months, 1),
            "cycle_count": cycle_count,
            "health_percentage": round(health * 100, 2),  # 确保是百分比形式
            "voltage_stability": voltage_stability,
            "internal_resistance": avg_resistance,
            "internal_resistance_trend": resistance_trend,
            "temperature_stability": temp_stability,
            "max_temperature": max_temp,
            "avg_temperature": avg_temp,
            "charge_efficiency": charge_efficiency,
            "recommendations": recommendations,
            "maintenance_schedule": maintenance_schedule,
            "usage_pattern": usage_pattern,
            "last_evaluation_time": time.time()
        }
        
        # 记录健康评估结果
        logger.info(f"电池健康评估完成:")
        logger.info(f"  - 健康状态: {health_status} (等级: {health_grade}, 得分: {health_score:.1f})")
        logger.info(f"  - RUL: {rul_percentage:.1f}%, 估计剩余循环: {estimated_remaining_cycles}")
        logger.info(f"  - 健康百分比: {health * 100:.2f}%")
        logger.info(f"  - 内阻: {avg_resistance:.4f}Ω, 趋势: {resistance_trend:.6f}")
        logger.info(f"  - 温度稳定性: {temp_stability:.2f}°C, 最高温度: {max_temp:.1f}°C")
        logger.info(f"  - 电压稳定性: {voltage_stability:.4f}V")
        logger.info(f"  - 建议使用模式: {usage_pattern}")
        
        return health_info 