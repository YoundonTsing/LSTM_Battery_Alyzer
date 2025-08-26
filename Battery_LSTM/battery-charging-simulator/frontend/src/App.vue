<template>
  <div class="app">
    <header class="app-header">
      <h1>BYD刀片电池充电仿真实验云服务</h1>
      <p class="subtitle">基于比亚迪秦L EV Battery Charge</p>
    </header>
    
    <TopBarMenu :active-item="activeView" @item-selected="setActiveView" />

    <main class="container">
      <div class="connection-status" :class="{ 'connected': isConnected, 'disconnected': !isConnected }">
        {{ isConnected ? '已连接到服务器' : '未连接到服务器' }}
      </div>
      
      <div class="main-content">
        <SimulationDashboard v-if="activeView === 'dashboard'" :battery-state="batteryState" @error="handleError" @show-notification="showNotification" />
        <StatisticsView v-if="activeView === 'statistics'" :records="chargingRecords" />
        <RecordsManagementView v-if="activeView === 'records'" @show-notification="showNotification" />
        <HealthAnalysisView v-if="activeView === 'health'" :battery-state="batteryState" @show-notification="showNotification" />
      </div>
      
      <div v-if="notification.message" :class="['notification', 'notification-' + notification.type]">
        <div class="notification-content">
          <span>{{ notification.message }}</span>
          <button @click="clearNotification" class="notification-close">×</button>
        </div>
      </div>
      
      <div v-if="errorMessage" class="error-message">
        <div class="error-content">
          <span>{{ errorMessage }}</span>
          <button @click="clearError" class="error-close">×</button>
        </div>
      </div>
    </main>
    
    <footer class="app-footer">
      <p>© 2023 电池充电仿真模拟器 | 基于深度学习的电池RUL预测与充电优化</p>
    </footer>
  </div>
</template>

<script>
import BatteryView from './components/BatteryView.vue';
import ControlPanel from './components/ControlPanel.vue';
import ChargingStats from './components/ChargingStats.vue';
import ChargingRecordsManager from './components/ChargingRecordsManager.vue';
import SimulatorControls from './components/SimulatorControls.vue';
import RulOptimizationToggle from './components/ChargingControls.vue';
import BatteryHealthInfo from './components/BatteryHealthInfo.vue';
import TopBarMenu from './components/TopBarMenu.vue';
import SimulationDashboard from './components/SimulationDashboard.vue';
import StatisticsView from './components/StatisticsView.vue';
import RecordsManagementView from './components/RecordsManagementView.vue';
import HealthAnalysisView from './components/HealthAnalysisView.vue';
import api from './services/api';

export default {
  name: 'App',
  components: {
    TopBarMenu,
    SimulationDashboard,
    StatisticsView,
    RecordsManagementView,
    HealthAnalysisView
  },
  data() {
    return {
      activeView: 'dashboard',
      isConnected: false,
      batteryState: {
        soc: 100,
        voltage: 375.0,
        current: 0,
        temperature: 25,
        internal_resistance: 0.100,
        polarization_resistance: 0.050,
        polarization_capacitance: 1000,
        polarization_voltage: 0,
        is_charging: false,
        is_discharging: false,
        charging_mode: 'none',
        charging_current: 0,
        charging_voltage: 0,
        estimated_rul: 100,
        rul_optimized_charging: false
      },
      chargingRecords: [],
      errorMessage: '',
      notification: {
        message: '',
        type: 'info', // 'info', 'success', 'error'
        timer: null
      }
    };
  },
  created() {
    this.connectToServer();
    
    // 添加WebSocket事件监听器
    api.addEventListener('batteryState', this.updateBatteryState);
    api.addEventListener('chargingRecords', this.updateChargingRecords);
    api.addEventListener('connect', this.handleConnect);
    api.addEventListener('disconnect', this.handleDisconnect);
    api.addEventListener('error', this.handleError);
  },
  beforeUnmount() {
    // 移除WebSocket事件监听器
    api.removeEventListener('batteryState', this.updateBatteryState);
    api.removeEventListener('chargingRecords', this.updateChargingRecords);
    api.removeEventListener('connect', this.handleConnect);
    api.removeEventListener('disconnect', this.handleDisconnect);
    api.removeEventListener('error', this.handleError);
    
    // 断开WebSocket连接
    api.disconnect();
  },
  methods: {
    setActiveView(view) {
      this.activeView = view;
    },
    // 连接到服务器
    async connectToServer() {
      try {
        await api.connect();
        this.fetchChargingRecords();
      } catch (error) {
        console.error('连接服务器失败:', error);
        this.handleError(error);
      }
    },
    
    // 获取充电记录
    async fetchChargingRecords() {
      try {
        await api.getChargingRecords();
      } catch (error) {
        console.error('获取充电记录失败:', error);
        this.handleError(error);
      }
    },
    
    // 更新电池状态
    updateBatteryState(data) {
      this.batteryState = { ...data };
    },
    
    // 更新充电记录
    updateChargingRecords(data) {
      this.chargingRecords = [...data];
    },
    
    // 处理连接成功
    handleConnect() {
      this.isConnected = true;
      this.errorMessage = '';
    },
    
    // 处理断开连接
    handleDisconnect() {
      this.isConnected = false;
      if (!this.errorMessage) {
        this.errorMessage = '已断开与服务器的连接，请刷新页面重试。';
      }
    },
    
    // 处理错误
    handleError(error) {
      this.errorMessage = error.message || '发生错误，请刷新页面重试。';
      console.error('Error:', error);
    },
    
    // 清除错误信息
    clearError() {
      this.errorMessage = '';
    },
    
    // 显示通知
    showNotification({ message, type = 'info' }) {
      this.notification.message = message;
      this.notification.type = type;
      
      if(this.notification.timer) clearTimeout(this.notification.timer);
      
      this.notification.timer = setTimeout(() => {
        this.clearNotification();
      }, 5000);
    },
    
    // 清除通知
    clearNotification() {
      this.notification.message = '';
      this.notification.type = 'info';
      if(this.notification.timer) {
        clearTimeout(this.notification.timer);
        this.notification.timer = null;
      }
    },
  }
};
</script>

<style scoped>
/* 基本应用样式 */
.app {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f0f2f5;
  color: #333;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #005A9E;
  color: white;
  padding: 1.5rem 2rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 2rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  font-size: 1rem;
  opacity: 0.9;
}

.container {
  flex-grow: 1;
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 连接状态 */
.connection-status {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-align: center;
  margin-bottom: 1rem;
  font-weight: bold;
}
.connected { background-color: #d4edda; color: #155724; }
.disconnected { background-color: #f8d7da; color: #721c24; }

/* 主布局 */
.main-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto auto auto;
  gap: 1.5rem;
  grid-template-areas: 
    "battery control"
    "optimization control"
    "stats stats"
    "manager manager"
    "health health";
}

@media (max-width: 1200px) {
  .main-layout {
    grid-template-columns: 1fr;
    grid-template-areas: 
      "battery"
      "optimization"
      "control"
      "stats"
      "manager"
      "health";
  }
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 1.5rem;
}

.card-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #333;
}

.battery-container { grid-area: battery; }
.optimization-container { grid-area: optimization; }
.control-container { grid-area: control; }
.stats-container { grid-area: stats; }
.records-manager-container { grid-area: manager; }
.health-info-container { grid-area: health; }

.control-panel-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 电池状态 */
.battery-stats-container {
  /* 样式与ControlPanel一致 */
}

.battery-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-weight: bold;
  font-size: 0.9em;
  color: #555;
}

.stat-value {
  font-size: 1.1em;
}

.rul-indicator {
  width: 100%;
  height: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 4px;
}

.rul-bar {
  height: 100%;
  transition: width 0.5s ease;
}

/* 错误与通知消息 */
.error-message, .notification {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 1rem 1.5rem;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  align-items: center;
  max-width: 90%;
}

.error-message { background-color: #e74c3c; color: white; }
.notification-info { background-color: #3498db; color: white; }
.notification-success { background-color: #2ecc71; color: white; }
.notification-error { background-color: #e74c3c; color: white; }

.error-content, .notification-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.error-close, .notification-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  margin-left: 1rem;
  cursor: pointer;
  opacity: 0.8;
}
.error-close:hover, .notification-close:hover {
  opacity: 1;
}

.app-footer {
  text-align: center;
  padding: 1rem;
  color: #666;
  font-size: 0.9em;
}
</style> 