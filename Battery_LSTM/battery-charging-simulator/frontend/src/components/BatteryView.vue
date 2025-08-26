<template>
  <div class="battery-view-container">
    <div class="battery-view">
      <svg
        :width="width * 1.5"
        :height="height * 1.5"
        viewBox="0 0 200 400"
        class="battery-svg"
      >
        <!-- 电池外壳 -->
        <rect
          x="40"
          y="40"
          width="120"
          height="320"
          rx="10"
          ry="10"
          class="battery-case"
        />
        
        <!-- 电池正极 -->
        <rect
          x="70"
          y="10"
          width="60"
          height="30"
          rx="5"
          ry="5"
          class="battery-terminal"
        />
        
        <!-- 电池内部 (背景) -->
        <rect
          x="50"
          y="50"
          width="100"
          height="300"
          rx="5"
          ry="5"
          class="battery-inside"
        />
        
        <!-- 电池电量 -->
        <rect
          x="50"
          :y="350 - socHeight"
          width="100"
          :height="socHeight"
          rx="5"
          ry="5"
          :class="['battery-level', batteryLevelClass]"
          style="transition: all 0.5s ease-in-out"
        />
        
        <!-- 电池百分比文字 -->
        <text
          x="100"
          y="200"
          text-anchor="middle"
          dominant-baseline="middle"
          class="battery-text"
        >{{ formattedSoc }}</text>
        
        <!-- 充电图标 (充电状态显示) -->
        <g v-if="isCharging" class="charging-icon">
          <path
            d="M95,130 L85,160 L95,160 L85,190 L115,160 L105,160 L115,130 Z"
            fill="#ffffff"
          />
        </g>
        
        <!-- 放电图标 (放电状态显示) -->
        <g v-if="isDischarging" class="discharging-icon">
          <path
            d="M85,130 L115,130 L115,145 L105,145 L105,175 L115,175 L85,175 Z"
            fill="#ffffff"
          />
        </g>
        
        <!-- 温度指示器 -->
        <g class="temperature-indicator" :transform="`translate(170, ${temperatureY})`">
          <rect x="0" y="-10" width="20" height="20" rx="3" ry="3" :class="temperatureClass" />
          <text x="10" y="3" text-anchor="middle" dominant-baseline="middle" class="temperature-text">{{ temperatureIcon }}</text>
        </g>
      </svg>
    </div>
    
    <div class="thevenin-model">
      <h3>戴维南等效电路模型</h3>
      <svg width="600" height="300" viewBox="0 0 300 150" class="thevenin-svg">
        <!-- 电池OCV -->
        <circle cx="40" cy="75" r="20" class="ocv-circle" />
        <text x="40" y="75" text-anchor="middle" dominant-baseline="middle" class="model-text">OCV</text>
        <text x="40" y="100" text-anchor="middle" dominant-baseline="middle" class="model-value">{{ calculateOcv().toFixed(1) }}V</text>
        
        <!-- 内阻R0 -->
        <line x1="60" y1="75" x2="120" y2="75" stroke="#333" stroke-width="2" />
        <rect x="80" y="65" width="30" height="20" class="resistance-rect" />
        <text x="95" y="75" text-anchor="middle" dominant-baseline="middle" class="model-text">R0</text>
        <text x="95" y="95" text-anchor="middle" dominant-baseline="middle" class="model-value">{{ internalResistance.toFixed(3) }}Ω</text>
        
        <!-- 极化电阻R1 -->
        <line x1="120" y1="75" x2="120" y2="40" stroke="#333" stroke-width="2" />
        <line x1="120" y1="40" x2="180" y2="40" stroke="#333" stroke-width="2" />
        <rect x="140" y="30" width="30" height="20" class="resistance-rect" />
        <text x="155" y="40" text-anchor="middle" dominant-baseline="middle" class="model-text">R1</text>
        <text x="155" y="60" text-anchor="middle" dominant-baseline="middle" class="model-value">{{ polarizationResistance.toFixed(3) }}Ω</text>
        
        <!-- 极化电容C1 -->
        <line x1="180" y1="40" x2="180" y2="110" stroke="#333" stroke-width="2" />
        <line x1="170" y1="75" x2="190" y2="75" stroke="#333" stroke-width="2" />
        <line x1="170" y1="85" x2="190" y2="85" stroke="#333" stroke-width="2" />
        <path d="M180,85 L180,110" stroke="#333" stroke-width="2" />
        <text x="180" y="65" text-anchor="middle" dominant-baseline="middle" class="model-text">C1</text>
        <text x="180" y="130" text-anchor="middle" dominant-baseline="middle" class="model-value">{{ polarizationCapacitance.toFixed(0) }}F</text>
        
        <!-- 电流方向 -->
        <line x1="120" y1="75" x2="220" y2="75" stroke="#333" stroke-width="2" />
        <polygon points="215,70 230,75 215,80" :fill="displayCurrent > 0 ? '#4CAF50' : '#F44336'" />
        <text x="200" y="65" text-anchor="middle" dominant-baseline="middle" class="model-text">I</text>
        <text x="200" y="95" text-anchor="middle" dominant-baseline="middle" class="model-value">{{ displayCurrent.toFixed(1) }}A</text>
        
        <!-- 端电压 -->
        <line x1="220" y1="75" x2="220" y2="110" stroke="#333" stroke-width="2" />
        <line x1="40" y1="110" x2="220" y2="110" stroke="#333" stroke-width="2" />
        <text x="130" y="125" text-anchor="middle" dominant-baseline="middle" class="model-text">端电压: {{ displayVoltage.toFixed(1) }}V</text>
        
        <!-- 电压分布 -->
        <text x="40" y="15" text-anchor="middle" dominant-baseline="middle" class="model-text">OCV</text>
        <text x="95" y="15" text-anchor="middle" dominant-baseline="middle" class="model-text">IR0</text>
        <text x="155" y="15" text-anchor="middle" dominant-baseline="middle" class="model-text">RC</text>
        <rect x="10" y="20" width="60" height="10" class="voltage-bar ocv-bar" />
        <rect x="70" y="20" :width="getR0VoltageDrop()" height="10" class="voltage-bar r0-bar" />
        <rect x="70" y="20" :x="70 + getR0VoltageDrop()" :width="getPolarizationVoltageDrop()" height="10" class="voltage-bar rc-bar" />
      </svg>
    </div>
    
  </div>
</template>

<script>
export default {
  name: 'BatteryView',
  props: {
    soc: {
      type: Number,
      default: 100
    },
    voltage: {
      type: Number,
      default: 375.0
    },
    current: {
      type: Number,
      default: 0
    },
    display_voltage: {
      type: Number,
      default: null
    },
    display_current: {
      type: Number,
      default: null
    },
    temperature: {
      type: Number,
      default: 25
    },
    internalResistance: {
      type: Number,
      default: 0.100
    },
    polarizationResistance: {
      type: Number,
      default: 0.050
    },
    polarizationCapacitance: {
      type: Number,
      default: 1000
    },
    polarizationVoltage: {
      type: Number,
      default: 0
    },
    isCharging: {
      type: Boolean,
      default: false
    },
    isDischarging: {
      type: Boolean,
      default: false
    },
    chargingMode: {
      type: String,
      default: 'none'
    },
    estimatedRul: {
      type: Number,
      default: 100
    },
    width: {
      type: Number,
      default: 200
    },
    height: {
      type: Number,
      default: 400
    }
  },
  computed: {
    // 电池电量高度
    socHeight() {
      const maxHeight = 300;
      return (this.soc / 100) * maxHeight;
    },
    
    // 格式化的SOC显示
    formattedSoc() {
      return `${this.soc.toFixed(2)}%`;
    },
    
    // 根据SOC计算电池电量样式类
    batteryLevelClass() {
      if (this.soc > 60) return 'level-high';
      if (this.soc > 20) return 'level-medium';
      return 'level-low';
    },
    
    // 温度指示器的Y位置
    temperatureY() {
      // 温度范围从-20°C到60°C映射到电池高度
      const minTemp = -20;
      const maxTemp = 60;
      const minY = 50;
      const maxY = 350;
      
      const tempPercentage = (this.temperature - minTemp) / (maxTemp - minTemp);
      return maxY - tempPercentage * (maxY - minY);
    },
    
    // 温度图标
    temperatureIcon() {
      if (this.temperature > 45) return '🔥';
      if (this.temperature > 35) return '🔆';
      if (this.temperature < 0) return '❄️';
      return '🌡️';
    },
    
    // 温度指示器颜色类
    temperatureClass() {
      if (this.temperature > 45) return 'temp-high';
      if (this.temperature > 35) return 'temp-warm';
      if (this.temperature < 0) return 'temp-cold';
      return 'temp-normal';
    },
    
    // 充电模式文本
    chargingModeText() {
      if (this.isCharging) {
        switch (this.chargingMode) {
          case 'cc': return '恒流充电';
          case 'cv': return '恒压充电';
          case 'trickle': return '涓流充电';
          default: return '充电中';
        }
      } else if (this.isDischarging) {
        return '放电中';
      }
      return '待机';
    },
    
    // RUL 颜色指示
    rulColor() {
      const rul = Math.min(100, Math.max(0, this.estimatedRul));
      if (rul > 70) return '#2ecc71'; // 绿色，健康状态良好
      if (rul > 40) return '#f39c12'; // 橙色，健康状态中等
      return '#e74c3c';              // 红色，健康状态较差
    },
    
    // 显示电压
    displayVoltage() {
      return this.display_voltage !== null ? this.display_voltage : this.voltage;
    },
    // 显示电流（确保放电时为负值）
    displayCurrent() {
      // 优先使用display_current属性
      const currentValue = this.display_current !== null ? this.display_current : this.current;
      
      if (this.isDischarging) {
        return -Math.abs(currentValue);
      }
      return currentValue;
    }
  },
  methods: {
    calculateOcv() {
      // 根据SOC计算开路电压的简化模型
      const soc = this.soc;
      const minVoltage = 290;
      const nominalVoltage = 375;
      const ccToCvVoltage = 395;
      const maxVoltage = 400;
      
      if (soc <= 10) {
        // 低SOC区域
        return minVoltage + (nominalVoltage - minVoltage) * soc / 10;
      } else if (soc <= 90) {
        // 中SOC区域
        return nominalVoltage + (ccToCvVoltage - nominalVoltage) * (soc - 10) / 80;
      } else {
        // 高SOC区域
        return ccToCvVoltage + (maxVoltage - ccToCvVoltage) * (soc - 90) / 10;
      }
    },
    getR0VoltageDrop() {
      // 计算R0上的电压降，并映射到图表上的宽度
      const voltageDrop = Math.abs(this.current * this.internalResistance);
      return Math.min(60, voltageDrop * 6); // 最大宽度60，比例因子6
    },
    getPolarizationVoltageDrop() {
      // 计算极化电压，并映射到图表上的宽度
      return Math.min(60, Math.abs(this.polarizationVoltage) * 6); // 最大宽度60，比例因子6
    }
  }
}
</script>

<style scoped>
.battery-view-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
}

.battery-view {
  position: relative;
  margin-bottom: 0.9rem;  /* 从0.75rem改为0.9rem，增加了1.2倍距离 */
}

.battery-svg {
  display: block;
  margin: 0 auto;
}

.battery-case {
  fill: #333;
  stroke: #222;
  stroke-width: 2;
}

.battery-terminal {
  fill: #444;
  stroke: #222;
  stroke-width: 2;
}

.battery-inside {
  fill: #f8f9fa;
  stroke: none;
}

.battery-level {
  stroke: none;
}

.level-high {
  fill: #2ecc71;
}

.level-medium {
  fill: #f39c12;
}

.level-low {
  fill: #e74c3c;
}

.battery-text {
  fill: #333;
  font-size: 24px;
  font-weight: bold;
  user-select: none;
}

.charging-icon, .discharging-icon {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.temperature-indicator rect {
  stroke: #333;
  stroke-width: 1;
}

.temp-normal {
  fill: #3498db;
}

.temp-warm {
  fill: #f39c12;
}

.temp-high {
  fill: #e74c3c;
}

.temp-cold {
  fill: #3498db;
}

.temperature-text {
  fill: white;
  font-size: 14px;
  user-select: none;
}

.thevenin-model {
  margin-top: 0.9rem;  /* 从0.75rem改为0.9rem，增加了1.2倍距离 */
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.thevenin-model h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  text-align: center;
}

.thevenin-svg {
  width: 100%;
  max-width: 600px;  /* 从300px改为600px */
  margin: 0 auto;
  display: block;
}

.ocv-circle {
  fill: #2196F3;
  stroke: #0D47A1;
  stroke-width: 2px;
}

.resistance-rect {
  fill: #FF9800;
  stroke: #E65100;
  stroke-width: 1px;
}

.model-text {
  font-size: 10px;
  font-weight: bold;
  fill: #333;
}

.model-value {
  font-size: 8px;
  fill: #666;
}

.voltage-bar {
  stroke: #333;
  stroke-width: 0.5px;
}

.ocv-bar {
  fill: #2196F3;
}

.r0-bar {
  fill: #FF9800;
}

.rc-bar {
  fill: #4CAF50;
}

.battery-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  width: 100%;
  max-width: 300px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-weight: bold;
  color: #333;
}

.stat-value {
  color: #2c3e50;
}

.rul-indicator {
  width: 100%;
  height: 4px;
  background-color: #f1f1f1;
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
}

.rul-bar {
  height: 100%;
  transition: width 0.5s ease-in-out, background-color 0.5s ease-in-out;
}

@media (max-width: 768px) {
  .battery-stats {
    grid-template-columns: 1fr;
  }
}
</style> 