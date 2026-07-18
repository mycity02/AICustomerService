<template>
  <article class="product-card" @click="goToDetail">
    <div class="card-media">
      <img
        :src="resolveProductImage(product.cover_image, product.title)"
        :alt="product.title"
        @error="(event) => handleImageFallback(event, product.title)"
      />

      <div class="media-gradient"></div>

      <div class="media-chips">
        <span class="media-chip">{{ difficultyText }}</span>
        <span class="media-chip subtle">{{ product.category?.name || '当季精选' }}</span>
      </div>
    </div>

    <div class="card-body">
      <div class="card-topline">
        <span class="card-kicker">严选好茶</span>
        <span class="rating-pill">
          <el-icon><Star /></el-icon>
          {{ product.rating.toFixed(1) }}
        </span>
      </div>

      <h3 class="card-title">{{ product.title }}</h3>
      <p class="card-description">{{ previewDescription }}</p>

      <div v-if="product.tech_stack?.length" class="tech-list">
        <span v-for="tech in product.tech_stack.slice(0, 3)" :key="tech">{{ tech }}</span>
      </div>

      <div class="card-footer">
        <div class="price-block">
          <strong>{{ formatPrice(product.price) }}</strong>
          <span v-if="product.original_price">{{ formatPrice(product.original_price) }}</span>
          <small>已售 {{ product.sales_count }} · {{ product.review_count }} 条评价</small>
        </div>

        <button class="card-action" type="button" @click.stop="handleAddToCart">
          加入购物车
        </button>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Star } from '@element-plus/icons-vue'
import { useCartStore } from '@/stores/cart'
import type { Product } from '@/stores/product'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const props = defineProps<{
  product: Product
}>()

const router = useRouter()
const cartStore = useCartStore()

const difficultyText = computed(() => {
  const map: Record<string, string> = {
    easy: '清新鲜爽',
    medium: '醇香回甘',
    hard: '浓醇耐泡'
  }

  return map[props.product.difficulty] || props.product.difficulty
})

const previewDescription = computed(() => {
  const raw = props.product.description?.trim() || '包含产地、工艺、香型与冲泡建议，可先咨询 AI 选茶顾问。'
  return raw.length > 72 ? `${raw.slice(0, 72)}...` : raw
})

function formatPrice(value?: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format(value ?? 0)
}

function goToDetail() {
  router.push(`/products/${props.product.id}`)
}

async function handleAddToCart() {
  try {
    await cartStore.addToCart(props.product.id)
    ElMessage.success('已加入购物车')
  } catch (error) {
    console.error('Failed to add item to cart', error)
    ElMessage.error('加入购物车失败，请稍后重试')
  }
}
</script>

<style scoped>
.product-card {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  overflow: hidden;
  border-radius: 30px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.product-card:hover {
  transform: translateY(-6px);
  border-color: rgba(0, 113, 227, 0.16);
  box-shadow: var(--shadow);
}

.card-media {
  position: relative;
  aspect-ratio: 1.16;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(0, 113, 227, 0.1));
}

.card-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.32s ease;
}

.product-card:hover .card-media img {
  transform: scale(1.04);
}

.media-gradient {
  position: absolute;
  inset: auto 0 0;
  height: 48%;
  background: linear-gradient(180deg, transparent 0%, rgba(10, 18, 34, 0.74) 100%);
}

.media-chips {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.media-chip {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  backdrop-filter: blur(10px);
}

.media-chip.subtle {
  background: rgba(10, 18, 34, 0.7);
  color: #f8fbff;
}

.card-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
}

.card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--primary);
}

.rating-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  font-size: 12px;
  font-weight: 700;
}

.card-title {
  margin: 0;
  font-size: 22px;
  line-height: 1.15;
  letter-spacing: -0.04em;
}

.card-description {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.7;
}

.tech-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tech-list span {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.card-footer {
  margin-top: auto;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}

.price-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-block strong {
  font-size: 26px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.price-block span {
  color: var(--text-muted);
  font-size: 13px;
  text-decoration: line-through;
}

.price-block small {
  color: var(--text-muted);
  font-size: 12px;
}

.card-action {
  min-width: 126px;
  height: 46px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 18px 30px rgba(0, 113, 227, 0.18);
}

@media (max-width: 720px) {
  .card-title {
    font-size: 20px;
  }

  .card-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .card-action {
    width: 100%;
  }
}
</style>
