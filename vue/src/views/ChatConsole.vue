<template>
  <el-container class="chat-console">
    <el-aside width="260px" class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          :class="['conversation-item', { active: conv.id === chatStore.currentConversationId }]"
          @click="handleSelectConversation(conv.id)"
        >
          <el-icon class="conv-icon"><ChatDotRound /></el-icon>
          <div class="conv-info">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-last">{{ conv.lastMessage }}</div>
          </div>
          <el-popconfirm
            title="确定要删除这个会话吗？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDeleteConversation(conv.id)"
          >
            <template #reference>
              <el-button
                class="delete-btn"
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click.stop
              />
            </template>
          </el-popconfirm>
        </div>
      </div>
    </el-aside>
    <el-main class="chat-main">
      <div class="messages-container" ref="messagesRef">
        <div
          v-for="(msg, index) in currentMessages"
          :key="msg.id"
          :class="['message-item', msg.role]"
        >
          <div class="message-avatar">
            <el-avatar
              :size="36"
              :icon="msg.role === 'user' ? 'User' : 'Cpu'"
              :class="msg.role"
            />
          </div>
          <div class="message-content">
            <MarkdownRenderer 
              v-if="msg.role === 'agent' || msg.role === 'assistant'" 
              :content="msg.content" 
              :is-streaming="msg.isStreaming"
            />
            <div v-else class="message-text">{{ msg.content }}</div>
            <div v-if="msg.toolCalls && msg.toolCalls.length" class="tool-calls">
              <div v-for="(tool, idx) in msg.toolCalls" :key="idx" class="tool-call-item">
                <el-tag type="info" size="small">
                  <el-icon><Search /></el-icon>
                  {{ tool.name }}
                </el-tag>
                <span v-if="tool.result" class="tool-result">{{ tool.result }}</span>
              </div>
            </div>
            <div v-if="msg.recommendations && msg.recommendations.length" class="recommendations">
              <CarRecommendCard
                v-for="car in msg.recommendations"
                :key="car.id"
                :car="car"
              />
            </div>
          </div>
        </div>
        <div v-if="chatStore.isLoading && !hasStreamingAgentMessage" class="message-item assistant loading">
          <div class="message-avatar">
            <el-avatar :size="36" icon="Cpu" class="assistant" />
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
      <div class="input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="请输入您的选车需求，例如：预算20万，想买一辆纯电SUV..."
          @keydown.enter.ctrl="handleSend"
          resize="none"
        />
        <div class="input-actions">
          <span class="tip">Ctrl + Enter 发送</span>
          <el-button
            type="primary"
            :loading="chatStore.isLoading"
            :disabled="!inputMessage.trim()"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, nextTick, watch, computed, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { 
  sendMessageStream, 
  getConversationHistory, 
  getConversations, 
  createNewConversation, 
  deleteConversation 
} from '@/api/chat'
import { ElMessage } from 'element-plus'
import { Delete, Search } from '@element-plus/icons-vue'
import CarRecommendCard from '@/components/CarRecommendCard.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const chatStore = useChatStore()
const inputMessage = ref('')
const messagesRef = ref(null)
const abortController = ref(null)

const currentMessages = computed(() => chatStore.messages)

const hasStreamingAgentMessage = computed(() => {
  const messages = chatStore.messages
  if (messages.length === 0) return false
  const lastMessage = messages[messages.length - 1]
  return lastMessage.role === 'agent' && lastMessage.isStreaming === true
})

onMounted(async () => {
  try {
    const res = await getConversations()
    if (res.code === 200 && res.data) {
      chatStore.setConversations(res.data)
    }
  } catch (error) {
    console.error('获取会话列表失败:', error)
  }
})

onUnmounted(() => {
  if (abortController.value) {
    abortController.value.abort()
  }
})

async function handleSelectConversation(sessionId) {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
  chatStore.setLoading(false)
  
  chatStore.setCurrentConversation(sessionId)
  try {
    const res = await getConversationHistory(sessionId)
    if (res.code === 200 && res.data) {
      chatStore.setMessages(sessionId, res.data)
    }
  } catch (error) {
    console.error('获取历史消息失败:', error)
  }
}

async function handleSend() {
  const message = inputMessage.value.trim()
  if (!message || chatStore.isLoading) return

  if (!chatStore.currentConversationId) {
    chatStore.createNewConversation()
  }

  chatStore.addMessage({
    role: 'user',
    content: message
  })

  inputMessage.value = ''
  scrollToBottom()

  chatStore.setLoading(true)

  const sessionId = chatStore.currentConversationId

  const agentMessageIndex = chatStore.messages.length
  
  chatStore.addMessage({
    role: 'agent',
    content: '',
    isStreaming: true,
    toolCalls: [],
    recommendations: []
  })

  scrollToBottom()

  abortController.value = sendMessageStream(
    {
      conversationId: sessionId,
      message: message
    },
    {
      onContent: (text) => {
        chatStore.appendStreamingContent(agentMessageIndex, text)
        scrollToBottom()
      },
      
      onToolCall: (name, args) => {
        chatStore.addToolCall(agentMessageIndex, { name, args })
        scrollToBottom()
      },
      
      onToolResult: (name, result) => {
        chatStore.updateToolCallResult(agentMessageIndex, name, result)
      },
      
      onDone: (data) => {
        chatStore.setLoading(false)
        
        chatStore.finalizeStreamingMessage(agentMessageIndex, {
          content: data.content || '',
          recommendations: data.recommendations || []
        })
        
        scrollToBottom()
      },
      
      onError: (errorMsg) => {
        chatStore.setLoading(false)
        
        chatStore.finalizeStreamingMessage(agentMessageIndex, {
          content: `抱歉，处理您的请求时遇到了问题：${errorMsg}`,
          recommendations: []
        })
        
        ElMessage.error(errorMsg)
        scrollToBottom()
      }
    }
  )
}

async function handleNewChat() {
  try {
    const res = await createNewConversation()
    if (res.code === 200 && res.data) {
      chatStore.createNewConversationWithId(res.data)
    }
  } catch (error) {
    console.error('创建新会话失败:', error)
    ElMessage.error('创建新会话失败')
  }
}

async function handleDeleteConversation(sessionId) {
  try {
    const res = await deleteConversation(sessionId)
    if (res.code === 200) {
      chatStore.removeConversation(sessionId)
      ElMessage.success('会话已删除')
      
      if (chatStore.currentConversationId === sessionId) {
        chatStore.setCurrentConversation(null)
        chatStore.clearMessages()
      }
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    console.error('删除会话失败:', error)
    ElMessage.error('删除会话失败')
  }
}

function scrollToBottom(force = false) {
  nextTick(() => {
    if (messagesRef.value) {
      if (force) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight
      } else {
        const container = messagesRef.value
        const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50
        if (isAtBottom) {
          container.scrollTop = container.scrollHeight
        }
      }
    }
  })
}

watch(
  () => currentMessages.value.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => chatStore.currentConversationId,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  }
)
</script>

<style lang="scss" scoped>
.chat-console {
  height: 100%;
  background: #f5f7fa;
}

.chat-sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;

  .new-chat-btn {
    width: 100%;
    height: 44px;
    font-size: 15px;
  }
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s;
  position: relative;

  &:hover {
    background: #f0f2f5;
  }

  &.active {
    background: #ecf5ff;
  }

  .conv-icon {
    font-size: 20px;
    color: #909399;
    margin-right: 10px;
    flex-shrink: 0;
  }

  .conv-info {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .conv-title {
    font-size: 14px;
    color: #303133;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .conv-last {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .delete-btn {
    flex-shrink: 0;
    margin-left: 8px;
    opacity: 0;
    transition: opacity 0.2s;
  }

  &:hover .delete-btn {
    opacity: 1;
  }
}

.chat-main {
  display: flex;
  flex-direction: column;
  padding: 0;
  background: #f5f7fa;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 85%;

  &.user {
    align-self: flex-end;
    flex-direction: row-reverse;

    .message-avatar .el-avatar {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .message-content {
      align-items: flex-end;
    }

    .message-text {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff;
      border-radius: 16px 16px 4px 16px;
    }
  }

  &.assistant,
  &.agent {
    align-self: flex-start;

    .message-avatar .el-avatar {
      background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
  }

  &.loading {
    .message-text {
      padding: 16px 20px;
    }
  }
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 200px;
  max-width: 100%;
}

.message-text {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 8px;
}

.tool-call-item {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-tag {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .tool-result {
    font-size: 12px;
    color: #909399;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 500px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;

  span {
    width: 8px;
    height: 8px;
    background: #909399;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }
    &:nth-child(2) {
      animation-delay: -0.16s;
    }
  }
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.input-area {
  padding: 16px 24px 24px;
  background: #fff;
  border-top: 1px solid #e4e7ed;

  :deep(.el-textarea__inner) {
    border-radius: 12px;
    border: 2px solid #e4e7ed;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px 16px;

    &:focus {
      border-color: #667eea;
    }
  }
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;

  .tip {
    font-size: 12px;
    color: #909399;
  }
}
</style>
