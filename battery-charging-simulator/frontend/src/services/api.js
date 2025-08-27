import { io } from 'socket.io-client';

class BatteryAPI {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.listeners = {
      batteryState: [],
      chargingRecords: [],
      chargingStatistics: [],
      connect: [],
      disconnect: [],
      error: [],
      chargingRecordsSearchResult: [], // Added for search results
      trainProgress: [],
      trainCompleted: []
    };
    this.clientId = this._generateClientId();
  }

  // 连接WebSocket
  connect() {
    if (this.socket) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      // 连接到WebSocket端点
      this.socket = io('http://localhost:8001', {
        path: '/ws',
        transports: ['polling', 'websocket'], // 允许降级到polling
        reconnectionAttempts: 10,
        reconnectionDelay: 2000,
        timeout: 10000,
        forceNew: true
      });

      // 监听连接成功事件
      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this._notifyListeners('connect');
        resolve();
      });

      // 监听断开连接事件
      this.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this._notifyListeners('disconnect');
      });

      // 监听错误事件
      this.socket.on('error', (error) => {
        console.error('WebSocket error:', error);
        this._notifyListeners('error', error);
        reject(error);
      });

      // 监听电池状态更新
      this.socket.on('battery_state', (data) => {
        this._notifyListeners('batteryState', data);
      });

      // 监听充电记录更新
      this.socket.on('charging_records', (data) => {
        console.log("Received charging_records event with data:", data);
        this._notifyListeners('chargingRecords', data);
      });
      
      this.socket.on('charging_records_search_result', (data) => {
        console.log("Received charging_records_search_result event with data:", data);
        this._notifyListeners('chargingRecordsSearchResult', data);
      });
      
      // 监听充电统计信息更新
      this.socket.on('charging_statistics', (data) => {
        this._notifyListeners('chargingStatistics', data);
      });

      // 训练进度与完成
      this.socket.on('train_progress', (data) => {
        this._notifyListeners('trainProgress', data);
      });
      this.socket.on('train_completed', (data) => {
        this._notifyListeners('trainCompleted', data);
      });
    });
  }

  // 断开WebSocket连接
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }

  // ===== RUL 数据集与训练 =====
  async uploadDataset(datasetId, file) {
    const form = new FormData();
    form.append('datasetId', datasetId);
    form.append('file', file);
    const resp = await fetch('http://localhost:8001/api/rul/dataset/upload', {
      method: 'POST',
      body: form
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`上传失败: ${txt}`);
    }
    return resp.json();
  }

  async triggerTrain({ datasetId, k = null, epochs = null, batchSize = null }) {
    const resp = await fetch('http://localhost:8001/api/rul/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ datasetId, k, epochs, batchSize })
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`触发训练失败: ${txt}`);
    }
    return resp.json();
  }

  async getTrainStatus(jobId) {
    const resp = await fetch(`http://localhost:8001/api/rul/train/${jobId}/status`);
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`获取训练状态失败: ${txt}`);
    }
    return resp.json();
  }

  // 轮询训练状态 (WebSocket备选方案)
  startTrainStatusPolling(jobId, onProgress, onCompleted, intervalMs = 3000) {
    if (this._pollingInterval) {
      clearInterval(this._pollingInterval);
    }
    
    this._pollingInterval = setInterval(async () => {
      try {
        const status = await this.getTrainStatus(jobId);
        
        // 模拟进度事件
        if (onProgress && status.logs) {
          // 发送最近的日志作为进度
          const recentLogs = status.logs.slice(-5); // 最近5条日志
          recentLogs.forEach(log => {
            onProgress({ jobId, message: log });
          });
        }
        
        // 检查是否完成
        if (status.status === 'completed' || status.status === 'failed') {
          this.stopTrainStatusPolling();
          if (onCompleted) {
            onCompleted({
              jobId,
              success: status.status === 'completed',
              error: status.error || null,
              modelCount: status.modelCount || 0,
              durationSec: status.durationSec || 0
            });
          }
        }
      } catch (error) {
        console.error('轮询训练状态失败:', error);
        // 不停止轮询，继续尝试
      }
    }, intervalMs);
    
    return this._pollingInterval;
  }
  
  stopTrainStatusPolling() {
    if (this._pollingInterval) {
      clearInterval(this._pollingInterval);
      this._pollingInterval = null;
    }
  }

  // 获取服务器状态 (REST API)
  async getServerStatus() {
    try {
      const response = await fetch('http://localhost:8001/api/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      console.log('服务器状态:', data);
      return data;
    } catch (error) {
      console.error('获取服务器状态失败:', error);
      throw error;
    }
  }

  // 开始充电
  startCharging() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'start_charging'
      }));
      resolve();
    });
  }

  // 开始放电
  startDischarging() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'start_discharging'
      }));
      resolve();
    });
  }

  // 停止充放电
  stop() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'stop'
      }));
      resolve();
    });
  }

  // 更新电池参数
  updateBatteryParams(params) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'update_params',
        params
      }));
      resolve();
    });
  }
  
  // 设置模拟器时间加速因子
  setTimeAccelerationFactor(factor) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'update_params',
        params: {
          time_acceleration_factor: factor
        }
      }));
      resolve();
    });
  }
  
  // 设置RUL优化充电状态
  setRulOptimization(enable) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    return new Promise((resolve, reject) => {
      // 创建一个请求ID
      const requestId = Date.now().toString();
      
      // 监听响应
      const handleResponse = (data) => {
        // 移除监听器
        this.socket.off('rul_optimization_response', handleResponse);
        
        if (data.success) {
          resolve(data);
        } else {
          reject(new Error(data.message || '设置RUL优化充电失败'));
        }
      };
      
      // 添加临时监听器
      this.socket.on('rul_optimization_response', handleResponse);
      
      // 发送请求
      this.socket.emit('message', JSON.stringify({
        action: 'set_rul_optimization',
        enable: enable,
        request_id: requestId
      }));
      
      // 设置超时
      setTimeout(() => {
        this.socket.off('rul_optimization_response', handleResponse);
        reject(new Error('设置RUL优化充电请求超时'));
      }, 5000);
    });
  }

  // 获取充电记录
  getChargingRecords() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_charging_records'
      }));
      // 记录会通过charging_records事件返回
      resolve();
    });
  }
  
  // 获取单条充电记录
  getChargingRecordById(recordId) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_charging_record_by_id',
        record_id: recordId
      }));
      // 记录会通过charging_records事件返回
      resolve();
    });
  }
  
  // 获取最近的充电记录
  getRecentChargingRecords(limit = 10) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_recent_charging_records',
        limit: limit
      }));
      // 记录会通过charging_records事件返回
      resolve();
    });
  }
  
  // 按日期范围获取充电记录
  getChargingRecordsByDateRange(startDate, endDate) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_charging_records_by_date_range',
        start_date: startDate,
        end_date: endDate
      }));
      // 记录会通过charging_records事件返回
      resolve();
    });
  }
  
  // 搜索充电记录
  searchChargingRecords(searchParams) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve, reject) => {
      // 创建一个唯一的请求ID
      const requestId = Date.now().toString();
      
      // 创建一次性的事件监听器，用于接收此次搜索的结果
      const handleSearchResult = (data) => {
        console.log("Received search result:", data);
        // 移除监听器，避免内存泄漏
        this.socket.off('charging_records_search_result', handleSearchResult);
        resolve(data);
      };
      
      // 添加临时监听器
      this.socket.on('charging_records_search_result', handleSearchResult);
      
      // 发送搜索请求
      this.socket.emit('message', JSON.stringify({
        action: 'search_charging_records',
        search_params: searchParams,
        request_id: requestId
      }));
      
      // 设置超时，避免永久等待
      setTimeout(() => {
        this.socket.off('charging_records_search_result', handleSearchResult);
        reject(new Error('Search request timeout'));
      }, 10000); // 10秒超时
    });
  }
  
  // 删除充电记录
  deleteChargingRecord(recordId) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'delete_charging_record',
        record_id: recordId
      }));
      resolve();
    });
  }
  
  // 批量删除充电记录
  deleteChargingRecords(recordIds) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'delete_charging_records_by_ids',
        record_ids: recordIds
      }));
      resolve();
    });
  }
  
  // 删除所有充电记录
  deleteAllChargingRecords() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'delete_all_charging_records'
      }));
      resolve();
    });
  }
  
  // 获取充电统计信息
  getChargingStatistics() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_charging_statistics'
      }));
      // 统计信息会通过charging_statistics事件返回
      resolve();
    });
  }
  
  // 获取充电阶段统计信息
  getChargingPhasesStatistics() {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'get_charging_phases_statistics'
      }));
      // 统计信息会通过charging_statistics事件返回
      resolve();
    });
  }
  
  // 导出充电记录到JSON文件
  exportChargingRecordsToJson(recordIds = null) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'export_charging_records_to_json',
        record_ids: recordIds
      }));
      resolve();
    });
  }
  
  // 从JSON文件导入充电记录
  importChargingRecordsFromJson(filePath) {
    if (!this.isConnected) {
      return Promise.reject(new Error('WebSocket not connected'));
    }

    return new Promise((resolve) => {
      this.socket.emit('message', JSON.stringify({
        action: 'import_charging_records_from_json',
        file_path: filePath
      }));
      resolve();
    });
  }

  // 添加事件监听器
  addEventListener(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return true;
  }

  // 移除事件监听器
  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index !== -1) {
        this.listeners[event].splice(index, 1);
        return true;
      }
    }
    return false;
  }

  // 生成客户端ID
  _generateClientId() {
    return 'client_' + Math.random().toString(36).substr(2, 9);
  }

  // 通知所有监听器
  _notifyListeners(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (e) {
          console.error('Error in event listener callback:', e);
        }
      });
    }
  }
}

// 创建单例
const api = new BatteryAPI();
export default api; 