<template>
  <div class="health-analysis-view">
    <!-- RUL模型管理 -->
    <ModelManager @show-notification="$emit('show-notification', $event)" />
    
    <!-- 详细健康信息 -->
    <div class="health-info-container card">
      <BatteryHealthInfo 
        :healthInfo="batteryState.health_info" 
        :chargingOptimization="batteryState.charging_optimization"
        :healthWarnings="batteryState.health_warnings"
        :capacity="60" 
      />
    </div>
  </div>
</template>

<script>
import BatteryHealthInfo from './BatteryHealthInfo.vue';
import ModelManager from './ModelManager.vue';

export default {
  name: 'HealthAnalysisView',
  components: {
    BatteryHealthInfo,
    ModelManager,
  },
  props: {
    batteryState: {
      type: Object,
      required: true,
    },
  },
};
</script>

<style scoped>
.health-analysis-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 1.5rem;
}
</style>