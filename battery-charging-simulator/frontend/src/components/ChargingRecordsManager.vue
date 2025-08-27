<template>
  <div class="records-manager">
    <h3 class="manager-title">充电记录管理</h3>
    
    <!-- 操作栏 -->
    <div class="actions-bar">
      <div class="search-filter">
        <input type="text" v-model="searchParams.query" placeholder="搜索ID或关键字..." @keyup.enter="searchRecords">
        <button @click="searchRecords" class="btn search-btn">搜索</button>
        <button @click="resetSearch" class="btn reset-btn">重置</button>
      </div>
      <div class="batch-actions">
        <button @click="deleteSelectedRecords" :disabled="selectedRecords.length === 0" class="btn delete-selected-btn">删除选中</button>
        <button @click="confirmDeleteAll" class="btn delete-all-btn">删除全部</button>
      </div>
    </div>

    <!-- 加载与错误提示 -->
    <div v-if="loading" class="loading-state">正在加载记录...</div>
    <div v-if="error" class="error-state">{{ error }}</div>

    <!-- 记录表格 -->
    <div v-if="!loading && !error" class="records-table-container">
      <table class="records-table">
        <thead>
          <tr>
            <th><input type="checkbox" @change="selectAllRecords" v-model="isAllSelected"></th>
            <th>ID</th>
            <th>开始时间</th>
            <th>结束时间</th>
            <th>充电时长</th>
            <th>初始/结束 SOC</th>
            <th>初始/结束温度</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td><input type="checkbox" v-model="selectedRecords" :value="record.id"></td>
            <td>{{ record.id }}</td>
            <td>{{ formatDateTime(record.start_time) }}</td>
            <td>{{ record.end_time ? formatDateTime(record.end_time) : 'N/A' }}</td>
            <td>{{ formatDuration(record.duration_seconds) }}</td>
            <td>{{ record.initial_soc.toFixed(2) }}% / {{ record.final_soc ? record.final_soc.toFixed(2) + '%' : 'N/A' }}</td>
            <td>{{ record.initial_temperature.toFixed(2) }}°C / {{ record.final_temperature ? record.final_temperature.toFixed(2) + '°C' : 'N/A' }}</td>
            <td>
              <button @click="viewRecordDetails(record)" class="btn view-btn">详情</button>
              <button @click="confirmDeleteRecord(record.id)" class="btn delete-btn">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
       <div v-if="records.length === 0" class="no-records">
        没有找到充电记录。
      </div>
    </div>
    
    <!-- 分页 -->
    <div class="pagination">
      <button @click="changePage(pagination.currentPage - 1)" :disabled="pagination.currentPage <= 1">上一页</button>
      <span>第 {{ pagination.currentPage }} / {{ pagination.totalPages }} 页</span>
      <button @click="changePage(pagination.currentPage + 1)" :disabled="pagination.currentPage >= pagination.totalPages">下一页</button>
    </div>

    <!-- 记录详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-content">
        <h4 class="modal-title">充电记录 #{{ selectedRecordDetails.id }} 详情</h4>
        <pre class="modal-body">{{ JSON.stringify(selectedRecordDetails, null, 2) }}</pre>
        <button @click="closeDetailModal" class="btn close-modal-btn">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'ChargingRecordsManager',
  data() {
    return {
      loading: false,
      error: null,
      records: [],
      selectedRecords: [],
      searchParams: {
        query: '',
        limit: 10,
        offset: 0,
      },
      pagination: {
        currentPage: 1,
        totalPages: 1,
        totalRecords: 0,
      },
      showDetailModal: false,
      selectedRecordDetails: null,
    };
  },
  computed: {
    isAllSelected() {
      return this.records.length > 0 && this.selectedRecords.length === this.records.length;
    }
  },
  created() {
    // 不要立即调用 fetchRecords，而是先检查连接状态
    if (api.isConnected) {
      this.fetchRecords();
    } else {
      // 如果未连接，先监听连接事件
      api.addEventListener('connect', this.handleConnect);
    }
    
    // 监听全局记录更新（例如，由另一个组件触发的删除）
    api.addEventListener('charging_records', this.handleGlobalRecordsUpdate);
    // 监听此组件发起的搜索操作的结果
    api.addEventListener('chargingRecordsSearchResult', this.handleSearchResult);
  },
  beforeDestroy() {
    api.removeEventListener('connect', this.handleConnect);
    api.removeEventListener('charging_records', this.handleGlobalRecordsUpdate);
    api.removeEventListener('chargingRecordsSearchResult', this.handleSearchResult);
  },
  methods: {
    handleConnect() {
      // 连接建立后获取数据
      console.log("WebSocket已连接，开始获取充电记录");
      this.fetchRecords();
      // 只需要监听一次连接事件
      api.removeEventListener('connect', this.handleConnect);
    },
    fetchRecords() {
      // 添加连接检查
      if (!api.isConnected) {
        console.error("WebSocket未连接，无法获取充电记录");
        this.error = "服务器连接失败，请刷新页面重试";
        return;
      }
      
      this.loading = true;
      this.error = null;
      const params = { 
        limit: this.searchParams.limit,
        offset: (this.pagination.currentPage - 1) * this.searchParams.limit,
        // 添加搜索查询参数
        query: this.searchParams.query || null 
      };
      api.searchChargingRecords(params).catch(err => {
        this.error = '发送搜索请求失败。';
        console.error(err);
        this.loading = false;
      });
    },
    handleSearchResult(response) {
      if (response && response.records) {
        this.records = response.records;
        this.pagination.totalRecords = response.total_count;
        this.pagination.totalPages = Math.ceil(response.total_count / this.searchParams.limit);
      } else {
        this.error = '收到了无效的搜索结果。';
        this.records = [];
      }
      this.loading = false;
    },
    handleGlobalRecordsUpdate(newRecords) {
        // 当记录被其他方式更改时，重新加载当前页数据
        console.log("收到全局记录更新，重新加载数据...");
        this.fetchRecords();
    },
    searchRecords() {
      this.pagination.currentPage = 1;
      this.fetchRecords();
    },
    resetSearch() {
        this.searchParams.query = '';
        this.searchRecords();
    },
    changePage(page) {
        if(page > 0 && page <= this.pagination.totalPages) {
            this.pagination.currentPage = page;
            this.fetchRecords();
        }
    },
    confirmDeleteRecord(id) {
        if(window.confirm(`确定要删除ID为 ${id} 的充电记录吗？`)) {
            this.deleteRecord(id);
        }
    },
    async deleteRecord(id) {
        try {
            await api.deleteChargingRecord(id);
            this.$emit('show-notification', { type: 'success', message: `记录 ${id} 已删除` });
            // fetchRecords将在事件监听器中被调用
        } catch(err) {
            this.$emit('show-notification', { type: 'error', message: `删除记录 ${id} 失败` });
        }
    },
    confirmDeleteAll() {
        if(window.confirm('确定要删除所有充电记录吗？此操作不可撤销。')) {
            this.deleteAllRecords();
        }
    },
    async deleteAllRecords() {
        try {
            await api.deleteAllChargingRecords();
            this.$emit('show-notification', { type: 'success', message: '所有记录已删除' });
            this.selectedRecords = [];
        } catch(err) {
            this.$emit('show-notification', { type: 'error', message: '删除所有记录失败' });
        }
    },
    deleteSelectedRecords() {
        if(this.selectedRecords.length === 0) return;
        if(window.confirm(`确定要删除选中的 ${this.selectedRecords.length} 条记录吗？`)) {
            this.batchDelete(this.selectedRecords);
        }
    },
    async batchDelete(ids) {
        try {
            await api.deleteChargingRecords(ids);
            this.$emit('show-notification', { type: 'success', message: `${ids.length} 条记录已删除` });
            this.selectedRecords = [];
        } catch(err) {
            this.$emit('show-notification', { type: 'error', message: '删除选中记录失败' });
        }
    },
    selectAllRecords(event) {
        if (event.target.checked) {
            this.selectedRecords = this.records.map(r => r.id);
        } else {
            this.selectedRecords = [];
        }
    },
    viewRecordDetails(record) {
      this.selectedRecordDetails = record;
      this.showDetailModal = true;
    },
    closeDetailModal() {
      this.showDetailModal = false;
      this.selectedRecordDetails = null;
    },
    formatDateTime(isoString) {
      if (!isoString) return 'N/A';
      return new Date(isoString).toLocaleString();
    },
    
    formatDuration(seconds) {
      if (!seconds && seconds !== 0) return 'N/A';
      
      // 将秒数转换为更友好的格式 (时:分:秒)
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = seconds % 60;
      
      if (hours > 0) {
        return `${hours}时${minutes}分${remainingSeconds}秒`;
      } else if (minutes > 0) {
        return `${minutes}分${remainingSeconds}秒`;
      } else {
        return `${remainingSeconds}秒`;
      }
    }
  }
};
</script>

<style scoped>
.records-manager {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.manager-title {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: #333;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-filter {
  display: flex;
  gap: 0.5rem;
}

.search-filter input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  font-weight: bold;
  transition: background-color 0.2s;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.search-btn { background-color: #3498db; }
.search-btn:hover { background-color: #2980b9; }
.reset-btn { background-color: #95a5a6; }
.reset-btn:hover { background-color: #7f8c8d; }
.delete-selected-btn { background-color: #e74c3c; }
.delete-selected-btn:hover { background-color: #c0392b; }
.delete-all-btn { background-color: #c0392b; }
.delete-all-btn:hover { background-color: #a53125; }

.loading-state, .error-state, .no-records {
  text-align: center;
  padding: 2rem;
  color: #666;
}
.error-state { color: #e74c3c; }

.records-table-container {
    overflow-x: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

.records-table th, .records-table td {
  border: 1px solid #ddd;
  padding: 0.75rem;
  text-align: left;
  font-size: 0.9em;
}

.records-table th {
  background-color: #f2f2f2;
}

.records-table tbody tr:nth-child(even) {
  background-color: #f9f9f9;
}

.records-table tbody tr:hover {
  background-color: #f1f1f1;
}

.records-table .btn {
  margin-right: 0.5rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.8em;
}
.view-btn { background-color: #2ecc71; }
.delete-btn { background-color: #e74c3c; }

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}
.pagination button {
    background-color: #3498db;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  width: 80%;
  max-width: 700px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}
.modal-title {
    margin-top: 0;
}
.modal-body {
    background-color: #f3f3f3;
    padding: 1rem;
    border-radius: 4px;
    max-height: 60vh;
    overflow-y: auto;
}

.close-modal-btn {
    background-color: #95a5a6;
    margin-top: 1rem;
    float: right;
}
</style> 