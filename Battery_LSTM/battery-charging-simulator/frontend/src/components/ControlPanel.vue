<template>
  <div class="control-panel card">
    <h2 class="card-title">控制面板</h2>
    
    <div class="control-buttons">
      <button 
        :class="['btn-primary', {'btn-disabled': isCharging}]" 
        @click="startCharging" 
        :disabled="isCharging"
      >
        开始充电
      </button>
      
      <button 
        :class="['btn-danger', {'btn-disabled': isDischarging}]" 
        @click="startDischarging" 
        :disabled="isDischarging"
      >
        开始放电
      </button>
      
      <button 
        :class="['btn-success', {'btn-disabled': !isActive}]" 
        @click="stop" 
        :disabled="!isActive"
      >
        停止
      </button>
    </div>
    
    <div class="control-section">
      <h3>参数调节</h3>
      
      <div class="slider-control">
        <label for="internal-resistance">内阻 (R0): {{ internalResistance.toFixed(3) }} Ω</label>
        <input
          id="internal-resistance"
          type="range"
          min="0.050"
          max="0.300"
          step="0.001"
          v-model.number="internalResistance"
          @change="updateBatteryParams"
        />
        <div class="slider-range">
          <span>50 mΩ</span>
          <span>300 mΩ</span>
        </div>
      </div>
      
      <div class="slider-control">
        <label for="polarization-resistance">极化电阻 (R1): {{ polarizationResistance.toFixed(3) }} Ω</label>
        <input
          id="polarization-resistance"
          type="range"
          min="0.020"
          max="0.200"
          step="0.001"
          v-model.number="polarizationResistance"
          @change="updateBatteryParams"
        />
        <div class="slider-range">
          <span>20 mΩ</span>
          <span>200 mΩ</span>
        </div>
      </div>
      
      <div class="slider-control">
        <label for="ambient-temperature">环境温度: {{ ambientTemperature.toFixed(1) }} °C</label>
        <input
          id="ambient-temperature"
          type="range"
          min="10"
          max="60"
          step="0.1"
          v-model.number="ambientTemperature"
          @change="updateBatteryParams"
        />
        <div class="slider-range">
          <span>10 °C</span>
          <span>60 °C</span>
        </div>
      </div>
      
      <div class="slider-control">
        <label for="initial-soc">初始SOC: {{ initialSoc.toFixed(0) }}%</label>
        <input
          id="initial-soc"
          type="range"
          min="0"
          max="100"
          step="1"
          v-model.number="initialSoc"
          @change="updateInitialSoc"
        />
        <div class="slider-range">
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
    
    <div class="control-section">
      <h3>状态信息</h3>
      
      <div class="status-info">
        <div class="status-item">
          <span class="status-label">充电状态:</span>
          <span 
            :class="[
              'status-value', 
              isCharging ? 'status-charging' : 
              isDischarging ? 'status-discharging' : 'status-idle'
            ]"
          >
            {{ statusText }}
          </span>
        </div>
        
        <div class="status-item">
          <span class="status-label">充电模式:</span>
          <span class="status-value">{{ chargingModeText }}</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">预测RUL:</span>
          <span 
            :class="[
              'status-value',
              { 
                'rul-high': estimatedRul > 85,
                'rul-medium': estimatedRul > 70 && estimatedRul <= 85,
                'rul-low': estimatedRul <= 70
              }
            ]"
          >
            {{ estimatedRul.toFixed(2) }}%
          </span>
        </div>
        
        <div class="status-item">
          <span class="status-label">SOC:</span>
          <span class="status-value">{{ soc.toFixed(2) }}%</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">充电电流:</span>
          <span class="status-value">{{ (displayCurrent !== null ? displayCurrent : chargingCurrent).toFixed(1) }} A</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">充电电压:</span>
          <span class="status-value">{{ (displayVoltage !== null ? displayVoltage : chargingVoltage).toFixed(1) }} V</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api';

export default {
  name: 'ControlPanel',
  props: {
    isCharging: {
      type: Boolean,
      default: false
    },
    isDischarging: {
      type: Boolean,
      default: false
    },
    chargingMode: {
      type: String,
      default: 'none'
    },
    estimatedRul: {
      type: Number,
      default: 100
    },
    soc: {
      type: Number,
      default: 100
    },
    chargingCurrent: {
      type: Number,
      default: 0
    },
    chargingVoltage: {
      type: Number,
      default: 0
    },
    displayCurrent: {
      type: Number,
      default: null
    },
    displayVoltage: {
      type: Number,
      default: null
    }
  },
  data() {
    return {
      internalResistance: 0.100,
      polarizationResistance: 0.050,
      ambientTemperature: 25,
      initialSoc: 20,
      isRulOptimized: false,
      showAdvancedSettings: false
    };
  },
  computed: {
    // 是否处于活动状态 (充电或放电)
    isActive() {
      return this.isCharging || this.isDischarging;
    },
    
    // 状态文本
    statusText() {
      if (this.isCharging) {
        return '充电中';
      } else if (this.isDischarging) {
        return '放电中';
      }
      return '待机';
    },
    
    // 充电模式文本
    chargingModeText() {
      if (this.isCharging) {
        switch (this.chargingMode) {
          case 'cc': return '恒流充电';
          case 'cv': return '恒压充电';
          case 'trickle': return '涓流充电';
          default: return '充电中';
        }
      } else if (this.isDischarging) {
        return '放电模式';
      }
      return '无';
    }
  },
  methods: {
    // 开始充电
    async startCharging() {
      try {
        await api.startCharging();
      } catch (error) {
        console.error('开始充电失败:', error);
        this.$emit('error', error);
      }
    },
    
    // 开始放电
    async startDischarging() {
      try {
        await api.startDischarging();
      } catch (error) {
        console.error('开始放电失败:', error);
        this.$emit('error', error);
      }
    },
    
    // 停止充放电
    async stop() {
      try {
        await api.stop();
      } catch (error) {
        console.error('停止充放电失败:', error);
        this.$emit('error', error);
      }
    },
    
    updateBatteryParams() {
      api.updateBatteryParams({
        internal_resistance: this.internalResistance,
        polarization_resistance: this.polarizationResistance,
        ambient_temperature: this.ambientTemperature
      }).catch(error => {
        this.$emit('error', error);
      });
    },
    
    updateInitialSoc() {
      api.updateBatteryParams({
        initial_soc: this.initialSoc
      }).catch(error => {
        this.$emit('error', error);
      });
    }
  }
}
</script>

<style scoped>
.control-panel {
  width: 100%;
}

.control-buttons {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.control-buttons button {
  flex: 1;
  padding: 0.75rem;
  font-size: 1rem;
}

.control-section {
  margin-bottom: 1.5rem;
}

.control-section h3 {
  margin-bottom: 1rem;
  color: var(--dark-color);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.parameter-control {
  margin-bottom: 1.5rem;
}

.parameter-control label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--dark-color);
}

.range-values {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #666;
}

.status-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.status-item {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.status-label {
  font-weight: bold;
  color: var(--dark-color);
  margin-right: 0.5rem;
}

.status-charging {
  color: var(--primary-color);
  font-weight: bold;
}

.status-discharging {
  color: var(--danger-color);
  font-weight: bold;
}

.status-idle {
  color: #7f8c8d;
}

.rul-high {
  color: var(--success-color);
  font-weight: bold;
}

.rul-medium {
  color: var(--warning-color);
  font-weight: bold;
}

.rul-low {
  color: var(--danger-color);
  font-weight: bold;
}

@media (max-width: 768px) {
  .control-buttons {
    flex-direction: column;
  }
  
  .status-info {
    grid-template-columns: 1fr;
  }
}
</style> 