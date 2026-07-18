<template>
  <div class="orders-page page-shell container">
    <section class="system-page-intro">
      <div class="system-page-intro-copy">
        <span class="system-page-kicker">交易与物流</span>
        <h1>茶品订单</h1>
        <p>统一查看茶品购买记录、支付状态与物流进度，并可继续发起售后咨询。</p>
      </div>
      <span class="system-page-metric">共 {{ total }} 笔订单</span>
    </section>
    <section class="filter-strip section-card">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-chip"
        :class="{ active: activeTab === tab.value }"
        type="button"
        @click="setTab(tab.value)"
      >
        {{ tab.label }}
      </button>
    </section>

    <section v-if="loading" class="state-card section-card">
      <div class="loader"></div>
      <strong>正在读取订单列表</strong>
      <p>正在同步订单状态、茶品信息与支付金额。</p>
    </section>

    <section v-else-if="orders.length === 0" class="state-card section-card">
      <div class="empty-illustration">
        <el-icon><Document /></el-icon>
      </div>
      <strong>当前筛选下没有订单</strong>
      <p>可以切换订单状态，或先去茶品商城挑选合适的茶叶。</p>
      <button class="accent-button" type="button" @click="router.push('/products')">选购茶品</button>
    </section>

    <section v-else class="orders-list">
      <article v-for="order in orders" :key="order.id" class="order-card section-card">
        <div class="order-head">
          <div>
            <span class="order-no">{{ order.order_no }}</span>
            <h2>{{ getStatusText(order.status) }}</h2>
            <p>创建于 {{ formatDateTime(order.created_at) }}</p>
          </div>
          <span class="status-pill" :class="order.status">{{ getStatusText(order.status) }}</span>
        </div>

        <div class="order-items">
          <div v-for="item in order.items || []" :key="item.id" class="order-item">
            <img
              :src="resolveProductImage(item.product_cover, item.product_title)"
              :alt="item.product_title"
              @error="(event) => handleImageFallback(event, item.product_title)"
            />
            <div class="item-copy">
              <strong>{{ item.product_title }}</strong>
              <span>数量 {{ item.quantity }}</span>
            </div>
            <strong class="item-price">{{ formatCents(item.subtotal || item.price * item.quantity) }}</strong>
          </div>
        </div>

        <div class="order-foot">
          <div class="order-total">
            <span>订单总计</span>
            <strong>{{ formatCents(order.total_amount) }}</strong>
          </div>

          <div class="order-actions">
            <button v-if="order.status === 'pending'" class="accent-button compact-button" type="button" @click="handlePay(order.id)">
              立即支付
            </button>
            <button v-if="order.status === 'pending'" class="ghost-button compact-button" type="button" @click="handleCancel(order.id)">
              取消订单
            </button>
            <button
              v-if="order.status === 'delivered'"
              class="accent-button compact-button"
              type="button"
              @click="handleComplete(order.id)"
            >
              确认收货
            </button>
          </div>
        </div>
      </article>
    </section>

    <section v-if="total > pageSize" class="pagination-card section-card">
      <button class="ghost-button" type="button" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">
        上一页
      </button>

      <div class="page-indicator">
        <strong>{{ currentPage }}</strong>
        <span>共 {{ Math.ceil(total / pageSize) }} 页</span>
      </div>

      <button class="accent-button" type="button" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="changePage(currentPage + 1)">
        下一页
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const router = useRouter()
const orderStore = useOrderStore()

const tabs = [
  { label: '全部', value: 'all' },
  { label: '待支付', value: 'pending' },
  { label: '已支付', value: 'paid' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' }
]

const activeTab = ref('all')
const loading = ref(false)
const orders = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

onMounted(() => {
  fetchOrders()
})

async function fetchOrders() {
  loading.value = true

  try {
    const status = activeTab.value === 'all' ? undefined : activeTab.value
    const result = await orderStore.fetchOrders({
      status,
      page: currentPage.value,
      page_size: pageSize.value
    })

    orders.value = result.items
    total.value = result.total
  } catch (error: any) {
    console.error('Failed to fetch orders', error)
    ElMessage.error(error.message || '获取订单列表失败')
  } finally {
    loading.value = false
  }
}

function setTab(tab: string) {
  activeTab.value = tab
  currentPage.value = 1
  fetchOrders()
}

function changePage(page: number) {
  currentPage.value = page
  fetchOrders()
}

async function handlePay(orderId: string) {
  try {
    await ElMessageBox.confirm('确认支付这笔订单吗？', '支付订单', {
      confirmButtonText: '确认支付',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const result = await orderStore.payOrder(orderId, 'alipay')
    ElMessage[result.success ? 'success' : 'error'](result.message || (result.success ? '支付成功' : '支付失败'))
    fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to pay order', error)
      ElMessage.error(error.message || '支付失败')
    }
  }
}

async function handleCancel(orderId: string) {
  try {
    await ElMessageBox.confirm('确认取消这笔订单吗？', '取消订单', {
      confirmButtonText: '确认取消',
      cancelButtonText: '返回',
      type: 'warning'
    })

    await orderStore.cancelOrder(orderId)
    ElMessage.success('订单已取消')
    fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to cancel order', error)
      ElMessage.error(error.message || '取消订单失败')
    }
  }
}

async function handleComplete(orderId: string) {
  try {
    await ElMessageBox.confirm('确认已经收到茶叶商品吗？', '确认收货', {
      confirmButtonText: '确认收货',
      cancelButtonText: '再看看',
      type: 'info'
    })

    await orderStore.confirmDelivery(orderId)
    ElMessage.success('订单已完成')
    fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to confirm delivery', error)
      ElMessage.error(error.message || '操作失败')
    }
  }
}

function formatCents(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format((value || 0) / 100)
}

function formatDateTime(value?: string) {
  if (!value) return '时间待补充'

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    delivered: '待确认收货',
    completed: '已完成',
    cancelled: '已取消',
    refunded: '已退款'
  }

  return texts[status] || status
}
</script>

<style scoped>
.orders-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
}

.orders-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 24px;
  background: white;
  border-radius: 20px;
  border: 1px solid var(--border);
}

.hero-copy {
  flex: 1;
  min-width: 0;
}

.hero-copy h1 {
  margin: 10px 0 8px;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  font-weight: 700;
  color: var(--text);
}

.hero-copy p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.6;
  font-size: 14px;
  max-width: 600px;
}

.hero-side {
  display: flex;
  gap: 12px;
  align-items: center;
}

.hero-stat {
  padding: 16px 20px;
  border-radius: 16px;
  background: white;
  border: 1px solid var(--border);
  flex: 1;
  min-width: 120px;
}

.hero-stat span {
  display: block;
  margin-bottom: 4px;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

.hero-stat strong {
  display: block;
  font-size: 24px;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--text);
}

.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px;
}

.tab-chip {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.tab-chip.active {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 16px 30px rgba(0, 113, 227, 0.16);
}

.state-card {
  min-height: 340px;
  padding: 40px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  text-align: center;
}

.loader {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 4px solid rgba(0, 113, 227, 0.12);
  border-top-color: var(--primary);
  animation: spin 0.9s linear infinite;
}

.empty-illustration {
  width: 82px;
  height: 82px;
  border-radius: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 113, 227, 0.08);
  color: var(--primary);
}

.empty-illustration :deep(.el-icon) {
  font-size: 34px;
}

.state-card strong {
  font-size: 24px;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.state-card p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.7;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px 0;
}

.order-card {
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.order-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.order-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #F8FAFC;
  border-bottom: 1px solid var(--border);
}

.order-head > div {
  display: flex;
  align-items: center;
  gap: 16px;
}

.order-no {
  font-family: 'Monaco', monospace;
  font-size: 13px;
  color: var(--text-muted);
  background: white;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-light);
}

.order-head h2 {
  display: none; /* Hide the duplicate status text in header */
}

.order-head p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}

.status-pill {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.order-items {
  padding: 0;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.order-item:last-child {
  border-bottom: none;
}

.order-item img {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  object-fit: cover;
  border: 1px solid var(--border-light);
}

.item-copy {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-copy strong {
  font-size: 16px;
  color: var(--text);
  font-weight: 600;
}

.item-copy span {
  color: var(--text-muted);
  font-size: 13px;
}

.item-price {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.order-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: white;
  border-top: 1px solid var(--border);
}

.order-total {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.order-total span {
  font-size: 13px;
  color: var(--text-muted);
}

.order-total strong {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
}

.order-actions {
  display: flex;
  gap: 12px;
}

.compact-button {
  min-height: 36px;
  padding: 0 16px;
  font-size: 13px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.accent-button {
  background: var(--primary);
  color: white;
  border: none;
}

.accent-button:hover {
  background: var(--primary-dark);
}

.ghost-button {
  background: white;
  border: 1px solid var(--border);
  color: var(--text);
}

.ghost-button:hover {
  background: #F8FAFC;
  border-color: var(--text-muted);
}

.pagination-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px;
}

.page-indicator {
  min-width: 140px;
  text-align: center;
}

.page-indicator strong {
  display: block;
  font-size: 26px;
  line-height: 1;
}

.page-indicator span {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1100px) {
  .orders-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .orders-hero,
  .order-card {
    padding: 18px;
  }

  .order-head,
  .order-foot,
  .order-item,
  .pagination-card {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: flex-start;
  }

  .order-actions {
    width: 100%;
  }

  .order-actions .compact-button {
    width: 100%;
    justify-content: center;
  }

  .pagination-card {
    align-items: stretch;
  }
}
</style>
