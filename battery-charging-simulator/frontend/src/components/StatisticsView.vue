<template>
  <div class="stats-container card">
    <ChargingStats :records="records" />
  </div>
</template>

<script>
import ChargingStats from './ChargingStats.vue';

export default {
  name: 'StatisticsView',
  components: {
    ChargingStats,
  },
  props: {
    records: {
      type: Array,
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