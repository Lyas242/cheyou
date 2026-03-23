import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])

  const currentConversationId = ref(null)

  const messagesMap = ref({})

  const isLoading = ref(false)

  const currentConversation = computed(() => {
    return conversations.value.find(c => c.id === currentConversationId.value)
  })

  const messages = computed(() => {
    return messagesMap.value[currentConversationId.value] || []
  })

  function setConversations(list) {
    conversations.value = list.map(item => ({
      id: item.id,
      title: item.title,
      lastMessage: item.lastMessage,
      createdAt: item.createdAt
    }))
  }

  function setMessages(sessionId, list) {
    messagesMap.value[sessionId] = list.map(item => ({
      id: item.id,
      role: item.role,
      content: item.content,
      recommendations: item.recommendations,
      timestamp: item.timestamp,
      isStreaming: false,
      toolCalls: []
    }))
  }

  function addMessage(message) {
    const conversationId = currentConversationId.value
    if (!conversationId) return

    if (!messagesMap.value[conversationId]) {
      messagesMap.value[conversationId] = []
    }
    messagesMap.value[conversationId].push({
      id: Date.now().toString(),
      ...message,
      timestamp: new Date().toISOString()
    })
  }

  function updateMessage(index, updates) {
    const conversationId = currentConversationId.value
    if (!conversationId || !messagesMap.value[conversationId]) return
    
    const messages = messagesMap.value[conversationId]
    if (messages[index]) {
      messages[index] = {
        ...messages[index],
        ...updates
      }
      messagesMap.value = {
        ...messagesMap.value,
        [conversationId]: [...messages]
      }
    }
  }

  function appendStreamingContent(messageIndex, text) {
    const conversationId = currentConversationId.value
    if (!conversationId || !messagesMap.value[conversationId]) return
    
    const messages = messagesMap.value[conversationId]
    if (messages[messageIndex]) {
      messages[messageIndex].content += text
      
      messagesMap.value = {
        ...messagesMap.value,
        [conversationId]: [...messages]
      }
    }
  }

  function addToolCall(messageIndex, toolCall) {
    const conversationId = currentConversationId.value
    if (!conversationId || !messagesMap.value[conversationId]) return
    
    const messages = messagesMap.value[conversationId]
    if (messages[messageIndex]) {
      if (!messages[messageIndex].toolCalls) {
        messages[messageIndex].toolCalls = []
      }
      messages[messageIndex].toolCalls.push({
        name: toolCall.name,
        args: toolCall.args,
        result: null
      })
      
      messagesMap.value = {
        ...messagesMap.value,
        [conversationId]: [...messages]
      }
    }
  }

  function updateToolCallResult(messageIndex, toolName, result) {
    const conversationId = currentConversationId.value
    if (!conversationId || !messagesMap.value[conversationId]) return
    
    const messages = messagesMap.value[conversationId]
    if (messages[messageIndex] && messages[messageIndex].toolCalls) {
      const toolCall = messages[messageIndex].toolCalls.find(t => t.name === toolName)
      if (toolCall) {
        toolCall.result = result
        
        messagesMap.value = {
          ...messagesMap.value,
          [conversationId]: [...messages]
        }
      }
    }
  }

  function finalizeStreamingMessage(messageIndex, data) {
    const conversationId = currentConversationId.value
    if (!conversationId || !messagesMap.value[conversationId]) return
    
    const messages = messagesMap.value[conversationId]
    if (messages[messageIndex]) {
      messages[messageIndex].isStreaming = false
      
      if (data.content) {
        messages[messageIndex].content = data.content
      }
      
      if (data.recommendations && data.recommendations.length) {
        messages[messageIndex].recommendations = data.recommendations
      }
      
      messagesMap.value = {
        ...messagesMap.value,
        [conversationId]: [...messages]
      }
    }
  }

  function setLoading(status) {
    isLoading.value = status
  }

  function setCurrentConversation(id) {
    currentConversationId.value = id
  }

  function createNewConversation() {
    const newId = Date.now().toString()
    conversations.value.unshift({
      id: newId,
      title: '新对话',
      lastMessage: '',
      createdAt: new Date().toISOString()
    })
    messagesMap.value[newId] = []
    currentConversationId.value = newId
    return newId
  }

  function createNewConversationWithId(sessionId) {
    conversations.value.unshift({
      id: sessionId,
      title: '新对话',
      lastMessage: '',
      createdAt: new Date().toISOString()
    })
    messagesMap.value[sessionId] = []
    currentConversationId.value = sessionId
  }

  function removeConversation(sessionId) {
    const index = conversations.value.findIndex(c => c.id === sessionId)
    if (index !== -1) {
      conversations.value.splice(index, 1)
    }
    delete messagesMap.value[sessionId]
  }

  function clearMessages() {
    if (currentConversationId.value) {
      messagesMap.value[currentConversationId.value] = []
    }
  }

  return {
    conversations,
    currentConversationId,
    messagesMap,
    messages,
    isLoading,
    currentConversation,
    setConversations,
    setMessages,
    addMessage,
    updateMessage,
    appendStreamingContent,
    addToolCall,
    updateToolCallResult,
    finalizeStreamingMessage,
    setLoading,
    setCurrentConversation,
    createNewConversation,
    createNewConversationWithId,
    removeConversation,
    clearMessages
  }
})
