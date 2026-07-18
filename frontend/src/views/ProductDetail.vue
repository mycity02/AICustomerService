<template>
  <div v-if="loading && !currentProduct" class="detail-loading section-card">
    <div class="loader"></div>
    <strong>正在载入茶品详情</strong>
    <p>正在同步茶品介绍、产地风味、价格与库存信息。</p>
  </div>

  <div v-else-if="currentProduct" class="detail-page page-shell">
    <section class="detail-hero section-card">
      <div class="media-column">
        <div class="main-media">
          <img
            :src="selectedPreview"
            :alt="currentProduct.title"
            @error="(event) => handleImageFallback(event, currentProduct?.title)"
          />
        </div>

        <div v-if="galleryImages.length > 1" class="thumb-strip">
          <button
            v-for="image in galleryImages"
            :key="image"
            class="thumb-button"
            :class="{ active: selectedPreview === image }"
            type="button"
            @click="selectedPreview = image"
          >
            <img :src="image" :alt="currentProduct.title" @error="(event) => handleImageFallback(event, currentProduct?.title)" />
          </button>
        </div>
      </div>

      <div class="summary-column">
        <span class="eyebrow">{{ currentProduct.category?.name || '当季精选茶品' }}</span>
        <h1>{{ currentProduct.title }}</h1>
        <p>{{ currentProduct.description }}</p>

        <div class="summary-badges">
          <span class="summary-badge">{{ difficultyText }}</span>
          <span class="summary-badge">{{ currentProduct.tech_stack?.slice(0, 2).join(' · ') || '产地与风味标签' }}</span>
          <span class="summary-badge">已售 {{ currentProduct.sales_count }}</span>
        </div>

        <div class="price-panel">
          <div>
            <strong>{{ formatPrice(currentProduct.price) }}</strong>
            <span v-if="currentProduct.original_price">{{ formatPrice(currentProduct.original_price) }}</span>
          </div>
          <small>评分 {{ currentProduct.rating.toFixed(1) }} · {{ currentProduct.review_count }} 条评价</small>
        </div>

        <div class="action-row">
          <button class="accent-button" type="button" @click="handleBuyNow">立即购买</button>
          <button class="ghost-button" type="button" @click="handleAddToCart">加入购物车</button>
          <button class="glass-button" type="button" @click="router.push('/chat')">咨询 AI 选茶顾问</button>
        </div>

        <div class="meta-grid">
          <article class="meta-card">
            <span>风味标签</span>
            <strong>{{ currentProduct.tech_stack?.length || 0 }} 项</strong>
            <p>{{ currentProduct.tech_stack?.join(' · ') || '等待补充' }}</p>
          </article>
          <article class="meta-card">
            <span>发布时间</span>
            <strong>{{ formatDate(currentProduct.created_at) }}</strong>
            <p>支持先咨询口感与冲泡方式，再安心下单。</p>
          </article>
          <article class="meta-card">
            <span>茶商信息</span>
            <strong>{{ currentProduct.seller?.username || '平台精选' }}</strong>
            <p>茶品信息、包装说明与售后保障清晰可查。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="detail-grid">
      <article class="story-card section-card">
        <span class="eyebrow">茶品介绍</span>
        <h2>茶品特点</h2>
        <p>{{ currentProduct.description }}</p>
      </article>

      <article class="story-card section-card">
        <span class="eyebrow">风味标签</span>
        <h2>产地、香型与工艺</h2>
        <div class="stack-list">
          <span v-for="tech in currentProduct.tech_stack" :key="tech">{{ tech }}</span>
          <span v-if="!currentProduct.tech_stack?.length">暂无风味标签</span>
        </div>
      </article>

      <article class="story-card section-card">
        <span class="eyebrow">品质保障</span>
        <h2>包装与配送服务</h2>
        <ul class="delivery-list">
          <li>独立密封包装，减少受潮与串味</li>
          <li>支持订单物流查询与签收提醒</li>
          <li>已售：{{ currentProduct.sales_count }} 件</li>
          <li>状态：{{ getProductStatusText(currentProduct.status) }}</li>
        </ul>
      </article>
    </section>

    <section class="detail-tabs section-card">
      <div class="tab-switcher">
        <button class="tab-button" :class="{ active: activeTab === 'description' }" type="button" @click="activeTab = 'description'">
          茶品介绍
        </button>
        <button class="tab-button" :class="{ active: activeTab === 'files' }" type="button" @click="activeTab = 'files'">
          包装配送
        </button>
        <button class="tab-button" :class="{ active: activeTab === 'reviews' }" type="button" @click="activeTab = 'reviews'">
          评价预览
        </button>
      </div>

      <div v-if="activeTab === 'description'" class="tab-panel">
        <h3>茶品详情</h3>
        <p>{{ currentProduct.description }}</p>
      </div>

      <div v-else-if="activeTab === 'files'" class="tab-panel">
        <h3>包装与配送说明</h3>
        <div class="file-grid">
          <article class="file-card">
            <strong>密封防潮</strong>
            <span>食品级内袋与外盒包装</span>
            <small>开封后请避光、密封保存</small>
          </article>
          <article class="file-card">
            <strong>订单配送</strong>
            <span>付款后按订单顺序安排发货</span>
            <small>可在订单中心查询物流</small>
          </article>
          <article class="file-card">
            <strong>售后保障</strong>
            <span>支持破损、错发和质量问题反馈</span>
            <small>请保留商品与包装凭证</small>
          </article>
        </div>
      </div>

      <div v-else class="tab-panel">
        <h3>茶友评价概览</h3>
        <div class="review-overview">
          <strong>{{ currentProduct.rating.toFixed(1) }}</strong>
          <span>综合评分</span>
        </div>
        <p>当前共 {{ currentProduct.review_count }} 条评价。可结合茶友反馈了解香型、滋味与耐泡度。</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { browseAPI } from '@/api/browse'
import { useCartStore } from '@/stores/cart'
import { useProductStore } from '@/stores/product'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()
const cartStore = useCartStore()
const { currentProduct, loading } = storeToRefs(productStore)

const activeTab = ref<'description' | 'files' | 'reviews'>('description')
const selectedPreview = ref('')
const enterTime = ref(0)

const difficultyText = computed(() => {
  const map: Record<string, string> = {
    easy: '清新鲜爽',
    medium: '醇香回甘',
    hard: '浓醇耐泡'
  }

  return map[currentProduct.value?.difficulty || ''] || currentProduct.value?.difficulty || '经典茶品'
})

const galleryImages = computed(() => {
  if (!currentProduct.value) return []

  const rawImages = [
    resolveProductImage(currentProduct.value.cover_image, currentProduct.value.title),
    ...(currentProduct.value.images?.map(image => image.url).filter(Boolean) || [])
  ]

  return Array.from(new Set(rawImages))
})

watch(
  () => route.params.id,
  async (newId, oldId) => {
    if (oldId) {
      await recordBrowseDuration()
    }

    if (typeof newId === 'string') {
      await loadProduct(newId)
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  recordBrowseDuration()
})

async function loadProduct(productId: string) {
  activeTab.value = 'description'
  await productStore.fetchProductDetail(productId)
  selectedPreview.value = galleryImages.value[0] || resolveProductImage(undefined, currentProduct.value?.title)
  enterTime.value = Date.now()

  try {
    await browseAPI.recordBrowse(productId, 0)
  } catch (error) {
    console.error('Failed to record product visit', error)
  }
}

async function recordBrowseDuration() {
  if (!currentProduct.value || enterTime.value <= 0) return

  const duration = Math.max(0, Math.floor((Date.now() - enterTime.value) / 1000))
  enterTime.value = 0

  try {
    await browseAPI.recordBrowse(currentProduct.value.id, duration)
  } catch (error) {
    console.error('Failed to update browse duration', error)
  }
}

function formatPrice(value?: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format(value ?? 0)
}

function getProductStatusText(status?: string) {
  const map: Record<string, string> = {
    draft: '待发布',
    published: '可购买',
    offline: '已下架',
    sold_out: '已售罄'
  }

  return map[status || ''] || '状态待确认'
}

function formatDate(value?: string) {
  if (!value) return '待补充'

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(new Date(value))
}

function formatBytes(size = 0) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

async function handleAddToCart() {
  if (!currentProduct.value) return

  try {
    await cartStore.addToCart(currentProduct.value.id)
    ElMessage.success('已加入购物车')
  } catch (error) {
    console.error('Failed to add current product to cart', error)
    ElMessage.error('加入购物车失败，请稍后重试')
  }
}

async function handleBuyNow() {
  await handleAddToCart()
  router.push('/cart')
}
</script>

<style scoped>
.detail-page {
  gap: 20px;
}

.detail-loading {
  min-height: 420px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  text-align: center;
}

.loader {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 4px solid rgba(0, 113, 227, 0.12);
  border-top-color: var(--primary);
  animation: spin 0.9s linear infinite;
}

.detail-loading strong {
  font-size: 24px;
}

.detail-loading p {
  margin: 0;
  color: var(--text-muted);
}

.detail-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.88fr);
  gap: 22px;
  padding: 24px;
}

.media-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.main-media {
  overflow: hidden;
  border-radius: 30px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(0, 113, 227, 0.1));
  aspect-ratio: 1.18;
}

.main-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(88px, 1fr));
  gap: 12px;
}

.thumb-button {
  overflow: hidden;
  padding: 0;
  border-radius: 20px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.84);
  aspect-ratio: 1;
}

.thumb-button.active {
  border-color: rgba(0, 113, 227, 0.28);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.08);
}

.thumb-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.summary-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  justify-content: center;
}

.summary-column h1 {
  margin: 0;
  font-size: clamp(36px, 4.2vw, 62px);
  line-height: 0.98;
  letter-spacing: -0.06em;
}

.summary-column p {
  margin: 0;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 1.8;
}

.summary-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.summary-badge {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.price-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px 20px;
  border-radius: 26px;
  background: linear-gradient(135deg, rgba(10, 18, 34, 0.94), rgba(0, 113, 227, 0.88));
  color: #f8fbff;
  box-shadow: var(--shadow);
}

.price-panel strong {
  font-size: 44px;
  line-height: 1;
  letter-spacing: -0.06em;
}

.price-panel span {
  margin-left: 10px;
  color: rgba(248, 251, 255, 0.66);
  font-size: 16px;
  text-decoration: line-through;
}

.price-panel small {
  color: rgba(248, 251, 255, 0.78);
  font-size: 13px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.action-row .accent-button,
.action-row .ghost-button,
.action-row .glass-button {
  flex: 1;
  justify-content: center;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.meta-card {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
}

.meta-card span {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.meta-card strong {
  display: block;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}

.meta-card p {
  margin: 8px 0 0;
  font-size: 13px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.story-card {
  padding: 22px;
}

.story-card h2 {
  margin: 14px 0 10px;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.story-card p {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.8;
}

.stack-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stack-list span {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(0, 113, 227, 0.08);
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
}

.delivery-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-muted);
  line-height: 1.9;
}

.detail-tabs {
  padding: 24px;
}

.tab-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

.tab-button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.74);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.tab-button.active {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 16px 30px rgba(0, 113, 227, 0.16);
}

.tab-panel h3 {
  margin: 0 0 10px;
  font-size: 24px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.tab-panel p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.8;
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.file-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
}

.file-card strong {
  font-size: 16px;
}

.file-card span,
.file-card small {
  color: var(--text-muted);
}

.review-overview {
  margin-bottom: 12px;
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(0, 113, 227, 0.08);
}

.review-overview strong {
  font-size: 34px;
  line-height: 1;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .detail-hero,
  .detail-grid,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .detail-hero,
  .detail-tabs {
    padding: 18px;
  }

  .summary-column h1 {
    font-size: 38px;
  }

  .action-row {
    flex-direction: column;
  }
}
</style>
