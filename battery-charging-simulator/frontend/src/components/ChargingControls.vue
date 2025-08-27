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

      <!-- 新增：数据集上传与训练控制 -->
      <div class="train-section">
        <h4 class="section-title">RUL模型训练</h4>
        <div class="upload-row">
          <input type="text" v-model="datasetId" placeholder="数据集ID（例如 my_nasa_001）" class="dataset-input" />
          <input type="file" @change="onFileChange" accept=".zip,.csv" />
          <button class="btn" :disabled="uploading || training" @click="uploadDataset">{{ uploading ? '上传中...' : '上传数据集' }}</button>
        </div>
        <div class="train-row">
          <button class="btn primary" :disabled="!canTrain || training" @click="startTraining">{{ training ? '训练中...' : '启动训练' }}</button>
          <span class="hint">建议上传包含 NASA/charge 与 NASA/discharge 子目录的zip</span>
        </div>
        <div class="progress" v-if="progressLogs.length">
          <div class="progress-title">训练进度</div>
          <div class="progress-list">
            <div class="log" v-for="(log, idx) in progressLogs" :key="idx">{{ log }}</div>
          </div>
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
      isLoading: false,
      datasetId: '',
      fileObj: null,
      uploadedOk: false,
      uploading: false,
      training: false,
      jobId: null,
      progressLogs: []
    };
  },
  computed: {
    canTrain() {
      // 允许：已选择文件 或 之前已成功上传（uploadedOk）
      return Boolean((this.fileObj || this.uploadedOk) && this.datasetId && !this.uploading);
    }
  },
  watch: {
    rulOptimizedCharging(newVal) {
      this.localRulOptimizedCharging = newVal;
    }
  },
  created() {
    // 监听电池状态更新
    api.addEventListener('batteryState', this.handleBatteryState);
    // 训练事件
    api.addEventListener('trainProgress', this.onTrainProgress);
    api.addEventListener('trainCompleted', this.onTrainCompleted);
    
    // 主动获取当前RUL优化充电状态
    this.fetchRulOptimizationStatus();
  },
  beforeDestroy() {
    // 移除事件监听器
    api.removeEventListener('batteryState', this.handleBatteryState);
    api.removeEventListener('trainProgress', this.onTrainProgress);
    api.removeEventListener('trainCompleted', this.onTrainCompleted);
    
    // 停止轮询
    api.stopTrainStatusPolling();
  },
  methods: {
    // 获取当前RUL优化充电状态
    async fetchRulOptimizationStatus() {
      try {
        this.isLoading = true;
        // 使用API服务获取状态
        const data = await api.getServerStatus();
        
        // 更新本地状态
        if (data && data.battery_state) {
          const rulEnabled = data.battery_state.rul_optimized_charging;
          const chargingOpt = data.battery_state.charging_optimization;
          
          if (rulEnabled !== undefined) {
            this.localRulOptimizedCharging = rulEnabled;
            console.log(`RUL优化充电当前状态: ${this.localRulOptimizedCharging ? '已启用' : '已禁用'}`);
          }
          
          // 如果有充电优化信息，也记录下来
          if (chargingOpt) {
            console.log('充电优化详情:', {
              enabled: chargingOpt.enabled,
              hasParams: !!chargingOpt.adjusted_params,
              strategy: chargingOpt.adjusted_params?.charging_strategy,
              advice: chargingOpt.charging_advice?.length || 0
            });
          }
        }
      } catch (error) {
        console.error('获取RUL优化充电状态失败:', error);
        // 显示错误提示
        this.$emit('show-notification', {
          type: 'error',
          message: `获取状态失败: ${error.message}`
        });
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
    ,
    onFileChange(e) {
      const files = e.target.files;
      this.fileObj = files && files.length ? files[0] : null;
      this.uploadedOk = false;
    },
    async uploadDataset() {
      if (!this.datasetId) {
        this.$emit('show-notification', { type: 'error', message: '请填写数据集ID' });
        return;
      }
      if (!this.fileObj) {
        this.$emit('show-notification', { type: 'error', message: '请选择要上传的zip或csv' });
        return;
      }
      try {
        this.uploading = true;
        await api.uploadDataset(this.datasetId, this.fileObj);
        this.uploadedOk = true;
        this.$emit('show-notification', { type: 'success', message: '数据集上传成功' });
      } catch (e) {
        this.$emit('show-notification', { type: 'error', message: `上传失败: ${e.message}` });
      } finally {
        this.uploading = false;
      }
    },
    async startTraining() {
      if (!this.datasetId) {
        this.$emit('show-notification', { type: 'error', message: '请先填写数据集ID并上传数据' });
        return;
      }
      try {
        this.training = true;
        this.progressLogs = [];
        const res = await api.triggerTrain({ datasetId: this.datasetId });
        this.jobId = res.jobId;
        
        // 总是启动轮询监控，作为可靠的备选方案
        this.$emit('show-notification', { type: 'info', message: `训练已启动，作业ID: ${this.jobId} (REST API监控)` });
        this.startPollingMode();
        
        // 如果WebSocket可用，也同时启用（双重保障）
        if (api.isConnected) {
          console.log('WebSocket也可用，将同时监控');
        }
      } catch (e) {
        this.$emit('show-notification', { type: 'error', message: `触发训练失败: ${e.message}` });
        this.training = false;
      }
    },
    
    // 启动轮询模式监控训练进度
    startPollingMode() {
      if (!this.jobId) return;
      
      api.startTrainStatusPolling(
        this.jobId,
        this.onTrainProgress, // 进度回调
        this.onTrainCompleted, // 完成回调
        2000 // 2秒轮询间隔
      );
    },
    onTrainProgress(payload) {
      if (payload && payload.message) {
        // 追加有限长度日志
        this.progressLogs.push(payload.message);
        if (this.progressLogs.length > 200) this.progressLogs.shift();
      }
    },
    onTrainCompleted(payload) {
      this.training = false;
      
      // 停止轮询（如果在使用轮询模式）
      api.stopTrainStatusPolling();
      
      if (payload && payload.success) {
        const duration = payload.durationSec ? ` (耗时: ${Math.round(payload.durationSec)}秒)` : '';
        this.$emit('show-notification', { 
          type: 'success', 
          message: `训练完成，激活模型数: ${payload.modelCount || 0}${duration}` 
        });
      } else {
        this.$emit('show-notification', { 
          type: 'error', 
          message: `训练失败: ${payload && payload.error ? payload.error : '未知错误'}` 
        });
      }
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
}

.toggle-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #333;
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
  border: 1px solid #eee;
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
  background-color: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 10px;
}

.feature-icon {
  font-size: 1.4rem;
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

/* 一致化：训练区域采用卡片式与小号字体，贴合全局风格 */
.train-section {
  margin-top: 8px;
}
.section-title {
  margin: 0 0 8px 0;
  font-size: 1rem;
  color: #333;
}
.upload-row, .train-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.dataset-input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.btn {
  padding: 8px 12px;
  border: 1px solid #3498db;
  background: #3498db;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.btn.primary {
  background: #2ecc71;
  border-color: #2ecc71;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.hint {
  font-size: 0.85rem;
  color: #6c757d;
}
.progress-title {
  font-weight: bold;
  margin-bottom: 4px;
}
.progress-list {
  max-height: 140px;
  overflow: auto;
  background: #f8f9fa;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 8px;
}
.log {
  font-size: 0.85rem;
  color: #555;
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