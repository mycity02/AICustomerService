import { defineStore } from 'pinia'
import { ref } from 'vue'

import { apiClient } from '@/api/client'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  metadata?: any
  attachments?: any[]
}

interface Session {
  id: string
  title: string
  created_at: string
  message_count: number
}

const WELCOME_TEXT = 'Hi，我是智能客服小助手，请问有什么可以帮您？'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const purchaseFlowData = ref<any>(null)
  const aftersalesFlowData = ref<any>(null)

  const sanitizeAttachments = (attachments?: any[]) =>
    attachments?.map(attachment => ({
      file_id: attachment.file_id,
      file_name: attachment.file_name,
      file_type: attachment.file_type,
      file_size: attachment.file_size,
      extracted_text: attachment.extracted_text ?? null,
      ocr_used: attachment.ocr_used ?? false,
      image_intent: attachment.image_intent ?? null,
      image_description: attachment.image_description ?? null
    })) ?? []

  const buildSessionTitle = (seed?: string, attachments?: any[]) => {
    const trimmed = seed?.replace(/\s+/g, ' ').trim()
    if (trimmed) {
      return trimmed.length > 20 ? `${trimmed.slice(0, 20)}...` : trimmed
    }

    const firstAttachmentName = attachments?.[0]?.file_name as string | undefined
    if (firstAttachmentName) {
      const baseName = firstAttachmentName.replace(/\.[^/.]+$/, '')
      const normalized = baseName.replace(/\s+/g, ' ').trim()
      if (normalized) {
        return normalized.length > 20 ? `${normalized.slice(0, 20)}...` : normalized
      }
    }

    const now = new Date()
    const month = (now.getMonth() + 1).toString().padStart(2, '0')
    const day = now.getDate().toString().padStart(2, '0')
    const hours = now.getHours().toString().padStart(2, '0')
    const minutes = now.getMinutes().toString().padStart(2, '0')
    return `新对话 ${month}-${day} ${hours}:${minutes}`
  }

  const appendWelcomeMessage = () => {
    const welcomeMessage: Message = {
      id: `welcome_${Date.now()}`,
      role: 'assistant',
      content: WELCOME_TEXT,
      created_at: new Date().toISOString(),
      metadata: { quick_actions: [] }
    }
    messages.value = [welcomeMessage]
    loadSmartQuestions(welcomeMessage.id)
  }

  const refreshSessions = async () => {
    const updatedSessions = await apiClient.get<Session[]>('/chat/sessions')
    sessions.value = updatedSessions
    if (currentSession.value) {
      const updatedCurrentSession = updatedSessions.find(session => session.id === currentSession.value?.id)
      if (updatedCurrentSession) {
        currentSession.value = { ...currentSession.value, ...updatedCurrentSession }
      }
    }
  }

  async function fetchSessions() {
    try {
      sessions.value = await apiClient.get<Session[]>('/chat/sessions')
    } catch (error) {
      console.error('获取会话列表失败:', error)
    }
  }

  async function createSession(title?: string) {
    try {
      const session = await apiClient.post<Session>('/chat/session', {
        title: buildSessionTitle(title)
      })
      sessions.value.unshift(session)
      currentSession.value = session
      appendWelcomeMessage()
      return session
    } catch (error) {
      console.error('创建会话失败:', error)
      return null
    }
  }

  async function deleteSession(sessionId: string) {
    try {
      await apiClient.post(`/chat/session/${sessionId}/delete`)
      sessions.value = sessions.value.filter(session => session.id !== sessionId)
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null
        messages.value = []
      }
      return true
    } catch (error) {
      console.error('删除会话失败:', error)
      return false
    }
  }

  async function selectSession(sessionId: string) {
    try {
      const session = sessions.value.find(item => item.id === sessionId)
      if (!session) {
        return
      }

      currentSession.value = session
      await fetchMessages(sessionId)
      if (messages.value.length === 0) {
        appendWelcomeMessage()
      }
    } catch (error) {
      console.error('选择会话失败:', error)
    }
  }

  async function fetchMessages(sessionId: string) {
    try {
      messages.value = await apiClient.get<Message[]>(`/chat/session/${sessionId}/messages`)
    } catch (error) {
      console.error('获取消息失败:', error)
    }
  }

  async function sendMessage(content: string, attachments?: any[]) {
    let sessionId = currentSession.value?.id
    const safeAttachments = sanitizeAttachments(attachments)

    if (!sessionId) {
      const newSession = await createSession(buildSessionTitle(content, safeAttachments))
      if (!newSession) {
        return
      }
      sessionId = newSession.id
    }

    loading.value = true
    try {
      messages.value = [
        ...messages.value,
        {
          id: Date.now().toString(),
          role: 'user',
          content,
          created_at: new Date().toISOString(),
          attachments: safeAttachments
        }
      ]

      const response = await apiClient.post<any>('/chat/message', {
        session_id: sessionId,
        message: content,
        attachments: safeAttachments,
        purchase_flow: purchaseFlowData.value,
        aftersales_flow: aftersalesFlowData.value
      })

      messages.value = [
        ...messages.value,
        {
          id: response.message_id,
          role: 'assistant',
          content: response.content,
          created_at: new Date().toISOString(),
          metadata: {
            intent: response.intent,
            sources: response.sources,
            quick_actions: response.quick_actions
          }
        }
      ]

      await refreshSessions()
    } catch (error) {
      console.error('发送消息失败:', error)
    } finally {
      loading.value = false
      purchaseFlowData.value = null
      aftersalesFlowData.value = null
    }
  }

  async function sendMessageStream(content: string, attachments?: any[], onChunk?: (chunk: string) => void) {
    let sessionId = currentSession.value?.id
    const safeAttachments = sanitizeAttachments(attachments)

    if (!sessionId) {
      const newSession = await createSession(buildSessionTitle(content, safeAttachments))
      if (!newSession) {
        return
      }
      sessionId = newSession.id
    }

    loading.value = true
    const assistantMessageId = `${Date.now()}_assistant`

    try {
      messages.value = [
        ...messages.value,
        {
          id: Date.now().toString(),
          role: 'user',
          content,
          created_at: new Date().toISOString(),
          attachments: safeAttachments
        },
        {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
          metadata: {}
        }
      ]

      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: content,
          attachments: safeAttachments,
          purchase_flow: purchaseFlowData.value,
          aftersales_flow: aftersalesFlowData.value
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
          if (done) {
            break
          }

          const chunk = decoder.decode(value)
          const events = chunk.split('\n\n')

          for (const eventText of events) {
            if (!eventText.startsWith('data: ')) {
              continue
            }

            try {
              const data = JSON.parse(eventText.slice(6))
              const messageIndex = messages.value.findIndex(message => message.id === assistantMessageId)
              if (messageIndex === -1) {
                continue
              }

              if (data.type === 'intent') {
                messages.value[messageIndex].metadata = {
                  ...messages.value[messageIndex].metadata,
                  intent: data.intent
                }
              } else if (data.type === 'thinking') {
                messages.value[messageIndex].metadata = {
                  ...messages.value[messageIndex].metadata,
                  thinking: data.content
                }
              } else if (data.type === 'content') {
                fullContent += data.delta
                messages.value[messageIndex].content = fullContent
                onChunk?.(data.delta)
              } else if (data.type === 'error') {
                messages.value[messageIndex].metadata = {
                  ...messages.value[messageIndex].metadata,
                  error: data.message
                }
              } else if (data.type === 'end') {
                messages.value[messageIndex].metadata = {
                  ...messages.value[messageIndex].metadata,
                  sources: data.sources,
                  quick_actions: data.quick_actions
                }
              }
            } catch (error) {
              console.error('解析流式数据失败:', error)
            }
          }
        }
      }

      setTimeout(async () => {
        await refreshSessions()
      }, 100)
    } catch (error) {
      console.error('流式发送消息失败:', error)
    } finally {
      loading.value = false
      purchaseFlowData.value = null
      aftersalesFlowData.value = null
    }
  }

  async function loadSmartQuestions(messageId: string) {
    try {
      const response = await apiClient.get<{ questions: any[]; mode: string }>('/chat/smart-questions?mode=smart')
      const messageIndex = messages.value.findIndex(message => message.id === messageId)
      if (messageIndex !== -1) {
        messages.value[messageIndex].metadata = {
          ...messages.value[messageIndex].metadata,
          quick_actions: response.questions.slice(0, 3)
        }
      }
    } catch (error) {
      console.error('加载智能问题失败:', error)
      const messageIndex = messages.value.findIndex(message => message.id === messageId)
      if (messageIndex === -1) {
        return
      }

      messages.value[messageIndex].metadata = {
        ...messages.value[messageIndex].metadata,
        quick_actions: [
          {
            type: 'button',
            label: '订单有问题',
            action: 'send_question',
            data: { question: '我的订单有问题' },
            icon: 'package'
          },
          {
            type: 'button',
            label: '如何申请退款',
            action: 'send_question',
            data: { question: '如何申请退款？' },
            icon: 'refund'
          },
          {
            type: 'button',
            label: '如何购买作品',
            action: 'send_question',
            data: { question: '如何购买作品？' },
            icon: 'cart'
          },
          {
            type: 'button',
            label: '使用遇到问题',
            action: 'send_question',
            data: { question: '使用遇到问题怎么办？' },
            icon: 'help'
          }
        ].slice(0, 3)
      }
    }
  }

  function setPurchaseFlowData(data: any) {
    purchaseFlowData.value = data
  }

  function getPurchaseFlowData() {
    return purchaseFlowData.value
  }

  function clearPurchaseFlowData() {
    purchaseFlowData.value = null
  }

  function setAftersalesFlowData(data: any) {
    aftersalesFlowData.value = data
  }

  function clearAftersalesFlowData() {
    aftersalesFlowData.value = null
  }

  function resetSession() {
    currentSession.value = null
    appendWelcomeMessage()
    clearPurchaseFlowData()
    clearAftersalesFlowData()
  }

  return {
    sessions,
    currentSession,
    messages,
    loading,
    purchaseFlowData,
    aftersalesFlowData,
    fetchSessions,
    createSession,
    deleteSession,
    selectSession,
    fetchMessages,
    sendMessage,
    sendMessageStream,
    loadSmartQuestions,
    resetSession,
    setPurchaseFlowData,
    getPurchaseFlowData,
    clearPurchaseFlowData,
    setAftersalesFlowData,
    clearAftersalesFlowData
  }
})
