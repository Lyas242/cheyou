package com.chece.api.controller;

import com.chece.api.common.Result;
import com.chece.api.dto.ChatRequestDTO;
import com.chece.api.dto.ChatResponseDTO;
import com.chece.api.dto.ConversationDTO;
import com.chece.api.dto.MessageDTO;
import com.chece.api.service.ChatService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;
    
    private final ExecutorService sseExecutor = Executors.newCachedThreadPool();

    @PostMapping("/send")
    public Result<ChatResponseDTO> sendMessage(@RequestBody ChatRequestDTO request) {
        log.info("收到前端发送消息请求, sessionId: {}, message: {}", 
            request.getConversationId(), request.getMessage());

        Result<ChatResponseDTO> result = chatService.sendMessage(
            request.getConversationId(), 
            request.getMessage()
        );

        log.info("消息处理完成, code: {}", result.getCode());
        return result;
    }

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter sendMessageStream(@RequestBody ChatRequestDTO request) {
        log.info("收到流式聊天请求, sessionId: {}, message: {}", 
            request.getConversationId(), request.getMessage());
        
        SseEmitter emitter = new SseEmitter(180000L);
        
        sseExecutor.execute(() -> {
            try {
                chatService.sendMessageStream(
                    request.getConversationId(),
                    request.getMessage(),
                    emitter
                );
            } catch (Exception e) {
                log.error("流式处理异常", e);
                try {
                    emitter.send(SseEmitter.event()
                        .data("{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
                    emitter.complete();
                } catch (IOException ex) {
                    emitter.completeWithError(ex);
                }
            }
        });
        
        emitter.onCompletion(() -> log.info("SSE 连接关闭, sessionId: {}", request.getConversationId()));
        emitter.onTimeout(() -> log.warn("SSE 连接超时, sessionId: {}", request.getConversationId()));
        emitter.onError(e -> log.error("SSE 连接错误: {}", e.getMessage()));
        
        return emitter;
    }

    @GetMapping("/history")
    public Result<List<MessageDTO>> getHistory(@RequestParam String sessionId) {
        log.info("收到查询历史消息请求, sessionId: {}", sessionId);

        if (sessionId == null || sessionId.isEmpty()) {
            log.warn("sessionId 为空，返回错误");
            return Result.error("sessionId 不能为空");
        }

        List<MessageDTO> history = chatService.getHistory(sessionId);
        log.info("查询到 {} 条历史消息", history.size());

        return Result.success(history);
    }

    @GetMapping("/conversations")
    public Result<List<ConversationDTO>> getConversations() {
        log.info("收到查询会话列表请求");

        List<ConversationDTO> conversations = chatService.getConversations();
        log.info("查询到 {} 个会话", conversations.size());

        return Result.success(conversations);
    }

    @PostMapping("/new")
    public Result<String> createNewConversation() {
        log.info("收到创建新会话请求");

        String sessionId = chatService.createNewConversation();
        log.info("新会话创建成功, sessionId: {}", sessionId);

        return Result.success(sessionId);
    }

    @DeleteMapping("/conversation/{sessionId}")
    public Result<Void> deleteConversation(@PathVariable String sessionId) {
        log.info("收到删除会话请求, sessionId: {}", sessionId);

        if (sessionId == null || sessionId.isEmpty()) {
            log.warn("sessionId 为空，返回错误");
            return Result.error("sessionId 不能为空");
        }

        boolean success = chatService.deleteConversation(sessionId);
        if (success) {
            log.info("会话删除成功, sessionId: {}", sessionId);
            return Result.success(null);
        } else {
            log.warn("会话删除失败, sessionId: {}", sessionId);
            return Result.error("会话不存在或删除失败");
        }
    }
}
