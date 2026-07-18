<template>
  <div class="favorites-page page-shell">
    <section class="system-page-intro">
      <div class="system-page-intro-copy">
        <span class="system-page-kicker">我的珍藏</span>
        <h1>茶品收藏</h1>
        <p>集中保存感兴趣的茶品，方便后续比较产地、香型、口感与价格。</p>
      </div>
      <span class="system-page-metric">共 {{ total }} 个收藏</span>
    </section>
    <section v-if="loading" class="state-card section-card">
      <div class="loader"></div>
      <strong>正在读取收藏列表</strong>
      <p>正在同步收藏茶品及其最新价格。</p>
    </section>

    <section v-else-if="favorites.length === 0" class="state-card section-card">
      <div class="empty-illustration">
        <el-icon><Star /></el-icon>
      </div>
      <strong>暂时没有收藏茶品</strong>
      <p>前往茶品商城逛逛，把感兴趣的好茶收藏到这里。</p>
      <button class="accent-button" type="button" @click="router.push('/products')">选购茶品</button>
    </section>

    <section v-else class="favorites-grid">
      <article v-for="item in favorites" :key="item.favorite_id" class="favorite-card section-card">
        <div class="card-media" @click="goToDetail(item.product_id)">
          <img
            :src="resolveProductImage(item.cover_image, item.title)"
            :alt="item.title"
            @error="(event) => handleImageFallback(event, item.title)"
          />
        </div>

        <div class="card-body">
          <div class="card-topline">
            <span class="eyebrow">已收藏茶品</span>
            <strong>{{ formatPrice(item.price) }}</strong>
          </div>

          <h2 @click="goToDetail(item.product_id)">{{ item.title }}</h2>
          <p>{{ getPreview(item.description) }}</p>

          <div class="card-actions">
            <button class="accent-button compact-button" type="button" @click="addToCart(item.product_id)">
              加入购物车
            </button>
            <button class="ghost-button compact-button" type="button" @click="removeFavorite(item.product_id)">
              取消收藏
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
import { Star } from '@element-plus/icons-vue'
import { apiClient } from '@/api/client'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const router = useRouter()

const loading = ref(false)
const favorites = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

onMounted(() => {
  fetchFavorites()
})

async function fetchFavorites() {
  loading.value = true

  try {
    const data: any = await apiClient.get('/favorites', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })

    favorites.value = data.items || []
    total.value = data.total || 0
  } catch (error: any) {
    console.error('Failed to fetch favorites', error)
    ElMessage.error(error.message || '获取收藏列表失败')
    favorites.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function changePage(page: number) {
  currentPage.value = page
  fetchFavorites()
}

function getPreview(text = '') {
  return text.length > 88 ? `${text.slice(0, 88)}...` : text || '可收藏后继续比较产地、香型、口感与价格。'
}

function formatPrice(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format(value || 0)
}

function goToDetail(productId: string) {
  router.push(`/products/${productId}`)
}

async function addToCart(productId: string) {
  try {
    await apiClient.post('/cart', { product_id: productId })
    ElMessage.success('已加入购物车')
  } catch (error: any) {
    console.error('Failed to add favorite item to cart', error)
    ElMessage.error(error.message || '加入购物车失败')
  }
}

async function removeFavorite(productId: string) {
  try {
    await ElMessageBox.confirm('确认取消收藏这件茶品吗？', '取消收藏', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await apiClient.delete(`/favorites/${productId}`)
    ElMessage.success('已取消收藏')
    fetchFavorites()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to remove favorite', error)
      ElMessage.error(error.message || '取消收藏失败')
    }
  }
}
</script>

<style scoped>
.favorites-page {
  gap: 18px;
}

.favorites-hero {
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
  display: block;
  font-size: 30px;
  line-height: 1;
  letter-spacing: -0.05em;
}

.state-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 40px 24px;
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
}

.state-card p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.7;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.favorite-card {
  overflow: hidden;
}

.card-media {
  overflow: hidden;
  aspect-ratio: 1.18;
  cursor: pointer;
}

.card-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.32s ease;
}

.favorite-card:hover .card-media img {
  transform: scale(1.04);
}

.card-body {
  padding: 20px;
}

.card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-topline strong {
  font-size: 22px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.card-body h2 {
  margin: 16px 0 10px;
  font-size: 28px;
  line-height: 1.05;
  letter-spacing: -0.05em;
  cursor: pointer;
}

.card-body p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.8;
}

.card-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.compact-button {
  flex: 1;
  justify-content: center;
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

@media (max-width: 980px) {
  .favorites-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .favorites-hero,
  .card-body,
  .pagination-card {
    padding: 18px;
  }

  .card-actions,
  .pagination-card {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
