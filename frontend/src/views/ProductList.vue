<template>
    <div class="product-list-page page-shell container">
    <section class="system-page-intro">
      <div class="system-page-intro-copy">
        <span class="system-page-kicker">当季茶品</span>
        <h1>茶品商城</h1>
        <p>按茶类、产地、香型、评分和价格筛选茶品，找到适合自饮、待客或礼赠的好茶。</p>
      </div>
      <span class="system-page-metric">共上架 {{ total }} 款茶品</span>
    </section>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-categories">
        <button
          class="filter-chip"
          :class="{ active: !selectedCategory }"
          @click="selectCategory(null)"
        >
          全部
        </button>
        <button
          v-for="category in categories"
          :key="category.id"
          class="filter-chip"
          :class="{ active: selectedCategory === category.id }"
          @click="selectCategory(category.id)"
        >
          {{ category.name }}
        </button>
      </div>
      
      <div class="filter-options">
        <div class="select-wrapper">
          <select v-model="sortBy" class="filter-select">
            <option value="created_at">最新发布</option>
            <option value="sales">销量优先</option>
            <option value="rating">评分优先</option>
            <option value="price">价格优先</option>
          </select>
          <el-icon class="select-icon"><ArrowDown /></el-icon>
        </div>
        <div class="select-wrapper">
          <select v-model="sortOrder" class="filter-select">
            <option value="desc">降序</option>
            <option value="asc">升序</option>
          </select>
          <el-icon class="select-icon"><ArrowDown /></el-icon>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div v-for="i in 8" :key="i" class="skeleton-card"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="products.length === 0" class="state-card section-card">
      <div class="empty-illustration">
        <el-icon><ShoppingBag /></el-icon>
      </div>
      <strong>暂无匹配的茶品</strong>
      <p>当前分类或搜索条件下没有茶品，请调整筛选条件后重试。</p>
      <button class="accent-button" @click="selectCategory(null)">查看全部</button>
    </div>

    <!-- 商品列表 -->
    <div v-else class="product-grid">
      <article
        v-for="product in products"
        :key="product.id"
        class="product-card"
        @click="goToDetail(product.id)"
      >
        <div class="product-media">
          <img
            :src="resolveProductImage(product.cover_image, product.title)"
            :alt="product.title"
            @error="(event) => handleImageFallback(event, product.title)"
          />
          <div v-if="product.original_price" class="product-badge sale">特惠</div>
        </div>
        
        <div class="product-content">
          <div class="product-main">
            <h3 class="product-title">{{ product.title }}</h3>
            <p class="product-desc">{{ product.description }}</p>
          </div>
          
          <div class="product-meta">
            <div class="meta-row">
              <span v-if="product.category" class="product-category">{{ product.category.name }}</span>
              <div v-if="product.rating" class="product-rating">
                <el-icon><StarFilled /></el-icon>
                <span>{{ product.rating.toFixed(1) }}</span>
              </div>
            </div>
            
            <div class="product-footer">
              <div class="price-block">
                <span class="price-current">¥{{ product.price }}</span>
                <span v-if="product.original_price" class="price-original">¥{{ product.original_price }}</span>
              </div>
              <button class="add-btn" @click.stop="addToCart(product)">
                <el-icon><Plus /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination-bar">
      <button class="page-btn" :disabled="currentPage === 1" @click="handlePageChange(currentPage - 1)">
        <el-icon><ArrowLeft /></el-icon>
      </button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="handlePageChange(currentPage + 1)">
        <el-icon><ArrowRight /></el-icon>
      </button>
    </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ShoppingBag, StarFilled, Plus, ArrowDown, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { useProductStore } from '@/stores/product'
import { useCartStore } from '@/stores/cart'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const router = useRouter()
const route = useRoute()
const productStore = useProductStore()
const cartStore = useCartStore()

const loading = ref(false)
const products = ref<any[]>([])
const categories = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const totalPages = ref(0)

const selectedCategory = ref<string | null>(null)
const sortBy = ref('created_at')
const sortOrder = ref('desc')

async function loadCategories() {
  try {
    categories.value = await productStore.fetchCategories()
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

async function loadProducts() {
  loading.value = true
  try {
    const keyword = typeof route.query.keyword === 'string' ? route.query.keyword.trim() : undefined
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      order: sortOrder.value,
      category_id: selectedCategory.value ?? undefined,
      keyword: keyword || undefined
    }

    const response = await productStore.fetchProducts(params)
    products.value = response.products
    total.value = response.total
    totalPages.value = response.total_pages
  } catch (error) {
    console.error('加载商品失败:', error)
    ElMessage.error('茶品列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function selectCategory(categoryId: string | null) {
  selectedCategory.value = categoryId
  currentPage.value = 1
  loadProducts()
}

function goToDetail(productId: string) {
  router.push(`/products/${productId}`)
}

async function addToCart(product: any) {
  try {
    await cartStore.addToCart(product.id, 1)
    ElMessage.success('茶品已加入购物车')
  } catch (error) {
    ElMessage.error('加入购物车失败，请稍后重试')
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProducts()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch([sortBy, sortOrder], () => {
  currentPage.value = 1
  loadProducts()
})

watch(() => route.query.keyword, () => {
  currentPage.value = 1
  loadProducts()
})

onMounted(() => {
  loadCategories()
  loadProducts()
})
</script>

<style scoped>
.product-list-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 24px 0 8px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.result-count {
  font-size: 14px;
  color: var(--text-muted);
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-categories {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-chip {
  height: 32px;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: white;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-chip:hover {
  border-color: var(--primary-light);
  color: var(--primary);
  background: #F8FAFC;
}

.filter-chip.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
  box-shadow: var(--shadow-sm);
}

.filter-options {
  display: flex;
  align-items: center;
  gap: 12px;
}

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-select {
  height: 32px;
  padding: 0 32px 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  appearance: none;
  transition: border-color 0.2s;
}

.filter-select:hover {
  border-color: var(--primary-light);
}

.filter-select:focus {
  outline: none;
  border-color: var(--primary);
}

.select-icon {
  position: absolute;
  right: 10px;
  font-size: 12px;
  color: var(--text-muted);
  pointer-events: none;
}

/* 加载状态 */
.loading-state {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
}

.skeleton-card {
  aspect-ratio: 0.8;
  background: #F1F5F9;
  border-radius: 16px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 空状态 */
.state-card {
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  text-align: center;
}

.empty-illustration {
  width: 80px;
  height: 80px;
  background: #F1F5F9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--text-muted);
}

/* 商品网格 */
.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.product-card {
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-light);
}

.product-media {
  position: relative;
  aspect-ratio: 4/3;
  overflow: hidden;
  background: #F8FAFC;
  border-bottom: 1px solid var(--border-light);
}

.product-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.product-card:hover .product-media img {
  transform: scale(1.05);
}

.product-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}

.product-badge.sale {
  background: var(--danger);
  color: white;
}

.product-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
  justify-content: space-between;
  gap: 16px;
}

.product-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 6px;
  line-height: 1.4;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.product-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.product-category {
  font-size: 11px;
  color: var(--text-secondary);
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.product-rating {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}

.product-rating .el-icon {
  color: var(--warning);
}

.product-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.price-block {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.price-current {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.price-original {
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: line-through;
}

.add-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.add-btn:hover {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

/* 分页 */
.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 24px 0;
}

.page-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: #F8FAFC;
  border-color: var(--text-muted);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-categories {
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
  }
  
  .filter-options {
    justify-content: space-between;
  }
  
  .select-wrapper {
    flex: 1;
  }
  
  .filter-select {
    width: 100%;
  }
  
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .product-grid {
    grid-template-columns: 1fr;
  }
}
</style>
