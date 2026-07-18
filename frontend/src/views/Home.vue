<template>
    <div class="home-page">
      <div class="container">
        <section class="hero">
          <div class="hero-content">
            <span class="hero-tag">云岫茶坊 · AI 茶叶销售系统</span>
            <h1 class="hero-title">好茶甄选与智能导购，一站完成</h1>
            <p class="hero-desc">按茶类、产地与香型挑选茶品，通过 AI 选茶顾问获得饮用场景、预算与冲泡建议。</p>
            <div class="hero-actions">
              <router-link class="btn btn-primary" to="/products">进入茶品商城</router-link>
              <router-link class="btn btn-outline" to="/chat">咨询智能客服</router-link>
            </div>
          </div>
          <div class="hero-panel">
            <strong>智能购茶流程</strong>
            <ul>
              <li>按茶类、产地与香型筛选茶品</li>
              <li>通过 AI 顾问获得选茶与冲泡建议</li>
              <li>统一管理订单、物流与售后进度</li>
            </ul>
          </div>
        </section>

        <section class="category-section">
          <div class="section-header">
            <h2>茶品分类</h2>
            <router-link to="/products" class="section-link">
              查看全部
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
          <div class="category-grid">
            <button
              v-for="category in categories.slice(0, 8)"
              :key="category.id"
              class="category-chip"
              @click="goToCategory(category.id)"
            >
              {{ category.name }}
            </button>
          </div>
        </section>

        <section class="product-section">
          <div class="section-header">
            <h2>人气茶品</h2>
            <router-link to="/products?sort_by=sales&order=desc" class="section-link">
              销量榜单
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
          <div class="products-grid">
            <article
              v-for="product in hotProducts"
              :key="product.id"
              class="product-card"
              @click="goToProduct(product.id)"
            >
              <div class="product-image">
                <img
                  :src="resolveProductImage(product.cover_image, product.title)"
                  :alt="product.title"
                  @error="(event) => handleImageFallback(event, product.title)"
                />
                <span class="product-badge">热销</span>
              </div>
              <div class="product-info">
                <h3 class="product-title">{{ product.title }}</h3>
                <p class="product-desc">{{ product.description }}</p>
                <div class="product-footer">
                  <span class="product-price">¥{{ product.price }}</span>
                  <button class="btn-cart" @click.stop="addToCart(product)">
                    <el-icon><ShoppingCart /></el-icon>
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="service-section">
          <router-link to="/orders" class="service-card">
            <el-icon><Document /></el-icon>
            <div>
              <strong>订单管理</strong>
              <p>查询订单状态与物流信息</p>
            </div>
          </router-link>
          <router-link to="/chat" class="service-card">
            <el-icon><ChatDotRound /></el-icon>
            <div>
              <strong>AI 选茶顾问</strong>
              <p>选茶推荐、风味对比与冲泡问题即时咨询</p>
            </div>
          </router-link>
          <router-link to="/refunds" class="service-card">
            <el-icon><RefreshLeft /></el-icon>
            <div>
              <strong>售后服务</strong>
              <p>退款退货申请与进度追踪</p>
            </div>
          </router-link>
        </section>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, ChatDotRound, ShoppingCart, Document, RefreshLeft } from '@element-plus/icons-vue'
import { useProductStore } from '@/stores/product'
import { useCartStore } from '@/stores/cart'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const router = useRouter()
const productStore = useProductStore()
const cartStore = useCartStore()

const hotProducts = ref<any[]>([])
const categories = ref<any[]>([])

async function loadCategories() {
  try {
    categories.value = await productStore.fetchCategories()
  } catch (error) {
    categories.value = []
  }
}

async function loadHotProducts() {
  try {
    const response = await productStore.fetchProducts({
      page: 1,
      page_size: 8,
      sort_by: 'sales',
      order: 'desc'
    })
    hotProducts.value = response.products
  } catch (error) {
    hotProducts.value = []
  }
}

function goToProduct(productId: string) {
  router.push(`/products/${productId}`)
}

function goToCategory(categoryId: string) {
  router.push({ path: '/products', query: { category_id: categoryId } })
}

async function addToCart(product: any) {
  try {
    await cartStore.addToCart(product.id, 1)
    ElMessage.success('已添加到购物车')
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

onMounted(() => {
  loadCategories()
  loadHotProducts()
})
</script>

<style scoped>
.home-page {
  padding: 24px 0 48px;
}

.hero {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}

.hero-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--primary-lighter);
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
}

.hero-title {
  margin: 14px 0 10px;
  font-size: 34px;
  line-height: 1.2;
  color: var(--text);
}

.hero-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.hero-actions {
  display: flex;
  gap: 12px;
}

.hero-panel {
  background: linear-gradient(135deg, #111827, #1f2937);
  color: white;
  border-radius: 16px;
  padding: 28px;
}

.hero-panel strong {
  display: block;
  font-size: 18px;
  margin-bottom: 12px;
}

.hero-panel ul {
  padding-left: 18px;
  display: grid;
  gap: 10px;
  color: rgba(255, 255, 255, 0.9);
}

.category-section,
.product-section {
  margin-bottom: 28px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-header h2 {
  font-size: 22px;
  color: var(--text);
}

.section-link {
  color: var(--primary);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.category-chip {
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.category-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.product-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}

.product-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-light);
}

.product-image {
  position: relative;
  aspect-ratio: 4/3;
  background: var(--gray-100);
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: var(--danger);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 3px 8px;
}

.product-info {
  padding: 12px;
}

.product-title {
  font-size: 15px;
  line-height: 1.4;
  margin-bottom: 6px;
  color: var(--text);
  display: -webkit-box;
  line-clamp: 1;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 10px;
  line-height: 1.5;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-price {
  font-size: 18px;
  font-weight: 700;
  color: var(--danger);
}

.btn-cart {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 8px;
  background: var(--primary-lighter);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.btn-cart:hover {
  background: var(--primary);
  color: white;
}

.service-section {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.service-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  text-decoration: none;
  color: var(--text);
}

.service-card .el-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary-lighter);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.service-card strong {
  display: block;
  margin-bottom: 2px;
}

.service-card p {
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 1024px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .category-grid,
  .products-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .service-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .category-grid,
  .products-grid {
    grid-template-columns: 1fr;
  }
}
</style>
