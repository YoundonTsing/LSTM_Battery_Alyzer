<template>
  <div class="dashboard-layout">
    <div class="battery-container card">
      <BatteryView 
        :soc="batteryState.soc"
        :voltage="batteryState.voltage"
        :current="batteryState.current"
        :display-voltage="batteryState.display_voltage"
        :display-current="batteryState.display_current"
        :temperature="batteryState.temperature"
        :internal-resistance="batteryState.internal_resistance"
        :polarization-resistance="batteryState.polarization_resistance || 0.050"
        :polarization-capacitance="batteryState.polarization_capacitance || 1000"
        :polarization-voltage="batteryState.polarization_voltage || 0"
        :is-charging="batteryState.is_charging"
        :is-discharging="batteryState.is_discharging"
        :charging-mode="batteryState.charging_mode"
        :estimated-rul="batteryState.estimated_rul"
      />
    </div>
    
    <div class="optimization-container card">
      <RulOptimizationToggle 
        :rulOptimizedCharging="batteryState.rul_optimized_charging"
        :isCharging="batteryState.is_charging"
        @show-notification="(payload) => $emit('show-notification', payload)" 
      />
    </div>
    
    <div class="control-container">
      <div class="control-panel-layout">
        <ControlPanel 
          :is-charging="batteryState.is_charging"
          :is-discharging="batteryState.is_discharging"
          :charging-mode="batteryState.charging_mode"
          :estimated-rul="batteryState.estimated_rul"
          :soc="batteryState.soc"
          :charging-current="batteryState.charging_current"
          :charging-voltage="batteryState.charging_voltage"
          :display-current="batteryState.display_current"
          :display-voltage="batteryState.display_voltage"
          @error="(payload) => $emit('error', payload)"
        />
        
        <div class="battery-stats-container card">
          <h2 class="card-title">电池状态</h2>
          <div class="battery-stats">
            <div class="stat-item">
              <span class="stat-label">SOC:</span>
              <span class="stat-value">{{ batteryState.soc.toFixed(2) }}%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">电压 (400V平台):</span>
              <span class="stat-value">
                {{ (batteryState.display_voltage || batteryState.voltage).toFixed(1) }} V
                <span class="voltage-range">
                  ({{ getVoltagePercentage(batteryState.display_voltage || batteryState.voltage) }}%)
                </span>
              </span>
              <div class="voltage-indicator">
                <div class="voltage-bar" :style="{width: `${getVoltagePercentage(batteryState.display_voltage || batteryState.voltage)}%`, backgroundColor: getVoltageColor(batteryState.display_voltage || batteryState.voltage)}"></div>
              </div>
            </div>
            <div class="stat-item">
              <span class="stat-label">电流:</span>
              <span class="stat-value">
                {{ batteryState.is_charging 
                  ? (batteryState.display_current || batteryState.charging_current).toFixed(1) 
                  : (batteryState.is_discharging 
                    ? (-(batteryState.display_current || batteryState.discharging_current)).toFixed(1) 
                    : (batteryState.display_current || batteryState.current).toFixed(1)) }} A
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">温度:</span>
              <span class="stat-value">{{ batteryState.temperature.toFixed(1) }} °C</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">内阻:</span>
              <span class="stat-value">{{ batteryState.internal_resistance.toFixed(3) }} Ω</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">RUL:</span>
              <span class="stat-value">{{ Math.min(100, Math.max(0, batteryState.estimated_rul)).toFixed(2) }}%</span>
              <div class="rul-indicator">
                <div class="rul-bar" :style="{width: `${Math.min(100, Math.max(0, batteryState.estimated_rul))}%`, backgroundColor: getRulColor(batteryState.estimated_rul)}"></div>
              </div>
            </div>
            <div class="stat-item">
              <span class="stat-label">模式:</span>
              <span class="stat-value">{{ getChargingModeText(batteryState) }}</span>
            </div>
          </div>
        </div>
        
        <SimulatorControls @show-notification="(payload) => $emit('show-notification', payload)" />
      </div>
    </div>
  </div>
</template>

<script>
import BatteryView from './BatteryView.vue';
import ControlPanel from './ControlPanel.vue';
import SimulatorControls from './SimulatorControls.vue';
import RulOptimizationToggle from './ChargingControls.vue';

export default {
  name: 'SimulationDashboard',
  components: {
    BatteryView,
    ControlPanel,
    SimulatorControls,
    RulOptimizationToggle,
  },
  props: {
    batteryState: {
      type: Object,
      required: true,
    },
  },
  methods: {
    getRulColor(rul) {
      const rulValue = Math.min(100, Math.max(0, rul));
      if (rulValue > 70) return '#2ecc71';
      if (rulValue > 40) return '#f39c12';
      return '#e74c3c';
    },
    getChargingModeText(state) {
      if (state.is_charging) {
        switch (state.charging_mode) {
          case 'cc': return '恒流充电';
          case 'cv': return '恒压充电';
          case 'trickle': return '涓流充电';
          default: return '充电中';
        }
      } else if (state.is_discharging) {
        return '放电中';
      }
      return '待机';
    },
    // 400V平台电压百分比计算
    getVoltagePercentage(voltage) {
      const minVoltage = 290; // 最低电压
      const maxVoltage = 400; // 最高电压
      const percentage = ((voltage - minVoltage) / (maxVoltage - minVoltage)) * 100;
      return Math.min(100, Math.max(0, percentage)).toFixed(1);
    },
    // 400V平台电压颜色指示
    getVoltageColor(voltage) {
      const percentage = this.getVoltagePercentage(voltage);
      if (percentage >= 95) return '#e74c3c'; // 过高电压，红色
      if (percentage >= 80) return '#2ecc71'; // 正常充电，绿色
      if (percentage >= 60) return '#f39c12'; // 中等电压，黄色
      if (percentage >= 30) return '#3498db'; // 低电压，蓝色
      return '#e74c3c'; // 极低电压，红色
    },
  },
};
</script>

<style scoped>
.dashboard-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 1.5rem;
  grid-template-areas: 
    "battery control"
    "optimization control";
}

@media (max-width: 1200px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
    grid-template-areas: 
      "battery"
      "optimization"
      "control";
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

.control-panel-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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

/* 400V平台电压指示器样式 */
.voltage-range {
  font-size: 0.85em;
  color: #666;
  margin-left: 0.5rem;
}

.voltage-indicator {
  width: 100%;
  height: 6px;
  background-color: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 4px;
}

.voltage-bar {
  height: 100%;
  transition: width 0.5s ease, background-color 0.3s ease;
}
</style>