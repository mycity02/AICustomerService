<template>
  <el-dialog
    v-model="visible"
    title="选择订单"
    width="600px"
    :close-on-click-modal="false"
  >
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载订单中...</span>
    </div>

    <div v-else-if="orders.length === 0" class="empty-container">
      <el-empty description="暂无订单" />
    </div>

    <div v-else class="order-list">
      <div
        v-for="order in orders"
        :key="order.id"
        class="order-item"
        :class="{ selected: selectedOrder?.id === order.id }"
        @click="selectOrder(order)"
      >
        <div class="order-header">
          <span class="order-no">{{ order.order_no }}</span>
          <span class="order-status" :class="'status-' + order.status">
            {{ getStatusText(order.status) }}
          </span>
        </div>
        <div class="order-body">
          <div class="product-info">
            <span class="product-name">{{ getProductName(order) }}</span>
            <span v-if="order.items && order.items.length > 1" class="item-count">
              等 {{ order.items.length }} 件茶品
            </span>
          </div>
          <div class="order-meta">
            <span class="order-amount">¥{{ (order.total_amount / 100).toFixed(2) }}</span>
            <span class="order-time">{{ formatTime(order.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!selectedOrder" @click="confirmSelection">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'

interface Order {
  id: string
  order_no: string
  status: string
  total_amount: number
  created_at: string
  items: any[]
}

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', order: Order): void
}>()

const visible = ref(false)
const loading = ref(false)
const orders = ref<Order[]>([])
const selectedOrder = ref<Order | null>(null)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    loadOrders()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (!val) {
    selectedOrder.value = null
  }
})

const loadOrders = async () => {
  loading.value = true
  try {
    // 直接使用fetch API，避免apiClient初始化问题
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/orders?page=1&page_size=20', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('订单数据:', data)
    console.log('订单items:', data.items)
    if (data.items && data.items.length > 0) {
      console.log('第一个订单:', data.items[0])
    }
    orders.value = data.items || []
  } catch (error) {
    console.error('加载订单失败:', error)
    orders.value = []
  } finally {
    loading.value = false
  }
}

const selectOrder = (order: Order) => {
  selectedOrder.value = order
}

const confirmSelection = () => {
  if (selectedOrder.value) {
    emit('select', selectedOrder.value)
    visible.value = false
  }
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    shipped: '已发货',
    delivered: '已送达',
    completed: '已完成',
    cancelled: '已取消'
  }
  return statusMap[status] || '未知'
}

const getProductName = (order: Order) => {
  // 添加详细的安全检查和日志
  console.log('getProductName 被调用, order:', order)
  console.log('order.items:', order.items)
  
  if (!order.items) {
    console.warn('order.items 不存在')
    return '茶品'
  }
  
  if (!Array.isArray(order.items)) {
    console.warn('order.items 不是数组:', typeof order.items)
    return '茶品'
  }
  
  if (order.items.length === 0) {
    console.warn('order.items 是空数组')
    return '茶品'
  }
  
  const firstItem = order.items[0]
  console.log('第一个商品:', firstItem)
  
  if (!firstItem) {
    console.warn('第一个商品不存在')
    return '茶品'
  }
  
  return firstItem.product_title || '茶品'
}

const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: var(--muted);
}

.loading-container .el-icon {
  font-size: 32px;
}

.empty-container {
  padding: 20px;
}

.order-list {
  max-height: 500px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-item {
  padding: 16px;
  background: var(--surface-2);
  border: 2px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.order-item:hover {
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.4);
  box-shadow: 0 4px 12px rgba(2, 6, 23, 0.3);
}

.order-item.selected {
  background: rgba(56, 189, 248, 0.15);
  border-color: rgba(56, 189, 248, 0.6);
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.4);
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.order-no {
  font-size: 13px;
  color: var(--muted);
  font-family: monospace;
}

.order-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.order-status.status-pending {
  background: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.order-status.status-paid {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.order-status.status-shipped {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.order-status.status-delivered,
.order-status.status-completed {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
}

.order-status.status-cancelled {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.order-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.product-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.item-count {
  font-size: 12px;
  color: var(--muted);
  padding: 2px 8px;
  background: rgba(148, 163, 184, 0.15);
  border-radius: 8px;
}

.order-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-amount {
  font-size: 16px;
  font-weight: 700;
  color: #ef4444;
}

.order-time {
  font-size: 12px;
  color: var(--muted);
}
</style>
