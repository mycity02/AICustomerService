<template>
  <div id="app">
    <router-view v-slot="{ Component, route }">
      <component :is="Component" v-if="route.meta.standalone" />
      <AppLayout v-else>
        <component :is="Component" />
      </AppLayout>
    </router-view>
  </div>
</template>

<script setup lang="ts">
import AppLayout from '@/components/AppLayout.vue'
</script>

<style>
/* ========================================
   云岫茶坊 AI 茶叶销售系统 - 全局设计系统
   风格: 东方茶文化 + AI 智能导购
   ======================================== */

@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700;800&display=swap');

:root {
  color-scheme: light;
  
  /* 主色调 - 科技蓝 */
  --primary: #2F6B4F;
  --primary-light: #4A8B68;
  --primary-lighter: rgba(47, 107, 79, 0.1);
  --primary-dark: #24523D;
  --primary-gradient: linear-gradient(135deg, #2F6B4F 0%, #5B8F69 100%);
  --hero-gradient: linear-gradient(135deg, #183C2B 0%, #2F6B4F 48%, #A7753A 100%);
  
  /* 辅助色 */
  --secondary: #8B633E;
  --secondary-light: #B88A5B;
  --secondary-gradient: linear-gradient(135deg, #8B633E 0%, #B88A5B 100%);
  
  /* 强调色 - 活力橙 */
  --accent: #C98B2E;
  --accent-light: #E1AE57;
  --accent-gradient: linear-gradient(135deg, #C98B2E 0%, #E1AE57 100%);
  
  /* 功能色 */
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --info: #06B6D4;
  
  /* 中性色 */
  --gray-50: #F9FAFB;
  --gray-100: #F3F4F6;
  --gray-200: #E5E7EB;
  --gray-300: #D1D5DB;
  --gray-400: #9CA3AF;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --gray-700: #374151;
  --gray-800: #1F2937;
  --gray-900: #111827;
  
  /* 背景色 */
  --bg: #F8FAFC;
  --bg-light: #FFFFFF;
  --bg-dark: #0F172A;
  --surface: #FFFFFF;
  --surface-hover: #F8FAFC;
  --surface-elevated: #FFFFFF;
  
  /* 文字色 */
  --text: #1F2937;
  --text-secondary: #4B5563;
  --text-muted: #6B7280;
  --text-light: #9CA3AF;
  --text-inverse: #FFFFFF;
  --muted: #64748B;
  
  /* 边框 */
  --border: #E5E7EB;
  --border-light: #F3F4F6;
  --border-dark: #D1D5DB;
  
  /* 阴影 */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  --shadow-primary: 0 4px 14px rgba(47, 107, 79, 0.25);
  
  /* 圆角 */
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;
  
  /* 间距 */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  
  /* Element Plus 覆盖 */
  --el-color-primary: var(--primary);
  --el-color-success: var(--success);
  --el-color-warning: var(--warning);
  --el-color-danger: var(--danger);
  --el-border-radius-base: 8px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  scroll-behavior: smooth;
}

body {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}

/* 统一业务页面标题 */
.system-page-intro {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 0 6px;
}

.system-page-intro-copy {
  min-width: 0;
}

.system-page-kicker {
  display: block;
  margin-bottom: 8px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.system-page-intro h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(28px, 3vw, 38px);
  line-height: 1.15;
}

.system-page-intro p {
  max-width: 680px;
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.75;
}

.system-page-metric {
  flex-shrink: 0;
  padding: 9px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}

@media (max-width: 640px) {
  .system-page-intro {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
    padding-top: 22px;
  }
}

/* 通用工具类 */
.container {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

.container-narrow {
  max-width: 960px;
}

.container-wide {
  max-width: 1440px;
}

/* 按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 10px 20px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  outline: none;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: white;
  box-shadow: var(--shadow-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(47, 107, 79, 0.3);
}

.btn-secondary {
  background: var(--secondary);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #6D28D9;
}

.btn-accent {
  background: var(--accent);
  color: white;
}

.btn-accent:hover:not(:disabled) {
  background: #D97706;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}

.btn-outline:hover:not(:disabled) {
  background: var(--gray-50);
  border-color: var(--gray-300);
}

.btn-ghost {
  background: transparent;
  color: var(--text);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--gray-100);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.btn-lg {
  padding: 14px 28px;
  font-size: 16px;
}

.btn-full {
  width: 100%;
}

/* 卡片样式 */
.card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card-hover:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

/* 输入框样式 */
.input {
  width: 100%;
  height: 44px;
  padding: 0 var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: all 0.2s ease;
}

.input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-lighter);
}

.input::placeholder {
  color: var(--text-light);
}

/* 标签样式 */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
}

.badge-primary {
  background: var(--primary-lighter);
  color: var(--primary);
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.badge-danger {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
}

/* 分割线 */
.divider {
  height: 1px;
  background: var(--border);
  margin: var(--space-4) 0;
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
}

/* 动画 */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease;
}

.animate-slide-up {
  animation: slideUp 0.4s ease;
}

/* 响应式工具 */
@media (max-width: 768px) {
  .container {
    padding: 0 var(--space-3);
  }
}
</style>
