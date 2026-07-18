<template>
  <div class="refunds-page page-shell">
    <section class="system-page-intro">
      <div class="system-page-intro-copy">
        <span class="system-page-kicker">售后服务中心</span>
        <h1>退款与售后</h1>
        <p>查询茶品退款、退货与换货申请，集中跟踪审核结果、处理节点和退款金额。</p>
      </div>
      <span class="system-page-metric">共 {{ total }} 条记录</span>
    </section>
    <section class="filter-strip section-card">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-chip"
        :class="{ active: activeTab === tab.value }"
        type="button"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </button>
    </section>

    <section v-if="loading" class="state-card section-card">
      <div class="loader"></div>
      <strong>正在读取售后记录</strong>
      <p>正在同步售后类型、处理状态、退款金额与审核时间。</p>
    </section>

    <section v-else-if="filteredRefunds.length === 0" class="state-card section-card">
      <div class="empty-illustration">
        <el-icon><Money /></el-icon>
      </div>
      <strong>当前筛选下没有售后记录</strong>
      <p>可切换处理状态查看记录，或前往智能客服咨询售后流程。</p>
    </section>

    <section v-else class="refund-list">
      <article v-for="refund in filteredRefunds" :key="refund.id" class="refund-card section-card">
        <div class="refund-head">
          <div>
            <span class="refund-no">{{ refund.refund_no }}</span>
            <h2>{{ getTypeText(refund.refund_type) }}</h2>
            <p>关联订单 {{ refund.order_no }}</p>
          </div>
          <span class="status-pill" :class="refund.status">{{ getStatusText(refund.status) }}</span>
        </div>

        <div class="refund-grid">
          <div class="info-card">
            <span>退款金额</span>
            <strong>{{ formatCents(refund.refund_amount) }}</strong>
            <p>{{ refund.reason }}</p>
          </div>
          <div class="info-card">
            <span>申请时间</span>
            <strong>{{ formatTime(refund.created_at) }}</strong>
            <p>{{ refund.reviewed_at ? `审核于 ${formatTime(refund.reviewed_at)}` : '等待审核中' }}</p>
          </div>
          <div class="info-card">
            <span>审核备注</span>
            <strong>{{ refund.review_note || '暂无备注' }}</strong>
            <p>{{ refund.description || '未填写补充说明' }}</p>
          </div>
        </div>

        <div v-if="refund.evidence_images?.length" class="evidence-strip">
          <el-image
            v-for="(img, index) in refund.evidence_images"
            :key="index"
            :src="img"
            :preview-src-list="refund.evidence_images"
            fit="cover"
            class="evidence-image"
          />
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Money } from '@element-plus/icons-vue'
import { apiClient } from '@/api/client'

const tabs = [
  { label: '全部', value: 'all' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' }
]

const activeTab = ref('all')
const loading = ref(false)
const refunds = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const processingStatuses = ['pending', 'approved', 'returning', 'refunding']
const finishedStatuses = ['completed', 'rejected', 'cancelled']

const filteredRefunds = computed(() => {
  if (activeTab.value === 'processing') {
    return refunds.value.filter(refund => processingStatuses.includes(refund.status))
  }

  if (activeTab.value === 'completed') {
    return refunds.value.filter(refund => finishedStatuses.includes(refund.status))
  }

  return refunds.value
})

onMounted(() => {
  fetchRefunds()
})

async function fetchRefunds() {
  loading.value = true

  try {
    const response: any = await apiClient.get('/refunds/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })

    refunds.value = response.items || []
    total.value = response.total || 0
  } catch (error) {
    console.error('Failed to fetch refunds', error)
    ElMessage.error('获取售后列表失败')
  } finally {
    loading.value = false
  }
}

function changePage(page: number) {
  currentPage.value = page
  fetchRefunds()
}

function getStatusText(status: string) {
  const textMap: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    returning: '退货中',
    refunding: '退款中',
    completed: '已完成',
    cancelled: '已取消'
  }

  return textMap[status] || status
}

function getTypeText(type: string) {
  const textMap: Record<string, string> = {
    refund_only: '仅退款',
    return_refund: '退货退款',
    exchange: '换货'
  }

  return textMap[type] || type
}

function formatTime(time: string) {
  if (!time) return '待补充'

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(time))
}

function formatCents(value = 0) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format(value / 100)
}
</script>

<style scoped>
.refunds-page {
  gap: 18px;
}

.refunds-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) 240px;
  gap: 18px;
  padding: 24px;
}

.hero-copy h1 {
  margin: 14px 0 12px;
  font-size: clamp(34px, 4vw, 56px);
  line-height: 0.98;
  letter-spacing: -0.05em;
}

.hero-copy p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.8;
}

.hero-side {
  display: grid;
  gap: 12px;
}

.hero-stat {
  padding: 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--border);
}

.hero-stat span {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.hero-stat strong {
  font-size: 30px;
  line-height: 1;
  letter-spacing: -0.05em;
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
  font-weight: 600;
}

.tab-chip.active {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  border-color: transparent;
  color: #fff;
}

.state-card {
  min-height: 320px;
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

.refund-list {
  display: grid;
  gap: 16px;
}

.refund-card {
  padding: 20px;
}

.refund-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.refund-no {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.refund-head h2 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.refund-head p {
  margin: 0;
  color: var(--text-muted);
}

.status-pill {
  padding: 10px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.status-pill.pending {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.status-pill.approved,
.status-pill.returning,
.status-pill.refunding {
  background: rgba(0, 113, 227, 0.12);
  color: var(--primary);
}

.status-pill.completed {
  background: rgba(22, 163, 74, 0.12);
  color: var(--success);
}

.status-pill.rejected,
.status-pill.cancelled {
  background: rgba(239, 68, 68, 0.12);
  color: var(--danger);
}

.refund-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.info-card {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
}

.info-card span {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.info-card strong {
  display: block;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}

.info-card p {
  margin: 10px 0 0;
  color: var(--text-muted);
  line-height: 1.7;
}

.evidence-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.evidence-image {
  width: 112px;
  height: 112px;
  border-radius: 20px;
  overflow: hidden;
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
}

.page-indicator span {
  font-size: 13px;
  color: var(--text-muted);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 980px) {
  .refunds-hero,
  .refund-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .refunds-hero,
  .refund-card,
  .pagination-card {
    padding: 18px;
  }

  .refund-head,
  .pagination-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
