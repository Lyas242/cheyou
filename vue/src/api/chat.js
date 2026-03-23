import request from '@/utils/request'
import { fetchEventSource } from '@microsoft/fetch-event-source'

export function sendMessage(data) {
  return request({
    url: '/chat/send',
    method: 'post',
    data
  })
}

export function sendMessageStream(data, callbacks) {
  const { onContent, onToolCall, onToolResult, onDone, onError } = callbacks
  
  const controller = new AbortController()
  
  fetchEventSource('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data),
    signal: controller.signal,
    
    async onopen(response) {
      if (response.ok) {
        console.log('SSE 连接已建立')
        return
      }
      
      if (response.status >= 400 && response.status < 500 && response.status !== 429) {
        const text = await response.text()
        onError(`连接失败: ${response.status} - ${text}`)
        controller.abort()
      }
    },
    
    onmessage(event) {
      try {
        const data = JSON.parse(event.data)
        console.log('收到 SSE 数据:', data)
        
        switch (data.type) {
          case 'content':
            onContent(data.text)
            break
          case 'tool_call':
            onToolCall(data.name, data.args)
            break
          case 'tool_result':
            onToolResult(data.name, data.result)
            break
          case 'done':
            onDone(data)
            controller.abort()
            break
          case 'error':
            onError(data.message)
            controller.abort()
            break
        }
      } catch (e) {
        console.error('解析 SSE 数据失败:', e, event.data)
      }
    },
    
    onerror(error) {
      console.error('SSE 连接错误:', error)
      onError(error.message || '连接错误，请稍后重试')
      throw error
    },
    
    onclose() {
      console.log('SSE 连接已关闭')
    }
  })
  
  return controller
}

export function getConversationHistory(sessionId) {
  return request({
    url: '/chat/history',
    method: 'get',
    params: { sessionId }
  })
}

export function getConversations() {
  return request({
    url: '/chat/conversations',
    method: 'get'
  })
}

export function createNewConversation() {
  return request({
    url: '/chat/new',
    method: 'post'
  })
}

export function deleteConversation(sessionId) {
  return request({
    url: `/chat/conversation/${sessionId}`,
    method: 'delete'
  })
}
