<template>
  <nav class="top-bar-menu">
    <ul>
      <li 
        v-for="item in menuItems" 
        :key="item.id"
        :class="{ active: activeItem === item.id }"
        @click="selectItem(item.id)"
      >
        {{ item.name }}
      </li>
    </ul>
  </nav>
</template>

<script>
export default {
  name: 'TopBarMenu',
  props: {
    activeItem: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      menuItems: [
        { id: 'dashboard', name: '仿真主页' },
        { id: 'statistics', name: '充电统计' },
        { id: 'records', name: '记录管理' },
        { id: 'health', name: '健康分析' },
      ],
    };
  },
  methods: {
    selectItem(itemId) {
      this.$emit('item-selected', itemId);
    },
  },
};
</script>

<style scoped>
.top-bar-menu {
  background-color: #ffffff;
  padding: 0 2rem;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.top-bar-menu ul {
  list-style-type: none;
  margin: 0;
  padding: 0;
  display: flex;
  justify-content: center;
}

.top-bar-menu li {
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-weight: 500;
  color: #555;
  transition: all 0.3s ease;
  border-bottom: 3px solid transparent;
}

.top-bar-menu li:hover {
  color: #005A9E;
}

.top-bar-menu li.active {
  color: #005A9E;
  border-bottom: 3px solid #005A9E;
}
</style>