<template>
  <div class="chat-container" :class="{ 'sidebar-open': sidebarVisible }">
    <div v-if="sidebarVisible" class="chat-backdrop" @click="closeSidebar"></div>

    <div class="chat-shell" :class="{ 'sidebar-collapsed': historyCollapsed && !isMobileLayout }">
      <!-- 侧边栏 - 会话列表 -->
      <div class="sidebar" :class="{ open: sidebarVisible }">
        <div class="sidebar-header">
          <div class="sidebar-title">
            <h3>云岫茶坊智能客服</h3>
          </div>

          <div class="sidebar-header-actions">
            <el-button class="sidebar-collapse" text circle @click="toggleHistoryPanel">
              <el-icon>
                <component :is="isMobileLayout ? Close : ArrowLeftBold" />
              </el-icon>
            </el-button>
          </div>
        </div>

        <div class="sidebar-toolbar">
          <el-button type="primary" style="width: 100%" @click="createNewSession">
            <el-icon><Plus /></el-icon>
            新建对话
          </el-button>
        </div>

        <div class="session-list">
          <div v-if="sessionGroups.length === 0" class="session-list-empty">
            <strong>还没有历史会话</strong>
            <p>发起选茶、冲泡、订单物流或售后咨询，系统会自动保存服务记录。</p>
          </div>

          <div
            v-for="group in sessionGroups"
            :key="group.label"
            class="session-group"
          >
            <div class="session-group-title">{{ group.label }}</div>
            <div
              v-for="session in group.sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: chatStore.currentSession?.id === session.id }"
              @click="selectSession(session.id)"
            >
              <div class="session-content">
                <div class="session-title">{{ session.title }}</div>
                <div class="session-info">{{ session.message_count }} 条消息</div>
              </div>
              <el-button
                class="session-delete-btn"
                type="danger"
                link
                @click.stop="deleteSession(session.id)"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-main" :class="{ 'is-new-chat': messageList.length === 0 }">
        <div class="chat-header">
          <div class="chat-header-main">
            <div class="chat-header-left">
              <el-button class="sidebar-toggle" text circle @click="toggleHistoryPanel">
                <el-icon>
                  <component :is="isMobileLayout ? Menu : historyCollapsed ? ArrowRightBold : ArrowLeftBold" />
                </el-icon>
              </el-button>

              <div class="chat-header-copy">
                <h3>{{ chatStore.currentSession?.title || '云岫茶坊 AI 客服' }}</h3>
              </div>
            </div>

            <div class="chat-header-actions">
              <span class="session-stat">{{ chatStore.sessions.length }} 个会话</span>
              <el-button plain @click="createNewSession">新会话</el-button>
            </div>
          </div>
        </div>

        <div class="chat-content-wrapper">
          <div ref="messageListRef" class="message-list">
            <div class="message-list-inner">
              <div v-if="messageList.length === 0" class="conversation-empty">
                <span class="system-page-kicker">云岫茶坊 AI 智能客服</span>
                <h4>你好，我是你的 AI 选茶顾问</h4>
                <p>可以根据饮用场景和口味推荐茶品，也能解答冲泡、订单物流与售后问题。</p>
                <div class="empty-suggestions">
                  <button class="suggestion-chip" type="button" @click="prefillMessage('帮我推荐一款适合送长辈、预算 300 元左右的茶')">
                    智能选茶
                  </button>
                  <button class="suggestion-chip" type="button" @click="prefillMessage('帮我查一下最近订单的物流状态')">
                    查询订单
                  </button>
                  <button class="suggestion-chip" type="button" @click="prefillMessage('收到的茶叶包装破损，售后流程怎么走？')">
                    售后咨询
                  </button>
                </div>
              </div>

              <div
                v-for="(message, _messageIndex) in messageList"
                :key="message.id"
                class="message-item"
                :class="message.role"
              >
          <!-- 用户消息 -->
          <template v-if="message.role === 'user'">
            <div class="message-avatar user-avatar">
              <el-icon><User /></el-icon>
            </div>
            <div class="message-content user-content">
              <div class="message-text">{{ message.content }}</div>
              
              <!-- 订单卡片 -->
              <div v-if="message.metadata?.order_card" class="user-order-card">
                <div class="order-card-header">
                  <span class="order-no">{{ message.metadata.order_card.order_no }}</span>
                  <span class="order-status">{{ message.metadata.order_card.status }}</span>
                </div>
                <div class="order-card-body">
                  <div class="product-name">{{ message.metadata.order_card.product_name }}</div>
                  <div class="order-amount">¥{{ message.metadata.order_card.total_amount }}</div>
                </div>
              </div>
              
              <!-- 附件列表 -->
              <div v-if="message.attachments && message.attachments.length > 0" class="message-attachments">
                <div
                  v-for="(attachment, index) in message.attachments"
                  :key="index"
                  class="attachment-item"
                  :class="{ 'is-image': isImageFile(attachment.file_type) }"
                >
                  <!-- 图片预览 -->
                  <template v-if="isImageFile(attachment.file_type)">
                    <img 
                      :src="getImageUrl(attachment.file_id)" 
                      class="attachment-image-preview"
                      @click="previewImage(getImageUrl(attachment.file_id))"
                    />
                  </template>
                  <!-- 普通文件 -->
                  <template v-else>
                    <el-icon><Document /></el-icon>
                    <span class="attachment-name">{{ attachment.file_name }}</span>
                    <span class="attachment-size">({{ formatFileSize(attachment.file_size) }})</span>
                  </template>
                </div>
              </div>
              <div class="message-time">{{ formatTime(message.created_at) }}</div>
            </div>
          </template>

          <!-- AI消息 -->
          <template v-else>
            <div class="message-avatar ai-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="message-content ai-content">
              <!-- 思考过程折叠面板 -->
              <div v-if="message.metadata?.thinking" class="thinking-panel">
                <div class="thinking-header" @click="toggleThinking(message.id)">
                  <el-icon class="thinking-icon"><ArrowRight v-if="!expandedThinking[message.id]" /><ArrowDown v-else /></el-icon>
                  <span class="thinking-title">思考过程</span>
                </div>
                <div v-show="expandedThinking[message.id]" class="thinking-content">
                  <pre>{{ message.metadata.thinking }}</pre>
                </div>
              </div>

              <!-- 正在思考状态 -->
              <div v-else-if="chatStore.loading && !message.content" class="thinking-panel">
                <div class="thinking-header">
                  <el-icon class="thinking-icon loading"><Loading /></el-icon>
                  <span class="thinking-title">正在思考</span>
                </div>
              </div>

              <!-- 消息内容 -->
              <div v-if="message.content" class="message-text">
                <MarkdownRenderer :content="message.content" />
              </div>

              <!-- 快速操作按钮 -->
              <div v-if="message.metadata?.quick_actions && message.metadata.quick_actions.length > 0" class="quick-actions">
                <div
                  v-for="(action, index) in message.metadata.quick_actions"
                  :key="index"
                  class="quick-action-item"
                  :class="action.type"
                  @click="handleQuickAction(action)"
                >
                  <!-- 简洁订单卡片样式 -->
                  <template v-if="action.type === 'order_card_simple'">
                    <div class="order-card-simple-content">
                      <div class="order-card-simple-header">
                        <span class="order-no-simple">订单号：{{ action.data.order_no }}</span>
                        <span class="order-status-simple" :class="'status-' + action.data.status">{{ action.data.status_text }}</span>
                      </div>
                      <div class="order-card-simple-body">
                        <span class="product-name-simple">{{ action.data.product_name }}</span>
                      </div>
                      <div class="order-card-simple-footer">
                        <span class="order-amount-simple">¥{{ action.data.total_amount.toFixed(2) }}</span>
                        <span class="order-time-simple">{{ formatOrderTime(action.data.created_at) }}</span>
                      </div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>
                  
                  <!-- 订单卡片样式 -->
                  <template v-else-if="action.type === 'order_card'">
                    <div class="order-card-content">
                      <div class="order-card-header">
                        <span class="order-no">订单号: {{ action.data.order_no }}</span>
                        <span class="order-status" :class="'status-' + action.data.status">{{ action.data.status_text }}</span>
                      </div>
                      <div class="order-card-body">
                        <div class="product-info">
                          <span class="product-name">{{ action.data.product_name }}</span>
                          <span v-if="action.data.item_count > 1" class="item-count">等 {{ action.data.item_count }} 件茶品</span>
                        </div>
                        <div class="order-meta">
                          <span class="order-amount">¥{{ action.data.total_amount.toFixed(2) }}</span>
                          <span class="order-time">{{ formatOrderTime(action.data.created_at) }}</span>
                        </div>
                      </div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>

                  <!-- 商品卡片样式 -->
                  <template v-else-if="action.type === 'product'">
                    <div class="product-card-content">
                      <div class="product-card-header">
                        <span class="product-card-title">{{ action.data.title }}</span>
                        <span class="product-card-price">¥{{ action.data.price.toFixed(2) }}</span>
                      </div>
                      <div class="product-card-meta">
                        <span class="product-card-rating"><el-icon class="rating-icon"><Star /></el-icon>{{ action.data.rating }}</span>
                        <span class="product-card-sales">已售 {{ action.data.sales_count }}</span>
                      </div>
                      <div v-if="action.data.tech_stack && action.data.tech_stack.length > 0" class="product-card-tech">
                        <span v-for="(tech, tIndex) in action.data.tech_stack.slice(0, 4)" :key="tIndex">{{ tech }}</span>
                      </div>
                      <div v-if="action.data.description" class="product-card-desc">{{ action.data.description }}</div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>
                  
                  <!-- 地址卡片样式 -->
                  <template v-else-if="action.type === 'address'">
                    <div class="address-card-content">
                      <div class="address-card-contact">{{ action.data.contact }} {{ action.data.phone }}</div>
                      <div class="address-card-detail">{{ action.data.address }}</div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>

                  <!-- 优惠券卡片样式 -->
                  <template v-else-if="action.type === 'coupon'">
                    <div class="coupon-card-content">
                      <div class="coupon-card-name">{{ action.data.name }}</div>
                      <div class="coupon-card-info">满¥{{ action.data.min_amount }} 减¥{{ action.data.discount }} | 有效期至 {{ action.data.expire_date }}</div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>

                  <!-- 售后卡片样式 -->
                  <template v-else-if="action.type === 'refund_card'">
                    <div class="refund-card-content">
                      <div class="refund-card-header">
                        <span class="refund-no">售后单号：{{ action.data.refund_no }}</span>
                        <span class="refund-status" :class="'status-' + action.data.status">{{ action.data.status_text }}</span>
                      </div>
                      <div class="refund-card-body">
                        <span class="refund-type">{{ action.data.refund_type_text }}</span>
                        <span class="refund-product">{{ action.data.product_name }}</span>
                      </div>
                      <div v-if="action.data.refund_amount" class="refund-card-footer">
                        <span class="refund-amount">退款：¥{{ action.data.refund_amount.toFixed(2) }}</span>
                      </div>
                    </div>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>

                  <!-- 普通按钮样式 -->
                  <template v-else>
                    <el-icon v-if="action.icon && quickActionIconMap[action.icon]" class="action-icon">
                      <component :is="quickActionIconMap[action.icon]" />
                    </el-icon>
                    <span class="action-label">{{ action.label }}</span>
                    <el-icon class="action-arrow"><ArrowRight /></el-icon>
                  </template>
                </div>
              </div>

              <div class="message-time">{{ formatTime(message.created_at) }}</div>
            </div>
          </template>
          </div>
        </div>
      </div>

      <!-- 已选择的文件预览 -->
      <div v-if="selectedFiles.length > 0" class="selected-files">
        <div class="selected-files-header">
          <span>已选择 {{ selectedFiles.length }} 个文件</span>
          <el-button type="danger" link @click="clearFiles">
            <el-icon><Delete /></el-icon>
            清除
          </el-button>
        </div>
        <div class="file-list">
          <div
            v-for="(file, index) in selectedFiles"
            :key="index"
            class="file-item"
          >
            <!-- 图片预览 -->
            <div v-if="isImageFile(file)" class="image-preview-item">
              <img :src="getFilePreviewUrl(file)" class="preview-image" />
              <span class="file-name">{{ getDisplayFileName(file) }}</span>
              <el-icon class="remove-icon" @click="removeFile(index)"><CircleClose /></el-icon>
            </div>
            <!-- 普通文件 -->
            <el-tag
              v-else
              closable
              class="file-tag"
              @close="removeFile(index)"
            >
              <el-icon><Document /></el-icon>
              {{ file.name }}
            </el-tag>
          </div>
        </div>
      </div>

      <div
        class="input-area"
        :class="{ 'drag-over': isDragOver }"
        @dragenter.prevent="handleDragEnter"
        @dragleave.prevent="handleDragLeave"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <!-- 拖拽提示 -->
        <div v-if="isDragOver" class="drag-overlay">
          <el-icon :size="48"><Upload /></el-icon>
          <span>释放文件以上传</span>
        </div>

        <div class="input-area-inner">
          <!-- 上传按钮 -->
          <el-upload
            ref="uploadRef"
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :show-file-list="false"
            :multiple="true"
            accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg"
            class="upload-btn"
          >
            <el-button type="info" circle>
              <el-icon><Paperclip /></el-icon>
            </el-button>
          </el-upload>

          <!-- 选择订单按钮 -->
          <el-button type="info" circle class="order-btn" @click="showOrderSelector">
            <el-icon><ShoppingBag /></el-icon>
          </el-button>

          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="请输入选茶、冲泡、订单物流或售后问题，也可拖拽文件到此处"
            @keydown.enter.exact.prevent="handleEnterKey"
            @paste="handlePaste"
          />
          <el-button
            type="primary"
            :loading="chatStore.loading || uploading"
            :disabled="chatStore.loading || uploading"
            @click="sendMessage"
          >
            {{ uploading ? '上传中...' : '发送' }}
          </el-button>
        </div>
      </div>
      </div> <!-- End chat-content-wrapper -->
    </div>
    </div>

    <!-- 订单选择弹窗 -->
    <OrderSelector v-model="orderSelectorVisible" @select="handleOrderSelect" />
    
    <!-- 支付密码弹窗 -->
    <el-dialog
      v-model="paymentDialogVisible"
      :title="paymentDialogTitle"
      width="400px"
      :close-on-click-modal="false"
      :show-close="!paymentProcessing"
      class="payment-dialog"
    >
      <div class="payment-info">
        <div class="payment-order-no">订单号：{{ paymentData.order_no }}</div>
        <div class="payment-amount">
          <span class="amount-label">支付金额</span>
          <span class="amount-value">¥{{ paymentData.amount?.toFixed(2) }}</span>
        </div>
      </div>
      
      <div class="password-input-section">
        <div class="password-label">请输入6位数字支付密码</div>
        <div class="password-dots">
          <div 
            v-for="i in 6" 
            :key="i" 
            class="password-dot"
            :class="{ filled: paymentPassword.length >= i }"
          >
            <span v-if="paymentPassword.length >= i">●</span>
          </div>
        </div>
        <input
          ref="passwordInputRef"
          v-model="paymentPassword"
          type="number"
          maxlength="6"
          class="password-input"
          @input="handlePasswordInput"
          @keydown="handlePasswordKeydown"
        />
      </div>
      
      <div class="numpad">
        <div 
          v-for="num in [1,2,3,4,5,6,7,8,9]" 
          :key="num"
          class="numpad-key"
          @click="appendPassword(num)"
        >{{ num }}</div>
        <div class="numpad-key disabled"></div>
        <div class="numpad-key" @click="appendPassword(0)">0</div>
        <div class="numpad-key" @click="deletePassword">⌫</div>
      </div>
      
      <template #footer>
        <el-button :disabled="paymentProcessing" @click="closePaymentDialog">取消</el-button>
        <el-button 
          type="primary" 
          :loading="paymentProcessing" 
          :disabled="paymentPassword.length !== 6"
          @click="confirmPayment"
        >
          确认支付
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { Plus, User, ChatDotRound, Document, Paperclip, Delete, Upload, ArrowRight, ArrowDown, Loading, ShoppingBag, Close, Star, Box, Coin, QuestionFilled, Menu, ArrowLeftBold, ArrowRightBold } from '@element-plus/icons-vue'
import { apiClient } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import OrderSelector from '@/components/OrderSelector.vue'

const router = useRouter()
const chatStore = useChatStore()
const cartStore = useCartStore()
const authStore = useAuthStore()
const messageList = computed(() => chatStore.messages)
const inputMessage = ref('')
const thinkingStatus = ref('正在分析文档内容...')
const messageListRef = ref<HTMLElement>()
const selectedFiles = ref<File[]>([])
const uploading = ref(false)
const isDragOver = ref(false)
const sidebarVisible = ref(false)
const isMobileLayout = ref(false)
const historyCollapsed = ref(false)
const expandedThinking = ref<Record<string, boolean>>({})
const orderSelectorVisible = ref(false)
const quickActionIconMap: Record<string, any> = {
  package: Box,
  refund: Coin,
  cart: ShoppingBag,
  help: QuestionFilled
}

const sessionGroups = computed(() => {
  const sortedSessions = [...chatStore.sessions]
    .filter(session => session.message_count > 0)
    .sort((a, b) => {
      const timeA = new Date(a.created_at).getTime()
      const timeB = new Date(b.created_at).getTime()
      return timeB - timeA
    })
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)
  const startOfLast7Days = new Date(startOfToday)
  startOfLast7Days.setDate(startOfLast7Days.getDate() - 6)
  const groups: Record<string, typeof sortedSessions> = {}
  for (const session of sortedSessions) {
    const sessionTime = new Date(session.created_at)
    let label = '更早'
    if (!Number.isNaN(sessionTime.getTime())) {
      if (sessionTime >= startOfToday) {
        label = '今天'
      } else if (sessionTime >= startOfYesterday) {
        label = '昨天'
      } else if (sessionTime >= startOfLast7Days) {
        label = '前7天'
      }
    }
    if (!groups[label]) {
      groups[label] = []
    }
    groups[label].push(session)
  }
  const order = ['今天', '昨天', '前7天', '更早']
  return order
    .filter(label => groups[label]?.length)
    .map(label => ({ label, sessions: groups[label] }))
})

const syncViewport = () => {
  isMobileLayout.value = window.innerWidth <= 980
  if (!isMobileLayout.value) {
    sidebarVisible.value = false
  }
}

const toggleSidebar = () => {
  sidebarVisible.value = !sidebarVisible.value
}

const closeSidebar = () => {
  sidebarVisible.value = false
}

const toggleHistoryPanel = () => {
  if (isMobileLayout.value) {
    toggleSidebar()
    return
  }

  historyCollapsed.value = !historyCollapsed.value
}

// 图片压缩配置
const IMAGE_COMPRESSION_CONFIG = {
  maxWidth: 1920,      // 最大宽度
  maxHeight: 1920,     // 最大高度
  quality: 0.85,       // 压缩质量 (0-1)
  maxSizeMB: 2         // 超过此大小才压缩 (MB)
}

/**
 * 压缩图片
 * @param file 原始图片文件
 * @returns 压缩后的图片文件（如果不需要压缩则返回原文件）
 */
const compressImage = async (file: File): Promise<File> => {
  // 如果不是图片或文件已经很小，直接返回
  if (!file.type.startsWith('image/') || file.size <= IMAGE_COMPRESSION_CONFIG.maxSizeMB * 1024 * 1024) {
    return file
  }

  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    
    img.onload = () => {
      URL.revokeObjectURL(url)
      
      let { width, height } = img
      const { maxWidth, maxHeight, quality } = IMAGE_COMPRESSION_CONFIG
      
      // 计算缩放比例
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height)
        width = Math.floor(width * ratio)
        height = Math.floor(height * ratio)
      }
      
      // 创建 canvas
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      
      if (!ctx) {
        resolve(file) // 压缩失败，返回原文件
        return
      }
      
      // 绘制图片
      ctx.drawImage(img, 0, 0, width, height)
      
      // 转换为 blob
      canvas.toBlob(
        (blob) => {
          if (blob) {
            // 创建新的 File 对象
            const compressedFile = new File([blob], file.name, {
              type: file.type,
              lastModified: file.lastModified
            })
            console.log(`[图片压缩] ${file.name}: ${(file.size / 1024 / 1024).toFixed(2)}MB -> ${(compressedFile.size / 1024 / 1024).toFixed(2)}MB`)
            resolve(compressedFile)
          } else {
            resolve(file) // 压缩失败，返回原文件
          }
        },
        file.type,
        quality
      )
    }
    
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(file) // 加载失败，返回原文件
    }
    
    img.src = url
  })
}

// 支付密码弹窗相关
const paymentDialogVisible = ref(false)
const paymentDialogTitle = ref('支付')
const paymentPassword = ref('')
const paymentProcessing = ref(false)
const passwordInputRef = ref<HTMLInputElement>()
const paymentData = ref<{
  order_id?: string
  order_no?: string
  payment_method?: string
  amount?: number
}>({})

onMounted(() => {
  syncViewport()
  window.addEventListener('resize', syncViewport)

  // 使用 setTimeout 避免阻塞页面渲染
  setTimeout(async () => {
    await chatStore.fetchSessions()
    if (chatStore.sessions.length > 0) {
      await chatStore.selectSession(chatStore.sessions[0].id)
    }
  }, 0)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
})

watch(() => messageList.value.length, () => {
  console.log('消息列表变化:', messageList.value.length)
  nextTick(() => {
    scrollToBottom()
  })
})

const createNewSession = async () => {
  chatStore.resetSession()
  if (isMobileLayout.value) {
    closeSidebar()
  }
}

const selectSession = async (sessionId: string) => {
  await chatStore.selectSession(sessionId)
  if (isMobileLayout.value) {
    closeSidebar()
  }
}


const deleteSession = async (sessionId: string) => {
  const success = await chatStore.deleteSession(sessionId)
  if (success) {
    ElMessage.success('会话已删除')
  } else {
    ElMessage.error('删除失败')
  }
}

// 处理文件选择
const handleFileChange = async (file: any) => {
  let rawFile = file.raw

  // 对图片进行压缩
  if (rawFile.type.startsWith('image/')) {
    rawFile = await compressImage(rawFile)
  }

  // 检查文件大小 (10MB)
  if (rawFile.size > 10 * 1024 * 1024) {
    ElMessage.warning(`文件 ${rawFile.name} 超过10MB限制`)
    return
  }

  // 检查是否已存在
  const exists = selectedFiles.value.some(f => f.name === rawFile.name && f.size === rawFile.size)
  if (!exists) {
    selectedFiles.value.push(rawFile)
  }
}

// 移除文件
const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

// 清除所有文件
const clearFiles = () => {
  selectedFiles.value = []
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 判断是否为图片文件（支持 File 对象或字符串类型）
const isImageFile = (fileOrType: File | string): boolean => {
  if (typeof fileOrType === 'string') {
    return ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(fileOrType.toLowerCase())
  }
  return fileOrType.type?.startsWith('image/') || false
}

// 预览图片
const previewImage = (url: string) => {
  window.open(url, '_blank')
}

// 获取图片URL（带认证token）
const getImageUrl = (fileId: string): string => {
  const token = authStore.token
  return `/api/files/${fileId}?token=${token}`
}

// 获取文件预览URL
const getFilePreviewUrl = (file: File): string => {
  return URL.createObjectURL(file)
}

// 获取显示的文件名（对粘贴的图片显示更友好的名称）
const getDisplayFileName = (file: File): string => {
  if (file.name.startsWith('pasted-image-')) {
    return '粘贴的图片'
  }
  return file.name
}

// 拖拽处理
const handleDragEnter = () => {
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

// 处理粘贴事件
const handlePaste = async (event: ClipboardEvent) => {
  const items = event.clipboardData?.items
  if (!items) return

  let hasImage = false

  for (let i = 0; i < items.length; i++) {
    const item = items[i]

    // 检查是否是图片类型
    if (item.type.indexOf('image') !== -1) {
      hasImage = true
      event.preventDefault() // 阻止默认粘贴行为

      const blob = item.getAsFile()
      if (blob) {
        // 创建 File 对象
        let file = new File([blob], `pasted-image-${Date.now()}.png`, {
          type: blob.type || 'image/png'
        })

        // 压缩图片
        file = await compressImage(file)

        // 检查文件大小 (10MB)
        if (file.size > 10 * 1024 * 1024) {
          ElMessage.warning('粘贴的图片超过10MB限制')
          continue
        }

        // 检查是否已存在
        const exists = selectedFiles.value.some(f => f.name === file.name && f.size === file.size)
        if (!exists) {
          selectedFiles.value.push(file)
          ElMessage.success('图片已粘贴到输入框')
        }
      }
      break
    }
  }

  // 如果不是图片，允许默认粘贴行为（粘贴文本）
  if (!hasImage) {
    return
  }
}

const handleDrop = async (event: DragEvent) => {
  isDragOver.value = false

  const files = event.dataTransfer?.files
  if (files) {
    for (let i = 0; i < files.length; i++) {
      let file = files[i]

      // 对图片进行压缩
      if (file.type.startsWith('image/')) {
        file = await compressImage(file)
      }

      // 检查文件大小 (10MB)
      if (file.size > 10 * 1024 * 1024) {
        ElMessage.warning(`文件 ${file.name} 超过10MB限制`)
        continue
      }

      // 检查是否已存在
      const exists = selectedFiles.value.some(f => f.name === file.name && f.size === file.size)
      if (!exists) {
        selectedFiles.value.push(file)
      }
    }
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() && selectedFiles.value.length === 0) {
    return
  }

  // 防止重复提交
  if (uploading.value || chatStore.loading) {
    return
  }

  // 使用 nextTick 确保 UI 先响应点击事件
  await nextTick()
  
  uploading.value = true

  // 设置思考状态
  if (selectedFiles.value.length > 0) {
    thinkingStatus.value = '正在读取文件内容...'
  } else {
    thinkingStatus.value = '正在思考问题...'
  }

  try {
    let attachments: any[] = []

    if (!chatStore.currentSession?.id) {
      const titleSeed = inputMessage.value.trim() || selectedFiles.value[0]?.name || ''
      await chatStore.createSession(titleSeed)
    }

    // 如果有文件，先上传
    if (selectedFiles.value.length > 0) {
      const uploadTasks = selectedFiles.value.map(file => {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('session_id', chatStore.currentSession?.id || '')

        return apiClient.post('/files/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      })

      const responses = await Promise.all(uploadTasks)
      attachments = responses.map((response: any) => ({
        file_id: response.file_id,
        file_name: response.file_name,
        file_type: response.file_type,
        file_size: response.file_size,
        extracted_text: response.extracted_text || null,  // 视觉LLM提取的文字
        ocr_used: response.ocr_used || false
      }))
    }

    // 保存消息内容并清空输入框（立即执行，不等待流式输出完成）
    const messageContent = inputMessage.value
    inputMessage.value = ''
    
    // 文件上传成功后，立即清空已选择的文件列表
    // 这样用户界面就不会继续显示"已选择 x 个文件"
    selectedFiles.value = []
    uploading.value = false

    // 发送消息（使用流式输出）
    await chatStore.sendMessageStream(messageContent, attachments, (chunk) => {
      console.log('收到内容片段:', chunk)
    })
  } catch (error) {
    console.error('发送失败:', error)
    ElMessage.error('发送失败，请重试')
    uploading.value = false
  }
}

const handleEnterKey = () => {
  // 在 loading 状态下不响应 Enter 键
  if (chatStore.loading || uploading.value) {
    return
  }
  sendMessage()
}

const toggleThinking = (messageId: string) => {
  expandedThinking.value[messageId] = !expandedThinking.value[messageId]
}

const prefillMessage = (message: string) => {
  inputMessage.value = message
  if (isMobileLayout.value) {
    closeSidebar()
  }
  nextTick(() => {
    scrollToBottom()
  })
}

const scrollToBottom = () => {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}

const formatOrderTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}

// 显示订单选择器
const showOrderSelector = () => {
  orderSelectorVisible.value = true
}

// 显示支付密码弹窗
const showPaymentDialog = (data: any) => {
  paymentData.value = data
  paymentDialogTitle.value = data.payment_method === 'wechat' ? '微信支付' : '支付宝'
  paymentPassword.value = ''
  paymentDialogVisible.value = true
  paymentProcessing.value = false
  // 自动聚焦密码输入框
  nextTick(() => {
    passwordInputRef.value?.focus()
  })
}

// 关闭支付密码弹窗
const closePaymentDialog = () => {
  if (paymentProcessing.value) return
  paymentDialogVisible.value = false
  paymentPassword.value = ''
}

// 追加密码数字
const appendPassword = (num: number) => {
  if (paymentPassword.value.length < 6) {
    paymentPassword.value += num.toString()
    // 输入6位后自动提交
    if (paymentPassword.value.length === 6) {
      setTimeout(() => confirmPayment(), 300)
    }
  }
}

// 删除密码最后一位
const deletePassword = () => {
  paymentPassword.value = paymentPassword.value.slice(0, -1)
}

// 处理密码输入
const handlePasswordInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  // 只允许数字
  let value = target.value.replace(/\D/g, '')
  // 最多6位
  if (value.length > 6) {
    value = value.slice(0, 6)
  }
  paymentPassword.value = value
}

// 处理密码键盘事件
const handlePasswordKeydown = (e: KeyboardEvent) => {
  // 阻止非数字键（除了退格、删除、方向键等）
  if (!/^[0-9]$/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
    e.preventDefault()
  }
}

// 确认支付
const confirmPayment = async () => {
  if (paymentPassword.value.length !== 6) {
    ElMessage.warning('请输入6位支付密码')
    return
  }
  
  paymentProcessing.value = true
  
  try {
    // 模拟支付处理
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 支付成功
    ElMessage.success('支付成功！')
    paymentDialogVisible.value = false
    paymentPassword.value = ''
    
    // 发送支付完成消息到后端
    const flowData = {
      action: 'purchase_flow',
      step: 'payment_success',
      order_id: paymentData.value.order_id,
      order_no: paymentData.value.order_no,
      payment_method: paymentData.value.payment_method,
      payment_password: '******' // 实际项目中不应该发送真实密码
    }
    inputMessage.value = `[购买流程] 支付完成`
    chatStore.setPurchaseFlowData(flowData)
    // 使用 setTimeout 避免阻塞 UI
    setTimeout(() => sendMessage(), 0)
  } catch (error) {
    console.error('支付失败:', error)
    ElMessage.error('支付失败，请重试')
  } finally {
    paymentProcessing.value = false
  }
}

// 处理订单选择 - 将订单信息以卡片形式插入到消息中
const handleOrderSelect = async (order: any) => {
  // 显示订单卡片消息
  const orderCardMessage = {
    id: Date.now().toString(),
    role: 'user' as const,
    content: `我要咨询订单 ${order.order_no}`,
    created_at: new Date().toISOString(),
    metadata: {
      order_card: {
        order_no: order.order_no,
        status: getOrderStatusText(order.status),
        product_name: getOrderProductName(order),
        total_amount: (order.total_amount / 100).toFixed(2),
        item_count: order.items?.length || 1
      }
    }
  }
  
  // 添加到消息列表
  chatStore.messages.push(orderCardMessage)
  
  // 直接调用后端API，不通过 sendMessageStream（避免重复添加用户消息）
  const sessionId = chatStore.currentSession?.id
  if (!sessionId) return
  
  chatStore.loading = true
  
  try {
    // 创建AI消息（空内容）
    const assistantMessageId = Date.now().toString() + '_assistant'
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant' as const,
      content: '',
      created_at: new Date().toISOString(),
      metadata: {}
    }
    chatStore.messages.push(assistantMessage)

    // 使用流式API（直连后端，绕过 Vite 代理的 SSE 缓冲）
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: `我要咨询订单 ${order.order_no}`,
        attachments: []
      })
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'intent') {
                const msgIndex = chatStore.messages.findIndex(m => m.id === assistantMessageId)
                if (msgIndex !== -1) {
                  chatStore.messages[msgIndex].metadata = { ...chatStore.messages[msgIndex].metadata, intent: data.intent }
                }
              } else if (data.type === 'thinking') {
                const msgIndex = chatStore.messages.findIndex(m => m.id === assistantMessageId)
                if (msgIndex !== -1) {
                  chatStore.messages[msgIndex].metadata = { ...chatStore.messages[msgIndex].metadata, thinking: data.content }
                }
              } else if (data.type === 'content') {
                fullContent += data.delta
                const msgIndex = chatStore.messages.findIndex(m => m.id === assistantMessageId)
                if (msgIndex !== -1) {
                  chatStore.messages[msgIndex].content = fullContent
                }
              } else if (data.type === 'end') {
                const msgIndex = chatStore.messages.findIndex(m => m.id === assistantMessageId)
                if (msgIndex !== -1) {
                  chatStore.messages[msgIndex].metadata = { 
                    ...chatStore.messages[msgIndex].metadata, 
                    sources: data.sources,
                    quick_actions: data.quick_actions
                  }
                }
              }
            } catch (e) {
              console.error('解析流式数据失败:', e)
            }
          }
        }
      }
    }

    // 更新会话列表
    await chatStore.fetchSessions()
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送失败，请重试')
  } finally {
    chatStore.loading = false
  }
}

const getOrderStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    shipped: '已发货',
    delivered: '已送达',
    completed: '已完成',
    cancelled: '已取消',
    refunded: '已退款'
  }
  return statusMap[status] || '未知'
}

const getOrderProductName = (order: any) => {
  if (!order.items || !Array.isArray(order.items) || order.items.length === 0) {
    return '茶品'
  }
  return order.items[0]?.product_title || '茶品'
}

// 处理快速操作按钮点击
const handleQuickAction = async (action: any) => {
  console.log('=== 快速操作 ===')
  console.log('action.type:', action.type)
  console.log('action.action:', action.action)
  console.log('完整action:', action)
  
  if (action.type === 'product') {
    // 商品卡片 - 跳转到商品详情
    if (action.data?.product_id) {
      window.open(`/products/${action.data.product_id}`, '_blank')
    }
  } else if (action.type === 'address') {
    // 地址卡片 - 选择该地址进入确认步骤
    const flowData = {
      action: 'purchase_flow',
      step: 'confirm_address',
      product_id: action.data?.product_id,
      coupon_id: action.data?.coupon_id,
      address_id: action.data?.address_id,
      final_price: action.data?.final_price
    }
    inputMessage.value = `[购买流程] 选择地址：${action.data?.contact}`
    chatStore.setPurchaseFlowData(flowData)
    setTimeout(() => sendMessage(), 0)
  } else if (action.type === 'coupon') {
    // 优惠券卡片 - 选择该优惠券
    const flowData = {
      action: 'purchase_flow',
      step: 'confirm_coupon',
      product_id: action.data?.product_id || chatStore.purchaseFlowData?.product_id,
      coupon_id: action.data?.coupon_id
    }
    inputMessage.value = `[购买流程] 使用优惠券：${action.data?.name}`
    chatStore.setPurchaseFlowData(flowData)
    setTimeout(() => sendMessage(), 0)
  } else if (action.type === 'order_card_simple' || action.type === 'order_card') {
    // 订单卡片 - 直接发送订单信息（只发送一条消息）
    console.log('点击了订单卡片:', action.type)
    const messageContent = `我要咨询订单 ${action.data.order_no}`
    
    // 直接调用 sendMessageStream，它会自动添加消息到列表
    setTimeout(async () => {
      await chatStore.sendMessageStream(messageContent, [], (chunk) => {
        console.log('收到内容片段:', chunk)
      })
    }, 0)
  } else if (action.type === 'button') {
    // 普通按钮 - 根据action类型处理
    console.log('点击了普通按钮, action.action:', action.action)
    if (action.action === 'send_question' && action.data?.question) {
      // 发送预设问题
      inputMessage.value = action.data.question
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'select_order') {
      // 选择订单 - 发送订单信息
      const orderNo = action.data?.order_no || ''
      inputMessage.value = `我要咨询订单 ${orderNo}`
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'open_order_selector') {
      // 打开订单选择弹窗
      console.log('打开订单选择弹窗')
      orderSelectorVisible.value = true
    } else if (action.action === 'cancel_order') {
      const orderNo = action.data?.order_no
      if (!orderNo) {
        ElMessage.error('订单信息不完整，暂时无法取消')
        return
      }

      try {
        await ElMessageBox.confirm(`确认取消订单 ${orderNo} 吗？`, '取消订单', {
          confirmButtonText: '确认取消',
          cancelButtonText: '返回',
          type: 'warning'
        })
      } catch (error) {
        if (error !== 'cancel' && error !== 'close') {
          ElMessage.error('取消操作未完成，请重试')
        }
        return
      }

      inputMessage.value = `取消订单 ${orderNo}`
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'navigate') {
      // 页面跳转
      const path = action.data?.path
      if (path) {
        router.push(path)
      }
    } else if (action.action === 'view_all_recommendations') {
      inputMessage.value = '查看全部推荐'
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'refresh_recommendations') {
      inputMessage.value = '换一批推荐'
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'add_to_cart') {
      // 加入购物车
      const productId = action.data?.product_id
      const productTitle = action.data?.product?.title || '茶品'
      if (productId) {
        try {
          await cartStore.addToCart(productId, 1)
          ElMessage.success(`已将 "${productTitle}" 加入购物车`)
        } catch (error) {
          ElMessage.error('加入购物车失败，请重试')
        }
      }
    } else if (action.action === 'purchase_flow') {
      // 购买流程 - 发送带有 action 的消息
      const step = action.data?.step
      
      // 如果是支付步骤，直接显示支付弹框，不发送消息到后端
      if (step === 'payment_done' && action.data?.order_id) {
        const paymentData = {
          order_id: action.data.order_id,
          order_no: action.data.order_no,
          payment_method: action.data.payment_method || 'wechat',
          amount: action.data.final_price || 0
        }
        // 保存当前流程数据供支付成功后使用
        chatStore.setPurchaseFlowData({
          action: 'purchase_flow',
          step: 'payment_done',
          ...action.data
        })
        // 直接显示支付弹框
        showPaymentDialog(paymentData)
        return
      }
      
      const flowData = {
        action: 'purchase_flow',
        step: step || 'start',
        product_id: action.data?.product_id,
        coupon_id: action.data?.coupon_id,
        address_id: action.data?.address_id,
        order_id: action.data?.order_id,
        product: action.data?.product,
        coupon: action.data?.coupon,
        address: action.data?.address,
        final_price: action.data?.final_price,
        order_no: action.data?.order_no
      }
      inputMessage.value = `[购买流程] ${action.label || '确认'}`
      chatStore.setPurchaseFlowData(flowData)
      // 使用 setTimeout 避免阻塞 UI
      setTimeout(() => sendMessage(), 0)
    } else if (action.action === 'aftersales_flow') {
      // 售后流程
      const step = action.data?.step
      if (step === 'cancel') {
        // 取消售后
        inputMessage.value = '取消售后申请'
        setTimeout(() => sendMessage(), 0)
        return
      }
      const flowData = {
        action: 'aftersales_flow',
        step: step || 'select_order',
        order_id: action.data?.order_id,
        order_no: action.data?.order_no,
        status: action.data?.status,
        product_name: action.data?.product_name,
        total_amount: action.data?.total_amount,
        items: action.data?.items,
        refund_type: action.data?.refund_type,
        reason: action.data?.reason,
        description: action.data?.description,
        refund_amount: action.data?.refund_amount,
      }
      inputMessage.value = `[售后流程] ${action.label || '确认'}`
      chatStore.setAftersalesFlowData(flowData)
      setTimeout(() => sendMessage(), 0)
    } else if (action.data?.question) {
      // 兼容旧格式
      inputMessage.value = action.data.question
      sendMessage()
    }
  } else if (action.type === 'link') {
    // 链接 - 打开URL
    if (action.data?.url) {
      window.open(action.data.url, '_blank')
    }
  } else if (action.type === 'payment_password') {
    // 支付密码输入 - 显示支付弹窗
    console.log('显示支付密码弹窗:', action.data)
    showPaymentDialog(action.data)
  }
}
</script>

<style scoped>
.chat-container {
  /* ==================================================
     Modern Tech Blue Theme
     Clean, professional, and trustworthy AI assistant
     ================================================== */
  
  /* Primary Colors - Tech Blue */
  --primary: #2F6B4F;
  --primary-light: #4A8B68;
  --primary-dark: #24523D;
  --primary-lighter: rgba(37, 99, 235, 0.08);
  
  /* Accent Colors - Violet */
  --accent: #8B633E;
  --accent-light: #8B5CF6;
  
  /* Text Colors - Slate */
  --text: #0F172A;
  --text-secondary: #334155;
  --text-muted: #64748B;
  --text-light: #94A3B8;
  
  /* Borders & Surfaces */
  --border: rgba(226, 232, 240, 0.8);
  --border-strong: rgba(203, 213, 225, 0.8);
  --surface-2: rgba(255, 255, 255, 0.9);
  --surface-3: #F8FAFC;
  --surface-hover: #F1F5F9;
  
  /* Utilities */
  --muted: #64748B;
  --danger: #EF4444;
  --danger-dark: #B91C1C;
  --success: #10B981;
  --warning: #F59E0B;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);

  /* Element Plus Overrides */
  --el-color-primary: var(--primary);
  --el-color-primary-light-3: #60A5FA;
  --el-color-primary-light-5: #93C5FD;
  --el-color-primary-light-7: #BFDBFE;
  --el-color-primary-light-8: #DBEAFE;
  --el-color-primary-light-9: #EFF6FF;
  --el-color-primary-dark-2: #1E40AF;
  
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  min-height: 100dvh;
  position: relative;
  isolation: isolate;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 40%),
    radial-gradient(circle at bottom left, rgba(124, 58, 237, 0.08), transparent 40%),
    linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%);
  padding: clamp(10px, 1.2vw, 18px);
  overflow: hidden;
}

.chat-container::before,
.chat-container::after {
  content: '';
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(60px);
  z-index: 0;
}

.chat-container::before {
  width: 500px;
  height: 500px;
  top: -200px;
  right: -100px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15), rgba(255, 255, 255, 0));
}

.chat-container::after {
  width: 400px;
  height: 400px;
  left: -150px;
  bottom: -150px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.1), rgba(255, 255, 255, 0));
}

.chat-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(12, 18, 28, 0.48);
  backdrop-filter: blur(8px);
  z-index: 25;
}

.chat-shell {
  display: flex;
  height: 100%;
  min-height: 0;
  position: relative;
  z-index: 1;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  box-shadow:
    0 20px 40px rgba(0, 0, 0, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.chat-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(110deg, rgba(255, 255, 255, 0.4), rgba(255, 255, 255, 0) 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0));
  pointer-events: none;
}

.sidebar {
  width: 300px;
  min-height: 0;
  position: relative;
  z-index: 1;
  background: rgba(248, 250, 252, 0.8);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.5);
  transition: width 0.24s ease, opacity 0.18s ease, transform 0.28s ease;
}

.chat-shell.sidebar-collapsed .sidebar {
  width: 0;
  min-width: 0;
  border-right: none;
  opacity: 0;
  pointer-events: none;
}

.chat-shell.sidebar-collapsed .sidebar > * {
  opacity: 0;
}

.sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 18px 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0));
}

.sidebar-title h3 {
  margin: 6px 0 8px;
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.02em;
}

.sidebar-title p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.sidebar-kicker {
  display: inline-flex;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--primary-lighter);
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.1);
}

.sidebar-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar-collapse {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
}

.sidebar-collapse:hover {
  color: var(--primary);
  border-color: var(--primary-light);
  background: white;
}

.sidebar-toolbar {
  padding: 0 18px 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-toolbar :deep(.el-button--primary) {
  height: 46px;
  border: none;
  border-radius: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
}

.sidebar-toolbar :deep(.el-button--primary:hover) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.3);
}

.session-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
}

.session-list::-webkit-scrollbar,
.message-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track,
.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb,
.message-list::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 999px;
}

.session-list-empty {
  padding: 18px;
  border-radius: 20px;
  background: white;
  border: 1px dashed var(--border-strong);
}

.session-list-empty strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text);
  font-size: 14px;
}

.session-list-empty p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.session-group {
  margin-bottom: 10px;
}

.session-group-title {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.1em;
  padding: 8px 12px 6px;
  font-weight: 700;
  text-transform: uppercase;
}

.session-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  cursor: pointer;
  border-radius: 14px;
  transition: all 0.2s ease;
  position: relative;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--border);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.session-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: var(--primary);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-delete-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.session-item:hover .session-delete-btn {
  opacity: 1;
}

.session-item:hover {
  background: var(--surface-hover);
  border-color: var(--primary-light);
  transform: translateX(2px);
}

.session-item.active {
  background: var(--primary-lighter);
  color: var(--primary);
  border-color: var(--primary-light);
}

.session-item:hover::before,
.session-item.active::before {
  opacity: 1;
}

.session-title {
  font-weight: 700;
  margin-bottom: 4px;
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-info {
  font-size: 11px;
  color: var(--text-muted);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: transparent;
  overflow: hidden;
}

/* Chat Content Wrapper */
.chat-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  transition: all 0.3s ease;
}

.chat-main.is-new-chat .chat-content-wrapper {
  justify-content: center;
  align-items: center;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.chat-main.is-new-chat .message-list {
  flex: 0 0 auto;
  overflow: visible;
  padding: 0;
  background: transparent;
  width: 100%;
}

.chat-main.is-new-chat .message-list::before {
  display: none;
}

.chat-main.is-new-chat .conversation-empty {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0 0 40px;
  margin: 0;
}

.chat-main.is-new-chat .input-area {
  width: 100%;
  border: none;
  background: transparent;
  padding: 0 20px;
}

.chat-main.is-new-chat .input-area-inner {
  background: white;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
}

.chat-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.sidebar-toggle {
  display: inline-flex;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: white;
  flex-shrink: 0;
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
}

.sidebar-toggle:hover {
  color: var(--primary);
  border-color: var(--primary-light);
}

.chat-header-copy {
  min-width: 0;
}

.chat-kicker {
  display: inline-flex;
  margin-bottom: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-lighter);
  color: var(--primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.chat-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.01em;
}

.chat-header p {
  margin: 2px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-stat {
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.chat-header-actions :deep(.el-button) {
  height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  border-color: var(--border-strong);
  font-weight: 600;
}

.chat-header-actions :deep(.el-button:hover) {
  color: var(--primary);
  border-color: var(--primary-light);
}

.message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  position: relative;
  padding: 24px 20px;
  background: #F8FAFC;
}

.message-list-inner {
  max-width: 900px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.conversation-empty {
  padding: 40px;
  margin-bottom: 24px;
  border-radius: 24px;
  background: white;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  text-align: center;
}

.empty-badge {
  display: inline-flex;
  padding: 8px 16px;
  border-radius: 999px;
  background: var(--primary-lighter);
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.conversation-empty h4 {
  margin: 20px 0 10px;
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
}

.conversation-empty p {
  margin: 0 auto;
  max-width: 500px;
  color: var(--text-muted);
  line-height: 1.6;
}

.empty-suggestions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

.suggestion-chip {
  padding: 10px 20px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: white;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-chip:hover {
  background: var(--primary-lighter);
  color: var(--primary);
  border-color: var(--primary-light);
  transform: translateY(-1px);
}

.message-item {
  display: flex;
  width: 100%;
  max-width: min(820px, calc(100% - 16px));
  margin-bottom: 24px;
  gap: 16px;
  align-items: flex-start;
}

.message-item.assistant,
.message-item.system {
  margin-right: auto;
}

.message-item.user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  font-size: 18px;
  flex-shrink: 0;
  color: var(--primary);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.message-item.user .message-avatar {
  background: var(--primary);
  color: white;
  border: none;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
}

.message-content {
  position: relative;
  max-width: min(780px, calc(100% - 56px));
  background: white;
  padding: 16px 20px;
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.message-item.assistant .message-content,
.message-item.system .message-content {
  border-top-left-radius: 4px;
}

.message-item.user .message-content {
  background: var(--primary);
  color: white;
  border: none;
  border-top-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}

.message-text {
  line-height: 1.75;
  font-size: 15px;
  color: var(--text);
}

.message-item.user .message-text {
  color: white;
}

.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(p + p) {
  margin-top: 12px;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 10px 0;
  padding-left: 20px;
}

.message-text :deep(li) {
  margin: 6px 0;
}

.message-item.user .message-text {
  white-space: pre-wrap;
}

.message-item.assistant .message-text,
.message-item.system .message-text {
  white-space: normal;
  color: var(--text);
}

.message-attachments {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text);
  margin-top: 4px;
  padding: 8px 12px;
  background: var(--surface-hover);
  border-radius: 10px;
  border: 1px solid var(--border);
}

.message-item.user .message-attachments {
  border-top-color: rgba(255, 255, 255, 0.2);
}

.message-item.user .attachment-item {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: white;
}

/* 图片附件样式 */
.attachment-item.is-image {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
}

.attachment-image-preview {
  width: 200px;
  max-height: 150px;
  object-fit: cover;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid var(--border);
}

.message-item.user .attachment-image-preview {
  border-color: rgba(255, 255, 255, 0.2);
}

.attachment-image-preview:hover {
  transform: scale(1.02);
  box-shadow: var(--shadow);
}

.message-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  letter-spacing: 0.05em;
}

.message-item.user .message-time {
  color: rgba(255, 255, 255, 0.7);
}

/* 用户发送的订单卡片样式 */
.user-order-card {
  margin-top: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}

.user-order-card .order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.2);
}

.user-order-card .order-no {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  font-family: monospace;
}

.user-order-card .order-status {
  font-size: 12px;
  padding: 2px 8px;
  background: white;
  border-radius: 4px;
  color: var(--primary);
  font-weight: 600;
}

.user-order-card .order-card-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-order-card .product-name {
  font-size: 14px;
  font-weight: 500;
  color: white;
}

.user-order-card .order-amount {
  font-size: 14px;
  font-weight: 600;
  color: white;
}

/* 快速操作按钮样式 */
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text);
  font-size: 14px;
  box-shadow: var(--shadow-sm);
}

.quick-action-item:hover {
  transform: translateY(-1px);
  background: var(--surface-hover);
  border-color: var(--primary-light);
  box-shadow: var(--shadow);
}

/* 订单卡片样式 */
.quick-action-item.order_card,
.quick-action-item.order_card_simple {
  padding: 16px;
  background: white;
}

/* 简洁订单卡片内容 */
.order-card-simple-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-card-simple-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.order-no-simple {
  font-size: 12px;
  color: var(--muted);
  font-family: monospace;
}

.order-status-simple {
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.order-status-simple.status-pending {
  background: rgba(251, 191, 36, 0.1);
  color: #d97706;
}

.order-status-simple.status-paid {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.order-status-simple.status-shipped {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.order-status-simple.status-delivered,
.order-status-simple.status-completed {
  background: rgba(168, 85, 247, 0.1);
  color: #9333ea;
}

.order-status-simple.status-cancelled {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.order-card-simple-body {
  padding: 4px 0;
}

.product-name-simple {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.order-card-simple-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-amount-simple {
  font-size: 16px;
  font-weight: 700;
  color: var(--danger);
}

.order-time-simple {
  font-size: 12px;
  color: var(--muted);
}

/* 原订单卡片样式 */
.order-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-no {
  font-size: 13px;
  color: var(--muted);
  font-family: monospace;
}

.order-status {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.order-status.status-pending {
  background: rgba(251, 191, 36, 0.1);
  color: #d97706;
}

.order-status.status-paid {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.order-status.status-shipped {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.order-status.status-delivered,
.order-status.status-completed {
  background: rgba(168, 85, 247, 0.1);
  color: #9333ea;
}

.order-status.status-cancelled {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.order-status.status-refunded {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.order-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.product-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.item-count {
  font-size: 12px;
  color: var(--muted);
  padding: 2px 8px;
  background: var(--surface-hover);
  border-radius: 4px;
}

.order-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-amount {
  font-size: 16px;
  font-weight: 700;
  color: var(--danger);
}

.order-time {
  font-size: 12px;
  color: var(--muted);
}

/* 地址卡片样式 */
.quick-action-item.address {
  padding: 14px 16px;
  background: #F8FAFC;
  border: 1px solid var(--border);
}

.quick-action-item.address:hover {
  background: white;
  border-color: var(--primary-light);
}

.address-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.address-card-contact {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.address-card-detail {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.4;
}

/* 优惠券卡片样式 */
.quick-action-item.coupon {
  padding: 14px 16px;
  background: rgba(251, 191, 36, 0.05);
  border: 1px solid rgba(251, 191, 36, 0.2);
}

.quick-action-item.coupon:hover {
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.4);
}

.coupon-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coupon-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.coupon-card-info {
  font-size: 12px;
  color: var(--muted);
}

/* 售后卡片样式 */
.quick-action-item.refund_card {
  padding: 14px 16px;
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.quick-action-item.refund_card:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
}

.refund-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.refund-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.refund-no {
  font-size: 13px;
  color: var(--muted);
  font-family: monospace;
}

.refund-status {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.refund-status.status-pending {
  background: rgba(251, 191, 36, 0.1);
  color: #d97706;
}

.refund-status.status-approved {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.refund-status.status-rejected {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.refund-status.status-returning {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.refund-status.status-refunding {
  background: rgba(168, 85, 247, 0.1);
  color: #9333ea;
}

.refund-status.status-completed {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.refund-status.status-cancelled {
  background: rgba(148, 163, 184, 0.1);
  color: #64748b;
}

.refund-card-body {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refund-type {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.refund-product {
  font-size: 13px;
  color: var(--muted);
}

.refund-card-footer {
  display: flex;
  align-items: center;
}

.refund-amount {
  font-size: 15px;
  font-weight: 700;
  color: var(--danger);
}

/* 商品卡片样式 */
.quick-action-item.product {
  background: rgba(59, 130, 246, 0.04);
  border-color: rgba(59, 130, 246, 0.2);
  flex-direction: column;
  align-items: flex-start;
  padding: 16px;
  gap: 8px;
}

.quick-action-item.product:hover {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.4);
}

.product-card-content {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.product-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  line-height: 1.4;
}

.product-card-price {
  font-size: 16px;
  font-weight: 700;
  color: var(--danger);
  margin-left: 12px;
}

.product-card-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  color: var(--muted);
}

.product-card-rating {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--warning);
}

.product-card-rating .rating-icon {
  font-size: 14px;
}

.product-card-sales {
  color: var(--muted);
}

.product-card-tech {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.product-card-tech span {
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
  font-size: 12px;
  color: var(--primary);
}

.product-card-desc {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
  margin-top: 4px;
}

.action-icon {
  font-size: 18px;
  flex-shrink: 0;
  color: var(--primary);
}

.action-label {
  flex: 1;
  font-weight: 500;
}

.action-arrow {
  font-size: 16px;
  color: var(--muted);
  transition: transform 0.3s ease;
}

.quick-action-item:hover .action-arrow {
  transform: translateX(4px);
  color: var(--primary);
}

.selected-files {
  padding: 10px 20px;
  border-top: 1px solid var(--border);
  background: rgba(248, 250, 252, 0.8);
  flex-shrink: 0;
}

.selected-files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.file-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: white;
  border-radius: 999px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
  border: 1px solid var(--border);
  color: var(--text);
}

.file-tag:hover {
  box-shadow: var(--shadow);
  border-color: var(--primary-light);
}

/* 图片预览样式 */
.file-item {
  display: inline-block;
}

.image-preview-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.image-preview-item:hover {
  box-shadow: var(--shadow);
  border-color: var(--primary-light);
}

.preview-image {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.image-preview-item .file-name {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-preview-item .remove-icon {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  background: var(--danger);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transition: all 0.2s ease;
}

.image-preview-item .remove-icon:hover {
  transform: scale(1.1);
  background: var(--danger-dark);
}

.input-area {
  display: flex;
  padding: 16px 20px 20px;
  background: white;
  align-items: center;
  position: relative;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.input-area.drag-over {
  background: var(--primary-lighter);
  border: 2px dashed var(--primary);
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}

.drag-overlay .el-icon {
  color: var(--primary);
  margin-bottom: 8px;
  font-size: 32px;
}

.drag-overlay span {
  color: var(--text);
  font-size: 14px;
}

.upload-btn {
  flex-shrink: 0;
}

.input-area-inner {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  width: 100%;
  max-width: min(1120px, 100%);
  margin: 0 auto;
  padding: 12px;
  border-radius: 16px;
  background: #F8FAFC;
  border: 1px solid var(--border);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
}

.upload-btn :deep(.el-button) {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: white;
  border: 1px solid var(--border);
  color: var(--text-muted);
  box-shadow: var(--shadow-sm);
}

.order-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: white;
  border: 1px solid var(--border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.upload-btn :deep(.el-button:hover),
.order-btn:hover {
  background: white;
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-1px);
}

.input-area :deep(.el-textarea__inner) {
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.55;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  min-height: 40px !important;
  max-height: 120px;
  box-shadow: none;
}

.input-area :deep(.el-textarea__inner::placeholder) {
  color: var(--text-light);
}

.input-area :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.input-area :deep(.el-button--primary) {
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  background: var(--primary);
  border: none;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
}

.input-area :deep(.el-button--primary:hover) {
  background: var(--primary-light);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.3);
}

.input-area :deep(.el-button--primary:active) {
  background: var(--primary-dark);
}

/* 思考面板样式 */
.thinking-panel {
  background: #F8FAFC;
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
  border-bottom: 1px solid transparent;
}

.thinking-header:hover {
  background: #F1F5F9;
}

.thinking-icon {
  font-size: 16px;
  color: var(--primary);
  transition: transform 0.3s ease;
}

.thinking-icon.loading {
  animation: spin 1s linear infinite;
  color: var(--primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.thinking-title {
  font-size: 14px;
  color: var(--text);
  font-weight: 600;
}

.thinking-time {
  font-size: 12px;
  color: var(--muted);
  margin-left: auto;
  background: rgba(59, 130, 246, 0.1);
  padding: 4px 10px;
  border-radius: 999px;
}

.thinking-content {
  padding: 16px;
  border-top: 1px solid var(--border);
  background: #F8FAFC;
}

.thinking-content pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'JetBrains Mono', 'Fira Code', 'Monaco', monospace;
}

/* 思考动画 */
.thinking-dots {
  display: inline-flex;
  margin-left: 4px;
}

.thinking-dots .dot {
  animation: thinking-bounce 1.4s infinite ease-in-out both;
  color: var(--primary);
}

.thinking-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes thinking-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.thinking-status {
  font-size: 12px;
  color: var(--muted);
  margin-top: 8px;
  font-style: italic;
}

/* 支付密码弹窗样式 */
.payment-dialog :deep(.el-dialog__header) {
  background: white;
  border-bottom: 1px solid var(--border);
  padding: 20px 24px;
  margin-right: 0;
  border-radius: 16px 16px 0 0;
}

.payment-dialog :deep(.el-dialog__title) {
  color: var(--text);
  font-weight: 600;
  font-size: 18px;
}

.payment-dialog :deep(.el-dialog__body) {
  padding: 24px;
  background: white;
}

.payment-dialog :deep(.el-dialog__footer) {
  background: #F8FAFC;
  border-top: 1px solid var(--border);
  padding: 16px 24px;
  border-radius: 0 0 16px 16px;
}

.payment-info {
  text-align: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}

.payment-order-no {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 12px;
  font-family: monospace;
}

.payment-amount {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.amount-label {
  font-size: 14px;
  color: var(--muted);
}

.amount-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--text);
}

.password-input-section {
  margin-bottom: 24px;
}

.password-label {
  text-align: center;
  font-size: 14px;
  color: var(--text);
  margin-bottom: 16px;
}

.password-dots {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.password-dot {
  width: 48px;
  height: 48px;
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--text);
  background: #F8FAFC;
  transition: all 0.2s ease;
}

.password-dot.filled {
  border-color: var(--primary);
  background: rgba(37, 99, 235, 0.05);
  color: var(--primary);
}

.password-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.numpad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  max-width: 280px;
  margin: 0 auto;
}

.numpad-key {
  aspect-ratio: 1.5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  background: white;
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.numpad-key:hover:not(.disabled) {
  background: #F8FAFC;
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.numpad-key:active:not(.disabled) {
  transform: translateY(0);
}

.numpad-key.disabled {
  cursor: default;
  background: transparent;
  border-color: transparent;
}

@media (max-width: 1180px) {
  .chat-container {
    padding: 14px;
  }

  .sidebar {
    width: 280px;
  }

  .chat-header-actions {
    display: none;
  }
}

@media (max-width: 980px) {
  .chat-container {
    padding: 12px;
  }

  .sidebar-toggle,
  .sidebar-collapse {
    display: inline-flex;
  }

  .chat-shell {
    border-radius: 22px;
  }

  .sidebar {
    position: fixed;
    top: 12px;
    left: 12px;
    bottom: 12px;
    width: min(84vw, 320px);
    z-index: 26;
    background: rgba(255, 252, 247, 0.92);
    border-right: none;
    border: 1px solid var(--border);
    border-radius: 24px;
    backdrop-filter: blur(18px);
    transform: translateX(-120%);
    transition: transform 0.28s ease;
    box-shadow: var(--shadow-lg);
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .chat-shell.sidebar-collapsed .sidebar {
    width: min(84vw, 320px);
  }

  .chat-shell.sidebar-collapsed .sidebar > * {
    opacity: 1;
  }

  .chat-main {
    border-radius: 0;
  }

  .chat-header {
    padding: 16px 18px;
  }

  .chat-header h3 {
    font-size: 18px;
  }

  .message-list,
  .selected-files,
  .input-area {
    padding-left: 16px;
    padding-right: 16px;
  }

  .message-content {
    max-width: calc(100% - 54px);
  }
}

@media (max-width: 640px) {
  .conversation-empty {
    padding: 22px 18px;
    border-radius: 22px;
  }

  .conversation-empty h4 {
    font-size: 22px;
  }

  .empty-suggestions {
    flex-direction: column;
  }

  .suggestion-chip {
    width: 100%;
    text-align: left;
  }

  .message-list {
    padding-top: 18px;
  }

  .message-item {
    margin-bottom: 16px;
  }

  .message-avatar {
    width: 34px;
    height: 34px;
    margin: 0 8px;
  }

  .selected-files {
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .input-area {
    padding: 14px 12px 18px;
  }

  .input-area-inner {
    gap: 8px;
    padding: 10px;
    border-radius: 20px;
  }

  .upload-btn :deep(.el-button),
  .order-btn,
  .input-area :deep(.el-button--primary) {
    height: 42px;
  }

  .input-area :deep(.el-button--primary) {
    padding: 0 16px;
  }

  .payment-dialog :deep(.el-dialog) {
    width: calc(100vw - 24px) !important;
    margin-top: 8vh !important;
  }

  .password-dots {
    gap: 8px;
  }

  .password-dot {
    width: 40px;
    height: 40px;
  }
}

@media (max-height: 860px) {
  .chat-container {
    padding: 10px;
  }

  .sidebar-header {
    padding-top: 16px;
    padding-bottom: 10px;
  }

  .sidebar-title p {
    display: none;
  }

  .sidebar-toolbar {
    padding-bottom: 10px;
  }

  .chat-header {
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .message-list {
    padding-top: 14px;
    padding-bottom: 12px;
  }

  .conversation-empty {
    padding: 20px;
  }

  .input-area {
    padding-top: 10px;
    padding-bottom: 12px;
  }

  .input-area-inner {
    padding: 8px;
  }
}
</style>
