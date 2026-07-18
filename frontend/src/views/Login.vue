<template>
  <div class="auth-page">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <div class="auth-shell">
      <section class="auth-story">
        <div class="story-header">
          <span class="eyebrow">云岫茶坊 · AI 茶叶销售系统</span>
          <h1>让选茶、购买与售后服务更简单</h1>
          <p>
            登录后可按茶类、产地与香型挑选茶品，并使用 AI 选茶顾问完成风味推荐、
            商品对比、订单物流查询和售后咨询。
          </p>
        </div>

        <div class="story-grid">
          <article class="story-card">
            <div class="story-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <strong>智能选茶</strong>
            <p>结合自饮或礼赠场景、预算与口味偏好，推荐更合适的茶品</p>
          </article>
          <article class="story-card">
            <div class="story-icon">
              <el-icon><ShoppingBag /></el-icon>
            </div>
            <strong>茶品推荐</strong>
            <p>从茶类检索、风味对比到冲泡建议，帮助你快速完成购买决策</p>
          </article>
          <article class="story-card">
            <div class="story-icon">
              <el-icon><Service /></el-icon>
            </div>
            <strong>订单与售后</strong>
            <p>统一查询订单、物流进度与退款售后，让服务过程清晰可追踪</p>
          </article>
        </div>
      </section>

      <div class="auth-card-wrapper">
        <div class="auth-card">
          <div class="card-head">
            <span class="eyebrow">欢迎回来</span>
            <h2>登录账号</h2>
            <p>登录云岫茶坊，继续管理茶品咨询、订单物流与售后进度</p>
          </div>

          <form class="auth-form" @submit.prevent="handleLogin">
            <div class="form-group">
              <label>用户名</label>
              <input
                v-model.trim="form.username"
                type="text"
                placeholder="请输入用户名"
                autocomplete="username"
                @keydown.enter.prevent="handleLogin"
              />
            </div>

            <div class="form-group">
              <label>密码</label>
              <input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                autocomplete="current-password"
                @keydown.enter.prevent="handleLogin"
              />
            </div>

            <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

            <button
              type="submit"
              class="submit-btn"
              :disabled="loading"
              :class="{ loading: loading }"
            >
              <span v-if="!loading">登录</span>
              <span v-else class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </button>

            <div class="helper-row">
              <span>还没有账号？</span>
              <button type="button" class="link-btn" @click="handleRegister">
                立即注册
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, ShoppingBag, Service } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: ''
})

onMounted(() => {
  authStore.logout()
})

async function handleLogin() {
  if (loading.value) return

  const username = form.username.trim()
  const password = form.password

  if (!username) {
    errorMessage.value = '请输入用户名'
    ElMessage.warning('请输入用户名')
    return
  }

  if (!password) {
    errorMessage.value = '请输入密码'
    ElMessage.warning('请输入密码')
    return
  }

  errorMessage.value = ''
  loading.value = true

  try {
    const success = await authStore.login({
      username,
      password
    })

    if (success) {
      ElMessage.success('登录成功')
      router.push('/')
      return
    }

    errorMessage.value = '登录失败，请检查用户名和密码'
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

function handleRegister() {
  router.push('/register')
}
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  padding: 20px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
}

.ambient-left {
  top: -100px;
  left: -80px;
  width: 400px;
  height: 400px;
  background: rgba(124, 58, 237, 0.15);
  animation: float 20s ease-in-out infinite;
}

.ambient-right {
  right: -100px;
  bottom: -100px;
  width: 350px;
  height: 350px;
  background: rgba(6, 182, 212, 0.12);
  animation: float 25s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.auth-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1200px;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 420px);
  gap: 24px;
}

/* 左侧故事区域 */
.auth-story {
  padding: 48px;
  border-radius: var(--radius-xl);
  background: var(--hero-gradient);
  color: #fff;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
}

.story-header {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.auth-story :deep(.eyebrow) {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.auth-story :deep(.eyebrow)::before {
  background: var(--accent);
}

.auth-story h1 {
  margin: 0;
  max-width: 600px;
  font-size: clamp(36px, 4vw, 56px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.auth-story > .story-header > p {
  max-width: 520px;
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.8);
}

.story-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.story-card {
  padding: 24px 20px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.story-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.story-icon {
  width: 44px;
  height: 44px;
  margin-bottom: 16px;
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.story-card strong {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
  font-weight: 600;
}

.story-card p {
  margin: 0;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
  line-height: 1.6;
}

/* 右侧登录卡片 */
.auth-card-wrapper {
  display: flex;
  align-items: center;
}

.auth-card {
  width: 100%;
  padding: 40px;
  border-radius: var(--radius-xl);
  background: var(--surface);
  border: 1px solid var(--border);
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow);
}

.card-head {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
}

.card-head h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}

.card-head p {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.6;
}

/* 表单样式 */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-group input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 15px;
  transition: all 0.2s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px var(--primary-lighter);
}

.form-group input::placeholder {
  color: var(--muted);
}

.error-text {
  margin: -8px 0;
  color: var(--danger);
  font-size: 13px;
  line-height: 1.5;
}

.submit-btn {
  width: 100%;
  height: 48px;
  margin-top: 8px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--primary-gradient);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: var(--shadow);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-dots {
  display: flex;
  gap: 4px;
  justify-content: center;
  align-items: center;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: bounce 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.helper-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 14px;
  color: var(--text-muted);
}

.link-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s ease;
}

.link-btn:hover {
  color: var(--primary-dark);
}

/* 响应式 */
@media (max-width: 1080px) {
  .auth-shell {
    grid-template-columns: 1fr;
    max-width: 480px;
  }

  .auth-story {
    display: none;
  }

  .auth-card-wrapper {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .auth-page {
    padding: 16px;
  }

  .auth-card {
    padding: 28px 24px;
  }

  .card-head h2 {
    font-size: 24px;
  }
}
</style>
