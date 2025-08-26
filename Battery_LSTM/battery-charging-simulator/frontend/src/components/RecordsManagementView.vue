<template>
  <div class="records-manager-container card">
    <ChargingRecordsManager @show-notification="(payload) => $emit('show-notification', payload)" />
  </div>
</template>

<script>
import ChargingRecordsManager from './ChargingRecordsManager.vue';

export default {
  name: 'RecordsManagementView',
  components: {
    ChargingRecordsManager,
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