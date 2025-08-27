<template>
  <div class="battery-health-info">
    <h3 class="info-title">电池健康评估</h3>
    
    <div class="health-status" v-if="healthInfo">
      <div class="status-header">
        <div class="status-indicator" :class="statusClass">
          <div class="status-icon">{{ statusIcon }}</div>
          <div class="status-text">{{ healthInfo.status }}</div>
        </div>
        
        <div class="health-grade">
          <div class="grade-badge" :class="gradeClass">{{ healthInfo.grade }}</div>
          <div class="health-score">{{ healthInfo.score }}分</div>
        </div>
      </div>
      
      <!-- 添加健康警告显示 -->
      <div class="health-warnings" v-if="healthWarnings && healthWarnings.length > 0">
        <div v-for="(warning, index) in healthWarnings" :key="index" class="warning-item" :class="'warning-' + warning.level">
          <div class="warning-icon">⚠️</div>
          <div class="warning-message">{{ warning.message }}</div>
        </div>
      </div>
      
      <div class="health-details">
        <div class="detail-item">
          <span class="detail-label">RUL百分比:</span>
          <span class="detail-value">{{ healthInfo.rul_percentage.toFixed(2) }}%</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">估计剩余循环:</span>
          <span class="detail-value">{{ healthInfo.estimated_remaining_cycles }} 次</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">估计剩余月数:</span>
          <span class="detail-value">{{ healthInfo.estimated_remaining_months }} 个月</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">已完成循环:</span>
          <span class="detail-value">{{ healthInfo.cycle_count.toFixed(2) }} 次</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">健康百分比:</span>
          <span class="detail-value">{{ healthInfo.health_percentage.toFixed(2) }}%</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">电压稳定性:</span>
          <span class="detail-value">{{ healthInfo.voltage_stability.toFixed(4) }} V</span>
        </div>
      </div>
      
      <div class="advanced-details">
        <h4>详细指标</h4>
        <div class="advanced-grid">
          <div class="advanced-item">
            <span class="advanced-label">内阻:</span>
            <span class="advanced-value">{{ healthInfo.internal_resistance.toFixed(4) }} Ω</span>
          </div>
          <div class="advanced-item">
            <span class="advanced-label">内阻趋势:</span>
            <span class="advanced-value" :class="{'warning': healthInfo.internal_resistance_trend > 0.001}">
              {{ (healthInfo.internal_resistance_trend * 1000).toFixed(2) }} mΩ/周期
            </span>
          </div>
          <div class="advanced-item">
            <span class="advanced-label">温度稳定性:</span>
            <span class="advanced-value" :class="{'warning': healthInfo.temperature_stability > 3}">
              {{ healthInfo.temperature_stability.toFixed(2) }} °C
            </span>
          </div>
          <div class="advanced-item">
            <span class="advanced-label">最高温度:</span>
            <span class="advanced-value" :class="{'warning': healthInfo.max_temperature > 40}">
              {{ healthInfo.max_temperature.toFixed(1) }} °C
            </span>
          </div>
          <div class="advanced-item">
            <span class="advanced-label">平均温度:</span>
            <span class="advanced-value">
              {{ healthInfo.avg_temperature.toFixed(1) }} °C
            </span>
          </div>
          <div class="advanced-item">
            <span class="advanced-label">充放电效率:</span>
            <span class="advanced-value" :class="{'warning': healthInfo.charge_efficiency < 0.8}">
              {{ (healthInfo.charge_efficiency * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
      </div>
      
      <div class="optimization-status" v-if="chargingOptimization">
        <h4>充电优化状态</h4>
        <div class="optimization-indicator" :class="{ 'active': chargingOptimization.enabled }">
          <div class="indicator-dot" :class="{ 'active': chargingOptimization.enabled }"></div>
          <span>RUL优化充电: {{ chargingOptimization.enabled ? '已启用' : '已禁用' }}</span>
        </div>
        
        <div v-if="chargingOptimization.enabled && chargingOptimization.adjusted_params" class="params-info">
          <div class="param-item">
            <span class="param-label">充电电流:</span>
            <span class="param-value">
              {{ chargingOptimization.adjusted_params.cc_current ? (chargingOptimization.adjusted_params.cc_current * capacity).toFixed(2) : 'N/A' }} A
              <span class="param-unit">({{ chargingOptimization.adjusted_params.cc_current ? chargingOptimization.adjusted_params.cc_current.toFixed(2) : 'N/A' }}C)</span>
            </span>
          </div>
          <div class="param-item">
            <span class="param-label">充电电压 (400V平台):</span>
            <span class="param-value">
              {{ chargingOptimization.adjusted_params.cv_voltage ? chargingOptimization.adjusted_params.cv_voltage.toFixed(1) : 'N/A' }} V
              <span class="param-unit" v-if="chargingOptimization.adjusted_params.cv_voltage">
                (单体: {{ (chargingOptimization.adjusted_params.cv_voltage / 100).toFixed(3) }}V)
              </span>
            </span>
          </div>
          <div class="param-item">
            <span class="param-label">充电策略:</span>
            <span class="param-value strategy">{{ getStrategyName(chargingOptimization.adjusted_params.charging_strategy) }}</span>
          </div>
          <div class="param-item">
            <span class="param-label">最大SOC:</span>
            <span class="param-value">{{ chargingOptimization.adjusted_params.max_soc || 'N/A' }}%</span>
          </div>
          <!-- 新增：充电建议显示 -->
          <div class="param-item" v-if="chargingOptimization.charging_advice && chargingOptimization.charging_advice.length > 0">
            <span class="param-label">充电建议:</span>
            <div class="charging-advice">
              <div v-for="(advice, index) in chargingOptimization.charging_advice" :key="index" class="advice-item">
                {{ advice }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="usage-pattern">
        <h4>使用模式建议</h4>
        <div class="usage-badge" :class="usageClass">
          {{ healthInfo.usage_pattern }}
        </div>
        <div class="maintenance">
          <span class="maintenance-label">维护周期:</span>
          <span class="maintenance-value">{{ healthInfo.maintenance_schedule }}</span>
        </div>
      </div>
      
      <div class="recommendations">
        <h4>建议</h4>
        <ul>
          <li v-for="(rec, index) in healthInfo.recommendations" :key="index">
            {{ rec }}
          </li>
        </ul>
      </div>
    </div>
    
    <div v-else class="no-data">
      暂无电池健康数据
    </div>
  </div>
</template>

<script>
export default {
  name: 'BatteryHealthInfo',
  props: {
    healthInfo: {
      type: Object,
      default: null
    },
    chargingOptimization: {
      type: Object,
      default: null
    },
    capacity: {
      type: Number,
      default: 60 // 默认容量60Ah
    },
    healthWarnings: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    statusClass() {
      if (!this.healthInfo) return '';
      
      const status = this.healthInfo.status;
      if (status === '良好') return 'status-excellent';
      if (status === '正常') return 'status-good';
      if (status === '一般') return 'status-fair';
      if (status === '较差') return 'status-poor';
      if (status === '需更换') return 'status-critical';
      
      return '';
    },
    statusIcon() {
      if (!this.healthInfo) return '';
      
      const status = this.healthInfo.status;
      if (status === '良好') return '🟢';
      if (status === '正常') return '🟢';
      if (status === '一般') return '🟡';
      if (status === '较差') return '🟠';
      if (status === '需更换') return '🔴';
      
      return '';
    },
    gradeClass() {
      if (!this.healthInfo) return '';
      
      const grade = this.healthInfo.grade;
      if (grade === 'A') return 'grade-a';
      if (grade === 'B+') return 'grade-b-plus';
      if (grade === 'B') return 'grade-b';
      if (grade === 'C') return 'grade-c';
      if (grade === 'D') return 'grade-d';
      
      return '';
    },
    usageClass() {
      if (!this.healthInfo) return '';
      
      const usage = this.healthInfo.usage_pattern;
      if (usage === '正常使用') return 'usage-normal';
      if (usage === '适度使用，避免高负荷') return 'usage-moderate';
      if (usage === '轻度使用，避免深度充放电') return 'usage-light';
      if (usage === '最小化使用，准备更换') return 'usage-minimal';
      
      return '';
    }
  },
  methods: {
    getStrategyName(strategy) {
      const strategies = {
        'standard': '标准模式',
        'eco': '经济模式',
        'longevity': '延寿模式'
      };
      
      // 处理空值或未定义的策略
      if (!strategy || strategy === 'null' || strategy === 'undefined') {
        return '未设置';
      }
      
      return strategies[strategy] || `未知策略 (${strategy})`;
    }
  }
};
</script>

<style scoped>
.battery-health-info {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.info-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #333;
}

.health-status {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  background-color: #f8f9fa;
  flex: 1;
}

.status-icon {
  font-size: 1.5rem;
}

.status-text {
  font-size: 1.2rem;
  font-weight: bold;
}

.health-grade {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 1rem;
  margin-left: 1rem;
}

.grade-badge {
  font-size: 1.8rem;
  font-weight: bold;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-bottom: 0.25rem;
}

.health-score {
  font-size: 0.9rem;
  color: #666;
}

.grade-a {
  background-color: #28a745;
  color: white;
}

.grade-b-plus {
  background-color: #5cb85c;
  color: white;
}

.grade-b {
  background-color: #5bc0de;
  color: white;
}

.grade-c {
  background-color: #f0ad4e;
  color: white;
}

.grade-d {
  background-color: #d9534f;
  color: white;
}

.status-excellent, .status-good {
  background-color: #d4edda;
  color: #155724;
}

.status-fair {
  background-color: #fff3cd;
  color: #856404;
}

.status-poor {
  background-color: #ffe5d0;
  color: #fd7e14;
}

.status-critical {
  background-color: #f8d7da;
  color: #721c24;
}

.health-warnings {
  margin-bottom: 1rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.warning-high {
  background-color: #f8d7da;
  color: #721c24;
}

.warning-warning {
  background-color: #fff3cd;
  color: #856404;
}

.warning-low {
  background-color: #d1ecf1;
  color: #0c5460;
}

.warning-icon {
  font-size: 1.2rem;
}

.warning-message {
  font-size: 0.95rem;
  font-weight: 500;
}

.health-details {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
}

.detail-label {
  font-size: 0.9rem;
  color: #6c757d;
  margin-bottom: 0.25rem;
}

.detail-value {
  font-size: 1.1rem;
  font-weight: bold;
  color: #333;
}

.advanced-details {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.advanced-details h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1rem;
  color: #333;
}

.advanced-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
}

.advanced-item {
  display: flex;
  flex-direction: column;
}

.advanced-label {
  font-size: 0.85rem;
  color: #6c757d;
}

.advanced-value {
  font-size: 0.95rem;
  font-weight: bold;
}

.advanced-value.warning {
  color: #dc3545;
}

.optimization-status {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.optimization-status h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1rem;
  color: #333;
}

.optimization-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.indicator-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #ccc;
}

.indicator-dot.active {
  background-color: #2ecc71;
}

.params-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.param-item {
  display: flex;
  flex-direction: column;
}

.param-label {
  font-size: 0.85rem;
  color: #6c757d;
}

.param-value {
  font-size: 1rem;
  font-weight: bold;
}

.param-value.strategy {
  color: #007bff;
}

/* 新增样式 */
.param-unit {
  font-size: 0.85em;
  color: #6c757d;
  margin-left: 0.5rem;
}

.charging-advice {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.advice-item {
  font-size: 0.9rem;
  color: #495057;
  background-color: #e9ecef;
  padding: 0.5rem;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.usage-pattern {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.usage-pattern h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1rem;
  color: #333;
}

.usage-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: bold;
  margin-bottom: 0.75rem;
}

.usage-normal {
  background-color: #d4edda;
  color: #155724;
}

.usage-moderate {
  background-color: #d1ecf1;
  color: #0c5460;
}

.usage-light {
  background-color: #fff3cd;
  color: #856404;
}

.usage-minimal {
  background-color: #f8d7da;
  color: #721c24;
}

.maintenance {
  display: flex;
  flex-direction: column;
  margin-top: 0.5rem;
}

.maintenance-label {
  font-size: 0.85rem;
  color: #6c757d;
}

.maintenance-value {
  font-size: 0.95rem;
  font-weight: bold;
}

.recommendations {
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
}

.recommendations h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1rem;
  color: #333;
}

.recommendations ul {
  margin: 0;
  padding-left: 1.5rem;
}

.recommendations li {
  margin-bottom: 0.5rem;
}

.no-data {
  padding: 2rem;
  text-align: center;
  color: #6c757d;
  background-color: #f8f9fa;
  border-radius: 6px;
}

@media (max-width: 768px) {
  .battery-health-info {
    padding: 1rem;
  }
  
  .health-details {
    grid-template-columns: 1fr;
  }
  
  .status-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .health-grade {
    margin-left: 0;
    margin-top: 0.5rem;
    flex-direction: row;
    gap: 0.5rem;
    align-items: center;
  }
  
  .grade-badge {
    margin-bottom: 0;
  }
}
</style> 