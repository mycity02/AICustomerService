<template>
  <div class="cart-page page-shell container">
    <section class="system-page-intro">
      <div class="system-page-intro-copy">
        <span class="system-page-kicker">订单结算</span>
        <h1>茶品购物车</h1>
        <p>核对已选茶品、购买数量与订单金额，确认无误后统一提交结算。</p>
      </div>
      <span class="system-page-metric">已选 {{ totalItems }} 件茶品</span>
    </section>

    <section v-if="loading" class="state-card section-card">
      <div class="loader"></div>
      <strong>正在同步购物车</strong>
      <p>正在同步茶品信息、数量与最新价格。</p>
    </section>

    <section v-else-if="items.length === 0" class="state-card section-card">
      <div class="empty-illustration">
        <el-icon><ShoppingCart /></el-icon>
      </div>
      <strong>购物车中还没有茶品</strong>
      <p>前往茶品商城挑选适合自饮或礼赠的好茶，再回来统一结算。</p>
      <button class="accent-button" type="button" @click="router.push('/products')">选购茶品</button>
    </section>

    <div v-else class="cart-content">
      <div class="cart-list">
        <article v-for="item in items" :key="item.id" class="cart-item">
          <div class="item-media">
            <img
              :src="resolveProductImage(item.product?.cover_image, item.product?.title)"
              :alt="item.product?.title"
              @error="(event) => handleImageFallback(event, item.product?.title)"
            />
          </div>

          <div class="item-body">
            <div class="item-main">
              <div class="item-info">
                <h3 class="item-title" @click="router.push(`/products/${item.product_id}`)">
                  {{ item.product?.title }}
                </h3>
                <div class="item-tags">
                  <span>{{ getDifficultyText(item.product?.difficulty) }}</span>
                  <span v-if="item.product?.tech_stack?.length">
                    {{ item.product.tech_stack.slice(0, 2).join(' · ') }}
                  </span>
                </div>
              </div>
              <div class="item-price-block">
                <strong class="item-total-price">
                  {{ formatCents((item.product?.price || 0) * item.quantity) }}
                </strong>
                <span class="item-unit-price">
                  {{ formatCents(item.product?.price || 0) }} / 件
                </span>
              </div>
            </div>

            <div class="item-actions-row">
              <div class="quantity-control">
                <button 
                  type="button" 
                  :disabled="item.quantity <= 1 || loading" 
                  @click="updateQuantity(item.product_id, item.quantity - 1)"
                >
                  <el-icon><Minus /></el-icon>
                </button>
                <input type="text" readonly :value="item.quantity" />
                <button 
                  type="button" 
                  :disabled="loading" 
                  @click="updateQuantity(item.product_id, item.quantity + 1)"
                >
                  <el-icon><Plus /></el-icon>
                </button>
              </div>
              
              <button class="remove-btn" type="button" @click="removeItem(item.product_id)">
                移除
              </button>
            </div>
          </div>
        </article>
      </div>

      <aside class="cart-sidebar">
        <div class="summary-card">
          <h2>结算摘要</h2>
          
          <div class="summary-list">
            <div class="summary-item">
              <span>茶品数量</span>
              <span>{{ totalItems }}</span>
            </div>
            <div class="summary-item">
              <span>商品总额</span>
              <span>{{ formatCents(totalAmount) }}</span>
            </div>
            <div class="summary-item highlight">
              <span>应付金额</span>
              <strong>{{ formatCents(totalAmount) }}</strong>
            </div>
          </div>

          <div class="summary-actions">
            <button 
              class="checkout-btn" 
              type="button" 
              :disabled="busy" 
              @click="handleCheckout"
            >
              {{ checkoutPending ? '正在创建订单...' : '立即结算' }}
            </button>
            <button 
              class="clear-btn" 
              type="button" 
              :disabled="busy" 
              @click="handleClearCart"
            >
              清空购物车
            </button>
          </div>
          
          <div class="summary-footer">
            <p><el-icon><ChatDotRound /></el-icon> 支持 AI 选茶顾问咨询</p>
            <p><el-icon><Document /></el-icon> 结算后自动生成茶品订单</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Minus, Plus } from '@element-plus/icons-vue'
import { useCartStore } from '@/stores/cart'
import { useOrderStore } from '@/stores/order'
import { handleImageFallback, resolveProductImage } from '@/utils/image'

const router = useRouter()
const cartStore = useCartStore()
const orderStore = useOrderStore()
const { items, loading, totalAmount, totalItems } = storeToRefs(cartStore)

const checkoutPending = ref(false)

const busy = computed(() => loading.value || checkoutPending.value)

onMounted(() => {
  cartStore.fetchCart()
})

function formatCents(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2
  }).format((value || 0) / 100)
}

function getDifficultyText(difficulty?: string) {
  const map: Record<string, string> = {
    easy: '清新鲜爽',
    medium: '醇香回甘',
    hard: '浓醇耐泡'
  }

  return map[difficulty || ''] || '经典茶品'
}

async function updateQuantity(productId: string, quantity: number) {
  try {
    await cartStore.updateQuantity(productId, quantity)
  } catch (error) {
    console.error('Failed to update cart quantity', error)
    ElMessage.error('更新数量失败，请稍后重试')
  }
}

async function removeItem(productId: string) {
  try {
    await ElMessageBox.confirm('确定要从购物车移除这件茶品吗？', '移除茶品', {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await cartStore.removeFromCart(productId)
    ElMessage.success('茶品已移除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to remove item from cart', error)
      ElMessage.error('移除失败，请稍后重试')
    }
  }
}

async function handleClearCart() {
  try {
    await ElMessageBox.confirm('确定清空购物车吗？此操作不会删除订单记录。', '清空购物车', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await cartStore.clearCart()
    ElMessage.success('购物车已清空')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to clear cart', error)
      ElMessage.error('清空失败，请稍后重试')
    }
  }
}

async function handleCheckout() {
  if (!items.value.length) {
    ElMessage.warning('购物车为空，请先添加茶品再结算')
    return
  }

  checkoutPending.value = true

  try {
    const order = await orderStore.createOrder(items.value.map(item => item.product_id))
    await cartStore.fetchCart()
    ElMessage.success(`订单创建成功：${order.order_no}`)
    router.push('/orders')
  } catch (error: any) {
    console.error('Failed to create order', error)
    ElMessage.error(error.response?.data?.detail || error.message || '结算失败，请稍后重试')
  } finally {
    checkoutPending.value = false
  }
}
</script>

<style scoped>
.cart-page {
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

.item-count {
  font-size: 14px;
  color: var(--text-muted);
}

.cart-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: start;
}

.cart-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cart-item {
  display: flex;
  gap: 20px;
  padding: 20px;
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  transition: all 0.2s ease;
}

.cart-item:hover {
  border-color: var(--primary-light);
  box-shadow: var(--shadow-sm);
}

.item-media {
  width: 100px;
  height: 100px;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-light);
  background: #F8FAFC;
}

.item-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
}

.item-main {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 8px;
  cursor: pointer;
  line-height: 1.4;
  transition: color 0.2s;
}

.item-title:hover {
  color: var(--primary);
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.item-tags span {
  font-size: 12px;
  color: var(--text-secondary);
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.item-price-block {
  text-align: right;
  flex-shrink: 0;
}

.item-total-price {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.item-unit-price {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
}

.item-actions-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quantity-control {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.quantity-control button {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: white;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.quantity-control button:hover:not(:disabled) {
  background: #F8FAFC;
  color: var(--primary);
}

.quantity-control button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quantity-control input {
  width: 40px;
  height: 32px;
  border: none;
  border-left: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  outline: none;
}

.remove-btn {
  font-size: 13px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.remove-btn:hover {
  color: var(--danger);
  text-decoration: underline;
}

.cart-sidebar {
  position: sticky;
  top: 24px;
}

.summary-card {
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.summary-card h2 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 20px;
  color: var(--text);
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--text-secondary);
}

.summary-item.highlight {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
  color: var(--text);
  font-weight: 600;
}

.summary-item.highlight strong {
  font-size: 20px;
  color: var(--primary);
}

.summary-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.checkout-btn {
  width: 100%;
  height: 44px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.checkout-btn:hover:not(:disabled) {
  background: var(--primary-dark);
}

.checkout-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.clear-btn {
  width: 100%;
  height: 40px;
  background: white;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover:not(:disabled) {
  background: #F8FAFC;
  border-color: var(--text-muted);
}

.summary-footer {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-footer p {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

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

@media (max-width: 900px) {
  .cart-content {
    grid-template-columns: 1fr;
  }
  
  .cart-sidebar {
    position: static;
  }
}

@media (max-width: 600px) {
  .item-main {
    flex-direction: column;
    gap: 8px;
  }
  
  .item-price-block {
    text-align: left;
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
}
</style>
