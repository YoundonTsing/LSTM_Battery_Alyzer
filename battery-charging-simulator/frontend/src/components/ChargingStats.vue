<template>
  <div class="charging-stats card">
    <h2 class="card-title">充电统计</h2>
    
    <div v-if="!hasChargingRecords" class="no-records">
      <p>暂无充电记录，请先开始充电过程。</p>
    </div>
    
    <div v-else>
      <div class="stats-summary">
        <div class="summary-item">
          <h3>本次充电时长</h3>
          <div class="summary-value">{{ formatDuration(totalChargingTime) }}</div>
        </div>
        
        <div class="summary-item">
          <h3>充电阶段分布</h3>
          <div class="phase-bars">
            <div 
              class="phase-bar cc-phase" 
              :style="{ width: `${ccPercentage}%` }"
              v-if="ccPercentage > 0"
            >
              <span class="phase-label">恒流 ({{ ccPercentage.toFixed(1) }}%)</span>
            </div>
            <div 
              class="phase-bar cv-phase" 
              :style="{ width: `${cvPercentage}%` }"
              v-if="cvPercentage > 0"
            >
              <span class="phase-label">恒压 ({{ cvPercentage.toFixed(1) }}%)</span>
            </div>
            <div 
              class="phase-bar trickle-phase" 
              :style="{ width: `${tricklePercentage}%` }"
              v-if="tricklePercentage > 0"
            >
              <span class="phase-label">涓流 ({{ tricklePercentage.toFixed(1) }}%)</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="charging-parameters">
        <h3>充电参数</h3>
        <div class="parameters-grid">
          <div class="parameter-item">
            <span class="parameter-label">恒流时间:</span>
            <span class="parameter-value">{{ formatDuration(ccDuration) }}</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">恒流电流:</span>
            <span class="parameter-value">{{ (currentRecord.cc_current || 0).toFixed(1) }} A</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">恒压时间:</span>
            <span class="parameter-value">{{ formatDuration(cvDuration) }}</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">恒压电压:</span>
            <span class="parameter-value">{{ (currentRecord.cv_voltage || 0).toFixed(1) }} V</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">涓流时间:</span>
            <span class="parameter-value">{{ formatDuration(trickleDuration) }}</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">涓流电流:</span>
            <span class="parameter-value">{{ (currentRecord.trickle_current || 0).toFixed(1) }} A</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">起始SOC:</span>
            <span class="parameter-value">{{ (currentRecord.initial_soc || 0).toFixed(1) }}%</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">终止SOC:</span>
            <span class="parameter-value">{{ (currentRecord.final_soc || 0).toFixed(1) }}%</span>
          </div>
          <div class="parameter-item">
            <span class="parameter-label">温度变化:</span>
            <span class="parameter-value">{{ (currentRecord.initial_temperature || 0).toFixed(1) }} → {{ (currentRecord.final_temperature || 0).toFixed(1) }} °C</span>
          </div>
        </div>
      </div>
      
      <div class="charging-history">
        <h3>充电历史记录</h3>
        
        <div class="history-table-container">
          <table class="history-table">
            <thead>
              <tr>
                <th>开始时间</th>
                <th>初始SOC</th>
                <th>最终SOC</th>
                <th>初始温度</th>
                <th>最终温度</th>
                <th>内阻 (R0)</th>
                <th>极化电阻 (R1)</th>
                <th>充电时长</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(record, index) in records" :key="`table-${index}`">
                <td>{{ formatTime(record.start_time) }}</td>
                <td>{{ formatPercentage(record.initial_soc) }}</td>
                <td>{{ formatPercentage(record.final_soc) }}</td>
                <td>{{ formatTemperature(record.initial_temperature) }}</td>
                <td>{{ formatTemperature(record.final_temperature) }}</td>
                <td>{{ formatResistance(record.internal_resistance || 0.100) }}</td>
                <td>{{ formatResistance(record.polarization_resistance || 0.050) }}</td>
                <td>{{ calculateRecordDuration(record) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="history-list">
          <div 
            v-for="(record, index) in records" 
            :key="index"
            class="history-item"
            :class="{ 'active': index === currentRecordIndex }"
            @click="selectRecord(index)"
          >
            <div class="history-header">
              <div class="history-title">充电记录 #{{ index + 1 }}</div>
              <div class="history-time">{{ formatDateTime(record.start_time) }}</div>
            </div>
            <div class="history-summary">
              <div class="history-stat">
                <span class="stat-label">SOC:</span>
                <span class="stat-value">{{ (record.initial_soc || 0).toFixed(1) }}% → {{ (record.final_soc || 0).toFixed(1) }}%</span>
              </div>
              <div class="history-stat">
                <span class="stat-label">时长:</span>
                <span class="stat-value">{{ calculateRecordDuration(record) }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="records.length > 5" class="history-note">
            显示最近5条记录，共{{ records.length }}条
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChargingStats',
  props: {
    records: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      currentRecordIndex: 0
    };
  },
  computed: {
    // 是否有充电记录
    hasChargingRecords() {
      return this.records && this.records.length > 0;
    },
    
    // 当前选中的充电记录
    currentRecord() {
      if (!this.hasChargingRecords) {
        return {};
      }
      return this.records[this.currentRecordIndex] || {};
    },
    
    // 恒流充电时长 (秒)
    ccDuration() {
      if (!this.currentRecord.charging_phases) {
        return 0;
      }
      
      const ccPhases = this.currentRecord.charging_phases.filter(phase => phase.phase === 'cc');
      if (ccPhases.length === 0) {
        return 0;
      }
      
      // 计算所有恒流阶段的总时长
      let duration = 0;
      ccPhases.forEach(phase => {
        if (phase.start_time && phase.end_time) {
          const startTime = new Date(phase.start_time);
          const endTime = new Date(phase.end_time);
          duration += (endTime - startTime) / 1000; // 转换为秒
        }
      });
      
      return duration;
    },
    
    // 恒压充电时长 (秒)
    cvDuration() {
      if (!this.currentRecord.charging_phases) {
        return 0;
      }
      
      const cvPhases = this.currentRecord.charging_phases.filter(phase => phase.phase === 'cv');
      if (cvPhases.length === 0) {
        return 0;
      }
      
      // 计算所有恒压阶段的总时长
      let duration = 0;
      cvPhases.forEach(phase => {
        if (phase.start_time && phase.end_time) {
          const startTime = new Date(phase.start_time);
          const endTime = new Date(phase.end_time);
          duration += (endTime - startTime) / 1000; // 转换为秒
        }
      });
      
      return duration;
    },
    
    // 涓流充电时长 (秒)
    trickleDuration() {
      if (!this.currentRecord.charging_phases) {
        return 0;
      }
      
      const tricklePhases = this.currentRecord.charging_phases.filter(phase => phase.phase === 'trickle');
      if (tricklePhases.length === 0) {
        return 0;
      }
      
      // 计算所有涓流阶段的总时长
      let duration = 0;
      tricklePhases.forEach(phase => {
        if (phase.start_time && phase.end_time) {
          const startTime = new Date(phase.start_time);
          const endTime = new Date(phase.end_time);
          duration += (endTime - startTime) / 1000; // 转换为秒
        }
      });
      
      return duration;
    },
    
    // 总充电时长 (秒)
    totalChargingTime() {
      if (!this.currentRecord.start_time || !this.currentRecord.end_time) {
        return 0;
      }
      
      const startTime = new Date(this.currentRecord.start_time);
      const endTime = new Date(this.currentRecord.end_time);
      return (endTime - startTime) / 1000; // 转换为秒
    },
    
    // 恒流阶段百分比
    ccPercentage() {
      if (this.totalChargingTime === 0) {
        return 0;
      }
      return (this.ccDuration / this.totalChargingTime) * 100;
    },
    
    // 恒压阶段百分比
    cvPercentage() {
      if (this.totalChargingTime === 0) {
        return 0;
      }
      return (this.cvDuration / this.totalChargingTime) * 100;
    },
    
    // 涓流阶段百分比
    tricklePercentage() {
      if (this.totalChargingTime === 0) {
        return 0;
      }
      return (this.trickleDuration / this.totalChargingTime) * 100;
    }
  },
  watch: {
    records: {
      handler(newRecords) {
        if (newRecords && newRecords.length > 0) {
          // 当记录更新时，默认选择最新的记录
          this.currentRecordIndex = newRecords.length - 1;
        }
      },
      immediate: true
    }
  },
  methods: {
    // 选择记录
    selectRecord(index) {
      this.currentRecordIndex = index;
    },
    
    // 格式化时间
    formatDuration(seconds) {
      if (!seconds || seconds <= 0) {
        return '00:00:00';
      }
      
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      
      return [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        remainingSeconds.toString().padStart(2, '0')
      ].join(':');
    },
    
    // 格式化日期时间
    formatDateTime(dateString) {
      if (!dateString) {
        return '';
      }
      
      const date = new Date(dateString);
      
      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const day = date.getDate().toString().padStart(2, '0');
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    },
    
    // 格式化时间
    formatTime(dateString) {
      if (!dateString) return 'N/A';
      
      const date = new Date(dateString);
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },
    
    // 计算记录的充电时长
    calculateRecordDuration(record) {
      if (!record.start_time || !record.end_time) {
        return '00:00:00';
      }
      
      const startTime = new Date(record.start_time);
      const endTime = new Date(record.end_time);
      const durationSeconds = (endTime - startTime) / 1000;
      
      return this.formatDuration(durationSeconds);
    },

    formatPercentage(value) {
      return value ? `${value.toFixed(1)} %` : 'N/A';
    },

    formatTemperature(temp) {
      return temp ? `${temp.toFixed(1)} °C` : 'N/A';
    },
    
    formatResistance(resistance) {
      return resistance ? `${(resistance * 1000).toFixed(0)} mΩ` : 'N/A';
    }
  }
}
</script>

<style scoped>
.charging-stats {
  width: 100%;
}

.no-records {
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
}

.stats-summary {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.summary-item {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.summary-item h3 {
  margin-bottom: 0.5rem;
  font-size: 1rem;
  color: var(--dark-color);
}

.summary-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
}

.phase-bars {
  display: flex;
  height: 2rem;
  border-radius: 4px;
  overflow: hidden;
  background-color: #ecf0f1;
}

.phase-bar {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.8rem;
  transition: width 0.5s ease;
  position: relative;
}

.phase-label {
  white-space: nowrap;
  padding: 0 0.5rem;
}

.cc-phase {
  background-color: var(--primary-color);
}

.cv-phase {
  background-color: var(--warning-color);
}

.trickle-phase {
  background-color: var(--success-color);
}

.charging-parameters {
  margin-bottom: 2rem;
}

.charging-parameters h3,
.charging-history h3 {
  margin-bottom: 1rem;
  color: var(--dark-color);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.parameters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.parameter-item {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.parameter-label {
  font-weight: bold;
  color: var(--dark-color);
  margin-right: 0.5rem;
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background-color: #ecf0f1;
}

.history-item.active {
  background-color: #e8f4f8;
  border-left: 4px solid var(--primary-color);
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.history-title {
  font-weight: bold;
  color: var(--dark-color);
}

.history-time {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.history-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.history-stat {
  display: flex;
  align-items: center;
}

.stat-label {
  font-weight: bold;
  margin-right: 0.5rem;
}

.history-note {
  text-align: center;
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-top: 1rem;
}

.history-table-container {
  margin-bottom: 1.5rem;
  overflow-x: auto;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.history-table th,
.history-table td {
  padding: 0.5rem;
  text-align: center;
  border: 1px solid #ddd;
}

.history-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.history-table tr:nth-child(even) {
  background-color: #f9f9f9;
}

.history-table tr:hover {
  background-color: #f0f0f0;
}

@media (max-width: 768px) {
  .stats-summary {
    grid-template-columns: 1fr;
  }
  
  .parameters-grid {
    grid-template-columns: 1fr;
  }
}
</style> 