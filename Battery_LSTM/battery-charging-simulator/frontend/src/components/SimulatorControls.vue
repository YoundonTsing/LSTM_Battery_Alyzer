<template>
  <div class="simulator-controls">
    <h3 class="controls-title">模拟器控制</h3>
    <div class="control-group">
      <label class="control-label">时间加速因子</label>
      <div class="acceleration-controls">
        <button @click="setAccelerationFactor(1)" :class="{'active': accelerationFactor === 1}" class="acceleration-btn">1x</button>
        <button @click="setAccelerationFactor(5)" :class="{'active': accelerationFactor === 5}" class="acceleration-btn">5x</button>
        <button @click="setAccelerationFactor(10)" :class="{'active': accelerationFactor === 10}" class="acceleration-btn">10x</button>
        <button @click="setAccelerationFactor(20)" :class="{'active': accelerationFactor === 20}" class="acceleration-btn">20x</button>
        <button @click="setCustomAcceleration" class="acceleration-btn custom-btn">自定义</button>
      </div>
      <div v-if="showCustomInput" class="custom-acceleration">
        <input type="number" v-model.number="customAccelerationFactor" min="0.1" step="0.1" />
        <button @click="applyCustomAcceleration" class="apply-btn">应用</button>
        <button @click="cancelCustomAcceleration" class="cancel-btn">取消</button>
      </div>
    </div>
    <div class="status-info">
      <div class="status-item">
        <span class="status-label">当前加速因子:</span>
        <span class="status-value">{{ accelerationFactor }}x</span>
      </div>
      <div class="status-item">
        <span class="status-label">模拟速度:</span>
        <span class="status-value">{{ accelerationFactor }}倍实时速度</span>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'SimulatorControls',
  data() {
    return {
      accelerationFactor: 1,
      showCustomInput: false,
      customAccelerationFactor: 1,
    };
  },
  created() {
    // 获取初始状态
    this.getInitialState();
  },
  methods: {
    async getInitialState() {
      try {
        const response = await fetch('/api/status');
        const data = await response.json();
        this.accelerationFactor = data.time_acceleration_factor || 1;
      } catch (error) {
        console.error('获取模拟器状态失败:', error);
      }
    },
    async setAccelerationFactor(factor) {
      try {
        await api.setTimeAccelerationFactor(factor);
        this.accelerationFactor = factor;
        this.$emit('show-notification', {
          type: 'success',
          message: `模拟速度已设置为 ${factor}x`
        });
      } catch (error) {
        this.$emit('show-notification', {
          type: 'error',
          message: `设置模拟速度失败: ${error.message}`
        });
      }
    },
    setCustomAcceleration() {
      this.customAccelerationFactor = this.accelerationFactor;
      this.showCustomInput = true;
    },
    async applyCustomAcceleration() {
      if (this.customAccelerationFactor <= 0) {
        this.$emit('show-notification', {
          type: 'error',
          message: '加速因子必须大于0'
        });
        return;
      }
      
      await this.setAccelerationFactor(this.customAccelerationFactor);
      this.showCustomInput = false;
    },
    cancelCustomAcceleration() {
      this.showCustomInput = false;
    }
  }
};
</script>

<style scoped>
.simulator-controls {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.controls-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #333;
}

.control-group {
  margin-bottom: 1rem;
}

.control-label {
  display: block;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.acceleration-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.acceleration-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #3498db;
  background-color: white;
  color: #3498db;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.acceleration-btn:hover {
  background-color: #f0f8ff;
}

.acceleration-btn.active {
  background-color: #3498db;
  color: white;
}

.custom-btn {
  border-color: #95a5a6;
  color: #95a5a6;
}

.custom-acceleration {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.custom-acceleration input {
  width: 80px;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.apply-btn {
  padding: 0.5rem 1rem;
  background-color: #2ecc71;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.cancel-btn {
  padding: 0.5rem 1rem;
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.status-info {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.status-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.status-label {
  font-weight: bold;
}

.status-value {
  color: #3498db;
}

@media (max-width: 768px) {
  .acceleration-controls {
    flex-direction: column;
  }
}
</style> 