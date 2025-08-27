<template>
  <div class="model-manager">
    <div class="card">
      <h3 class="card-title">
        <span class="icon">🧠</span>
        RUL模型管理
      </h3>
      
      <!-- 模型状态显示 -->
      <div class="model-status">
        <div class="status-item">
          <label>当前模型状态:</label>
          <span :class="['status-badge', modelStatus.available ? 'status-active' : 'status-inactive']">
            {{ modelStatus.available ? '已激活' : '未激活' }}
          </span>
        </div>
        
        <div class="status-item" v-if="modelStatus.available">
          <label>模型数量:</label>
          <span class="model-count">{{ modelStatus.modelCount || 0 }} 个</span>
        </div>
        
        <div class="status-item" v-if="modelStatus.lastTrainingTime">
          <label>最后训练:</label>
          <span class="training-time">{{ formatTrainingTime(modelStatus.lastTrainingTime) }}</span>
        </div>
      </div>

      <!-- RUL预测显示 -->
      <div class="rul-prediction" v-if="rulData.available">
        <h4>当前RUL预测</h4>
        <div class="rul-display">
          <div class="rul-percentage">
            <div class="rul-circle">
              <svg viewBox="0 0 36 36" class="circular-chart">
                <path class="circle-bg"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path class="circle"
                  :stroke-dasharray="`${rulData.percentage}, 100`"
                  :class="getRulColorClass(rulData.percentage)"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <text x="18" y="20.35" class="percentage-text">{{ rulData.percentage.toFixed(1) }}%</text>
              </svg>
            </div>
            <p class="rul-label">剩余寿命</p>
          </div>
          
          <div class="rul-details">
            <div class="detail-item">
              <span class="label">健康状态:</span>
              <span :class="['value', getHealthColorClass(rulData.healthGrade)]">
                {{ rulData.healthStatus }} ({{ rulData.healthGrade }})
              </span>
            </div>
            <div class="detail-item">
              <span class="label">估计剩余循环:</span>
              <span class="value">{{ rulData.estimatedCycles || 'N/A' }} 次</span>
            </div>
            <div class="detail-item">
              <span class="label">预计剩余月数:</span>
              <span class="value">{{ rulData.estimatedMonths || 'N/A' }} 个月</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 充电参数调控显示 -->
      <div class="charging-optimization" v-if="chargingOptimization.enabled">
        <h4>智能充电调控</h4>
        <div class="optimization-grid">
          <div class="param-item">
            <label>恒流充电电流:</label>
            <span class="param-value">{{ formatCurrent(chargingOptimization.params.cc_current) }}</span>
          </div>
          <div class="param-item">
            <label>恒压充电电压:</label>
            <span class="param-value">{{ chargingOptimization.params.cv_voltage.toFixed(2) }}V</span>
          </div>
          <div class="param-item">
            <label>最大SOC限制:</label>
            <span class="param-value">{{ chargingOptimization.params.max_soc }}%</span>
          </div>
          <div class="param-item">
            <label>充电策略:</label>
            <span :class="['strategy-badge', `strategy-${chargingOptimization.params.charging_strategy}`]">
              {{ getStrategyName(chargingOptimization.params.charging_strategy) }}
            </span>
          </div>
        </div>
        
        <!-- 充电建议 -->
        <div class="charging-advice" v-if="chargingOptimization.advice.length > 0">
          <h5>🔍 充电建议</h5>
          <ul class="advice-list">
            <li v-for="(advice, index) in chargingOptimization.advice" :key="index">
              {{ advice }}
            </li>
          </ul>
        </div>
      </div>

      <!-- 手动刷新按钮 -->
      <div class="actions">
        <button @click="refreshModelStatus" :disabled="refreshing" class="btn btn-primary">
          <span v-if="refreshing">🔄 刷新中...</span>
          <span v-else>🔄 刷新状态</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api.js';

export default {
  name: 'ModelManager',
  data() {
    return {
      refreshing: false,
      modelStatus: {
        available: false,
        modelCount: 0,
        lastTrainingTime: null
      },
      rulData: {
        available: false,
        percentage: 0,
        healthStatus: 'unknown',
        healthGrade: 'N/A',
        estimatedCycles: 0,
        estimatedMonths: 0
      },
      chargingOptimization: {
        enabled: false,
        params: {},
        advice: []
      }
    };
  },
  mounted() {
    this.refreshModelStatus();
    
    // 监听电池状态更新
    api.addEventListener('batteryState', this.handleBatteryState);
  },
  beforeDestroy() {
    api.removeEventListener('batteryState', this.handleBatteryState);
  },
  methods: {
    async refreshModelStatus() {
      this.refreshing = true;
      try {
        const response = await fetch('http://localhost:8001/api/status');
        const data = await response.json();
        
        // 更新模型状态
        this.modelStatus.available = data.rul_model_available || false;
        
        // 更新电池状态相关信息
        if (data.battery_state) {
          this.handleBatteryState(data.battery_state);
        }
        
      } catch (error) {
        console.error('刷新模型状态失败:', error);
        this.$emit('show-notification', {
          type: 'error',
          message: '刷新模型状态失败'
        });
      } finally {
        this.refreshing = false;
      }
    },
    
    handleBatteryState(batteryState) {
      // 更新RUL数据
      if (batteryState.estimated_rul !== undefined) {
        this.rulData.available = true;
        this.rulData.percentage = batteryState.estimated_rul || 0;
      }
      
      // 更新健康状态
      if (batteryState.health_info) {
        this.rulData.healthStatus = batteryState.health_info.status || 'unknown';
        this.rulData.healthGrade = batteryState.health_info.grade || 'N/A';
        this.rulData.estimatedCycles = batteryState.health_info.estimated_remaining_cycles || 0;
        this.rulData.estimatedMonths = batteryState.health_info.estimated_remaining_months || 0;
      }
      
      // 更新充电优化信息
      if (batteryState.charging_optimization) {
        this.chargingOptimization.enabled = batteryState.charging_optimization.enabled || false;
        this.chargingOptimization.params = batteryState.charging_optimization.adjusted_params || {};
        this.chargingOptimization.advice = batteryState.charging_optimization.charging_advice || [];
      }
    },
    
    formatTrainingTime(timestamp) {
      if (!timestamp) return 'N/A';
      return new Date(timestamp * 1000).toLocaleString();
    },
    
    formatCurrent(cRate) {
      if (typeof cRate !== 'number') return 'N/A';
      return `${cRate.toFixed(2)}C`;
    },
    
    getStrategyName(strategy) {
      const names = {
        'standard': '标准模式',
        'eco': '经济模式', 
        'longevity': '延寿模式'
      };
      return names[strategy] || strategy;
    },
    
    getRulColorClass(percentage) {
      if (percentage >= 70) return 'rul-good';
      if (percentage >= 50) return 'rul-fair';
      if (percentage >= 30) return 'rul-poor';
      return 'rul-critical';
    },
    
    getHealthColorClass(grade) {
      if (grade === 'A') return 'health-good';
      if (grade === 'B+' || grade === 'B') return 'health-fair';
      if (grade === 'C') return 'health-poor';
      return 'health-critical';
    }
  }
};
</script>

<style scoped>
.model-manager {
  margin-bottom: 1.5rem;
}

.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  color: #333;
  font-weight: bold;
}

.icon {
  font-size: 1.4rem;
}

.model-status {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.status-item label {
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-align: center;
}

.status-active {
  background: #d1f2eb;
  color: #0d5345;
}

.status-inactive {
  background: #fadbd8;
  color: #922b21;
}

.model-count, .training-time {
  font-weight: 600;
  color: #333;
}

.rul-prediction, .charging-optimization {
  margin-bottom: 1.5rem;
}

.rul-prediction h4, .charging-optimization h4 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
}

.rul-display {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2rem;
  align-items: center;
}

.rul-percentage {
  text-align: center;
}

.rul-circle {
  width: 100px;
  height: 100px;
  margin: 0 auto 0.5rem;
}

.circular-chart {
  width: 100%;
  height: 100%;
}

.circle-bg {
  fill: none;
  stroke: #eee;
  stroke-width: 3.8;
}

.circle {
  fill: none;
  stroke-width: 2.8;
  stroke-linecap: round;
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
  transition: stroke-dasharray 0.5s ease-in-out;
}

.rul-good { stroke: #4CAF50; }
.rul-fair { stroke: #FF9800; }
.rul-poor { stroke: #FF5722; }
.rul-critical { stroke: #F44336; }

.percentage-text {
  font-size: 0.5em;
  text-anchor: middle;
  fill: #333;
  font-weight: bold;
}

.rul-label {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
}

.rul-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.detail-item .label {
  font-size: 0.9rem;
  color: #666;
}

.detail-item .value {
  font-weight: 600;
  color: #333;
}

.health-good { color: #4CAF50; }
.health-fair { color: #FF9800; }
.health-poor { color: #FF5722; }
.health-critical { color: #F44336; }

.optimization-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.param-item label {
  font-size: 0.9rem;
  color: #666;
}

.param-value {
  font-weight: 600;
  color: #333;
}

.strategy-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-align: center;
}

.strategy-standard {
  background: #e3f2fd;
  color: #1565c0;
}

.strategy-eco {
  background: #e8f5e8;
  color: #2e7d32;
}

.strategy-longevity {
  background: #fff3e0;
  color: #ef6c00;
}

.charging-advice {
  padding: 1rem;
  background: #e8f4fd;
  border-radius: 6px;
  border-left: 4px solid #2196f3;
}

.charging-advice h5 {
  margin: 0 0 0.75rem 0;
  color: #1976d2;
  font-size: 1rem;
}

.advice-list {
  margin: 0;
  padding-left: 1.25rem;
}

.advice-list li {
  margin-bottom: 0.5rem;
  color: #333;
  font-size: 0.9rem;
}

.actions {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1976d2;
}

@media (max-width: 768px) {
  .rul-display {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .optimization-grid {
    grid-template-columns: 1fr;
  }
}
</style>