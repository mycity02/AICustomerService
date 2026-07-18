<template>
  <div class="app-layout">
    <!-- 顶部导航 -->
    <header class="app-header">
      <div class="header-container">
        <!-- Logo -->
        <router-link to="/" class="logo">
          <div class="logo-icon">
            <el-icon><ShoppingBag /></el-icon>
          </div>
          <span class="logo-text">云岫茶坊</span>
        </router-link>

        <!-- 搜索栏 -->
        <div class="header-search">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索茶类、产地、香型或商品..."
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </button>
        </div>

        <!-- 导航菜单 -->
        <nav class="header-nav">
          <router-link to="/products" class="nav-link">茶品商城</router-link>
          <router-link to="/chat" class="nav-link nav-link-ai">
            <el-icon><ChatDotRound /></el-icon>
            <span>智能客服</span>
          </router-link>
        </nav>

        <!-- 用户操作区 -->
        <div class="header-actions">
          <router-link to="/favorites" class="action-btn" title="我的收藏">
            <el-icon><Star /></el-icon>
          </router-link>
          <router-link to="/cart" class="action-btn cart-btn" title="茶品购物车">
            <el-icon><ShoppingCart /></el-icon>
            <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
          </router-link>
          <router-link to="/orders" class="action-btn" title="茶品订单">
            <el-icon><Document /></el-icon>
          </router-link>
          
          <!-- 用户菜单 -->
          <el-dropdown v-if="authStore.isAuthenticated" trigger="click">
            <div class="user-menu">
              <div class="user-avatar">{{ userInitial }}</div>
              <span class="user-name">{{ authStore.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/orders')">
                  <el-icon><Document /></el-icon>我的订单
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/favorites')">
                  <el-icon><Star /></el-icon>我的收藏
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/refunds')">
                  <el-icon><Money /></el-icon>售后服务
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <router-link v-else to="/login" class="btn btn-primary btn-sm">登录</router-link>
        </div>

        <!-- 移动端菜单按钮 -->
        <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen">
          <el-icon><Menu /></el-icon>
        </button>
      </div>
    </header>

    <!-- 移动端菜单 -->
    <div v-if="mobileMenuOpen" class="mobile-menu" @click="mobileMenuOpen = false">
      <div class="mobile-menu-content" @click.stop>
        <div class="mobile-menu-header">
          <span class="mobile-menu-title">菜单</span>
          <button class="mobile-menu-close" @click="mobileMenuOpen = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>
        <nav class="mobile-nav">
          <router-link to="/products" class="mobile-nav-link" @click="mobileMenuOpen = false">
            <el-icon><ShoppingBag /></el-icon>
            <span>茶品商城</span>
          </router-link>
          <router-link to="/chat" class="mobile-nav-link" @click="mobileMenuOpen = false">
            <el-icon><ChatDotRound /></el-icon>
            <span>智能客服</span>
          </router-link>
          <router-link to="/cart" class="mobile-nav-link" @click="mobileMenuOpen = false">
            <el-icon><ShoppingCart /></el-icon>
            <span>购物车</span>
          </router-link>
          <router-link to="/orders" class="mobile-nav-link" @click="mobileMenuOpen = false">
            <el-icon><Document /></el-icon>
            <span>我的订单</span>
          </router-link>
          <router-link to="/favorites" class="mobile-nav-link" @click="mobileMenuOpen = false">
            <el-icon><Star /></el-icon>
            <span>我的收藏</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- 主内容区 -->
    <main class="app-main">
      <slot />
    </main>

    <!-- 底部 -->
    <footer class="app-footer">
      <div class="footer-container">
        <div class="footer-section">
          <h4>关于平台</h4>
          <p>融合精选茶品、智能选茶、订单物流与售后服务的一站式茶叶销售系统。</p>
        </div>
        <div class="footer-section">
          <h4>客户服务</h4>
          <router-link to="/chat">智能客服</router-link>
          <router-link to="/refunds">售后服务</router-link>
          <router-link to="/orders">订单追踪</router-link>
        </div>
        <div class="footer-section">
          <h4>平台服务</h4>
          <router-link to="/products">选购茶品</router-link>
          <router-link to="/cart">茶品购物车</router-link>
          <router-link to="/orders">订单管理</router-link>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© 2026 云岫茶坊 · AI 茶叶销售与智能导购系统</p>
      </div>
    </footer>

    <!-- 智能客服悬浮按钮 -->
    <router-link to="/chat" class="ai-float-btn" title="智能客服">
      <el-icon><ChatDotRound /></el-icon>
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import {
  ShoppingBag,
  Search,
  ChatDotRound,
  Star,
  ShoppingCart,
  Document,
  ArrowDown,
  Money,
  SwitchButton,
  Menu,
  Close
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()
const { itemCount: cartCount } = storeToRefs(cartStore)

const searchKeyword = ref('')
const mobileMenuOpen = ref(false)

const userInitial = computed(() => {
  return authStore.user?.username?.charAt(0).toUpperCase() || 'U'
})

function handleSearch() {
  if (searchKeyword.value.trim()) {
    router.push({
      path: '/products',
      query: { keyword: searchKeyword.value.trim() }
    })
    searchKeyword.value = ''
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.header-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  height: 64px;
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--text);
  flex-shrink: 0;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--primary-gradient);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 搜索栏 */
.header-search {
  flex: 1;
  max-width: 480px;
  position: relative;
}

.header-search input {
  width: 100%;
  height: 40px;
  padding: 0 var(--space-10) 0 var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--gray-50);
  font-size: 14px;
  transition: all 0.2s ease;
}

.header-search input:focus {
  outline: none;
  background: var(--surface);
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-lighter);
}

.search-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.search-btn:hover {
  background: var(--primary-dark);
}

/* 导航菜单 */
.header-nav {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--radius);
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: var(--primary);
  background: var(--primary-lighter);
}

.nav-link.router-link-active {
  color: var(--primary);
  background: var(--primary-lighter);
}

.nav-link-ai {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%);
  color: var(--primary);
}

.nav-link-ai:hover {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%);
}

/* 用户操作区 */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.action-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s ease;
  position: relative;
}

.action-btn:hover {
  background: var(--gray-100);
  color: var(--primary);
}

.cart-btn .cart-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--danger);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2) var(--space-1) var(--space-1);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.2s ease;
}

.user-menu:hover {
  background: var(--gray-100);
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: var(--primary-gradient);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text);
  font-size: 20px;
}

.mobile-menu-btn:hover {
  background: var(--gray-100);
}

/* 移动端菜单 */
.mobile-menu {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.5);
}

.mobile-menu-content {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 280px;
  background: var(--surface);
  box-shadow: var(--shadow-xl);
}

.mobile-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.mobile-menu-title {
  font-size: 16px;
  font-weight: 600;
}

.mobile-menu-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text);
}

.mobile-menu-close:hover {
  background: var(--gray-100);
}

.mobile-nav {
  padding: var(--space-2);
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  color: var(--text);
  text-decoration: none;
  font-size: 14px;
  border-radius: var(--radius);
  transition: all 0.2s ease;
}

.mobile-nav-link:hover,
.mobile-nav-link.router-link-active {
  background: var(--primary-lighter);
  color: var(--primary);
}

/* 主内容区 */
.app-main {
  flex: 1;
  padding: var(--space-6) 0;
}

/* 底部 */
.app-footer {
  background: var(--gray-900);
  color: var(--gray-400);
  padding: var(--space-12) 0 var(--space-6);
}

.footer-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-8);
}

.footer-section h4 {
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: var(--space-4);
}

.footer-section p {
  font-size: 14px;
  line-height: 1.6;
}

.footer-section a {
  display: block;
  color: var(--gray-400);
  text-decoration: none;
  font-size: 14px;
  padding: var(--space-1) 0;
  transition: color 0.2s ease;
}

.footer-section a:hover {
  color: white;
}

.footer-bottom {
  max-width: 1440px;
  margin: var(--space-8) auto 0;
  padding: var(--space-6) var(--space-4) 0;
  border-top: 1px solid var(--gray-800);
  text-align: center;
  font-size: 13px;
}

/* 智能客服悬浮按钮 */
.ai-float-btn {
  position: fixed;
  right: var(--space-6);
  bottom: var(--space-6);
  width: 56px;
  height: 56px;
  background: var(--primary-gradient);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  box-shadow: var(--shadow-lg), 0 0 20px rgba(37, 99, 235, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 90;
  text-decoration: none;
}

.ai-float-btn:hover {
  transform: scale(1.1) translateY(-4px);
  box-shadow: var(--shadow-xl), 0 0 30px rgba(37, 99, 235, 0.4);
}

/* 响应式 */
@media (max-width: 1024px) {
  .header-nav {
    display: none;
  }
  
  .header-search {
    max-width: 320px;
  }
}

@media (max-width: 768px) {
  .header-container {
    gap: var(--space-3);
  }
  
  .logo-text {
    display: none;
  }
  
  .header-search {
    max-width: none;
  }
  
  .header-search input {
    height: 36px;
    font-size: 13px;
  }
  
  .action-btn:not(.cart-btn) {
    display: none;
  }
  
  .user-name {
    display: none;
  }
  
  .mobile-menu-btn {
    display: flex;
  }
  
  .mobile-menu {
    display: block;
  }
  
  .app-main {
    padding: var(--space-4) 0;
  }
  
  .footer-container {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }
  
  .ai-float-btn {
    right: var(--space-4);
    bottom: var(--space-4);
    width: 48px;
    height: 48px;
    font-size: 20px;
  }
}
</style>
