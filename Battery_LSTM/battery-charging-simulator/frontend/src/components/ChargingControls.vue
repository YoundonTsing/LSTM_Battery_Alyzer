<template>
  <div class="rul-optimization-toggle">
    <h3 class="toggle-title">RUL优化充电设置</h3>
    <div class="toggle-container">
      <div class="control-group">
        <div class="toggle-control">
          <label class="toggle-label">RUL 优化充电</label>
          <label class="switch" :class="{ 'disabled': isLoading }">
            <input type="checkbox" v-model="localRulOptimizedCharging" @change="toggleRulOptimization" :disabled="isLoading">
            <span class="slider round"></span>
          </label>
          <span class="toggle-status" :class="{ 'loading': isLoading, 'status-enabled': localRulOptimizedCharging && !isLoading, 'status-disabled': !localRulOptimizedCharging && !isLoading }">
            {{ isLoading ? '处理中...' : (localRulOptimizedCharging ? '已启用' : '已禁用') }}
          </span>
        </div>
        
        <div class="feature-description">
          <div class="feature-icon">🔋</div>
          <div class="feature-text">
            <p><strong>CNN+LSTM深度学习模型</strong>基于电池健康状态智能调整充电参数，延长电池寿命。</p>
            <p>启用后，系统将根据RUL预测结果自动优化充电电流、电压和充电策略。</p>
          </div>
        </div>
        
        <div class="hint-text" v-if="localRulOptimizedCharging">
          <div class="hint-icon">💡</div>
          基于电池健康状态自动调整充电参数，延长电池寿命
        </div>
        
        <div class="status-indicator" v-if="localRulOptimizedCharging">
          <div class="status-dot" :class="{ 'active': isCharging && localRulOptimizedCharging }"></div>
          <span>{{ isCharging && localRulOptimizedCharging ? '正在使用优化充电参数' : '等待下次充电时应用' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'RulOptimizationToggle',
  props: {
    rulOptimizedCharging: {
      type: Boolean,
      default: false
    },
    isCharging: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      localRulOptimizedCharging: this.rulOptimizedCharging,
      isLoading: false
    };
  },
  watch: {
    rulOptimizedCharging(newVal) {
      this.localRulOptimizedCharging = newVal;
    }
  },
  created() {
    // 监听电池状态更新
    api.addEventListener('batteryState', this.handleBatteryState);
    
    // 主动获取当前RUL优化充电状态
    this.fetchRulOptimizationStatus();
  },
  beforeDestroy() {
    // 移除事件监听器
    api.removeEventListener('batteryState', this.handleBatteryState);
  },
  methods: {
    // 获取当前RUL优化充电状态
    async fetchRulOptimizationStatus() {
      try {
        this.isLoading = true;
        // 发送请求获取当前状态
        const response = await fetch('http://localhost:8000/api/status');
        const data = await response.json();
        
        // 更新本地状态
        if (data && data.battery_state && data.battery_state.rul_optimized_charging !== undefined) {
          this.localRulOptimizedCharging = data.battery_state.rul_optimized_charging;
          console.log(`RUL优化充电当前状态: ${this.localRulOptimizedCharging ? '已启用' : '已禁用'}`);
        }
      } catch (error) {
        console.error('获取RUL优化充电状态失败:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    handleBatteryState(data) {
      // 只更新RUL优化充电状态
      if (data.rul_optimized_charging !== undefined && data.rul_optimized_charging !== this.localRulOptimizedCharging) {
        this.localRulOptimizedCharging = data.rul_optimized_charging;
      }
    },
    
    toggleRulOptimization() {
      this.isLoading = true;
      
      api.setRulOptimization(this.localRulOptimizedCharging)
        .then((response) => {
          // 确保本地状态与服务器状态同步
          this.localRulOptimizedCharging = response.rul_optimized_charging;
          
          // 显示提示信息
          this.$emit('show-notification', {
            type: this.localRulOptimizedCharging ? 'success' : 'info',
            message: response.message || (this.localRulOptimizedCharging ? 'RUL 优化充电已启用' : 'RUL 优化充电已禁用')
          });
        })
        .catch(error => {
          // 如果失败，恢复之前的状态
          this.localRulOptimizedCharging = !this.localRulOptimizedCharging;
          
          this.$emit('show-notification', {
            type: 'error',
            message: `设置失败: ${error.message}`
          });
        })
        .finally(() => {
          this.isLoading = false;
        });
    }
  }
};
</script>

<style scoped>
.rul-optimization-toggle {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 2px solid #3498db;
  position: relative;
  overflow: hidden;
}

.rul-optimization-toggle::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 5px;
  background: linear-gradient(90deg, #3498db, #2ecc71);
}

.toggle-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #2980b9;
  font-weight: bold;
}

.toggle-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* 开关样式 */
.toggle-control {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  background-color: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.toggle-label {
  margin-right: 10px;
  font-weight: bold;
  font-size: 1.1rem;
  color: #333;
}

.toggle-status {
  margin-left: 10px;
  font-size: 0.9em;
  padding: 4px 8px;
  border-radius: 4px;
}

.status-enabled {
  background-color: #d4edda;
  color: #155724;
  font-weight: bold;
}

.status-disabled {
  background-color: #f8d7da;
  color: #721c24;
}

.feature-description {
  display: flex;
  gap: 10px;
  background-color: #e8f4fd;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 10px;
}

.feature-icon {
  font-size: 2rem;
  color: #3498db;
}

.feature-text {
  flex: 1;
}

.feature-text p {
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  color: #333;
}

.feature-text p:last-child {
  margin-bottom: 0;
}

.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 30px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 22px;
  width: 22px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
}

input:checked + .slider {
  background-color: #2ecc71;
}

input:focus + .slider {
  box-shadow: 0 0 1px #2ecc71;
}

input:checked + .slider:before {
  transform: translateX(30px);
}

.slider.round {
  border-radius: 30px;
}

.slider.round:before {
  border-radius: 50%;
}

.hint-text {
  font-size: 0.9em;
  color: #2980b9;
  margin-top: 5px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.hint-icon {
  font-size: 1.2rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9em;
  color: #666;
  margin-top: 5px;
  margin-bottom: 10px;
  background-color: #f8f9fa;
  padding: 8px 12px;
  border-radius: 6px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #ccc;
}

.status-dot.active {
  background-color: #2ecc71;
  box-shadow: 0 0 5px #2ecc71;
  animation: pulse 1.5s infinite;
}

.switch.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-status.loading {
  color: #3498db;
  animation: blink 1s infinite;
}

@keyframes blink {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }
  70% { box-shadow: 0 0 0 5px rgba(46, 204, 113, 0); }
  100% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }
}

@media (max-width: 768px) {
  .rul-optimization-toggle {
    padding: 1rem;
  }
}
</style> 