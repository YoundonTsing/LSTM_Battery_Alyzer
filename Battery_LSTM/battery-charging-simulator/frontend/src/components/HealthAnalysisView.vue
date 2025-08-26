<template>
  <div class="health-info-container card">
    <BatteryHealthInfo 
      :healthInfo="batteryState.health_info" 
      :chargingOptimization="batteryState.charging_optimization"
      :healthWarnings="batteryState.health_warnings"
      :capacity="60" 
    />
  </div>
</template>

<script>
import BatteryHealthInfo from './BatteryHealthInfo.vue';

export default {
  name: 'HealthAnalysisView',
  components: {
    BatteryHealthInfo,
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
.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 1.5rem;
}
</style>