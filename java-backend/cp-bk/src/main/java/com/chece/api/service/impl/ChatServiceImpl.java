package com.chece.api.service.impl;

import cn.hutool.core.util.IdUtil;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.chece.api.common.Result;
import com.chece.api.dto.AgentRequestDTO;
import com.chece.api.dto.AgentResponseDTO;
import com.chece.api.dto.ChatResponseDTO;
import com.chece.api.dto.ConversationDTO;
import com.chece.api.dto.MessageDTO;
import com.chece.api.entity.CarRecommendation;
import com.chece.api.entity.ChatMessage;
import com.chece.api.entity.ChatSession;
import com.chece.api.mapper.ChatMessageMapper;
import com.chece.api.mapper.ChatSessionMapper;
import com.chece.api.service.ChatService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.Disposable;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatServiceImpl implements ChatService {

    private final ChatMessageMapper messageMapper;
    private final ChatSessionMapper sessionMapper;
    private final ObjectMapper objectMapper;
    
    @Value("${agent.service.url:http://localhost:8000}")
    private String agentServiceUrl;

    private static final int CONNECT_TIMEOUT = 10000;
    private static final int READ_TIMEOUT = 60000;
    
    private WebClient getWebClient() {
        return WebClient.builder()
            .baseUrl(agentServiceUrl)
            .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(10 * 1024 * 1024))
            .build();
    }

    @Override
    public Result<ChatResponseDTO> sendMessage(String sessionId, String userMessage) {
        log.info("收到用户消息, sessionId: {}, message: {}", sessionId, userMessage);

        try {
            if (sessionId == null || sessionId.isEmpty()) {
                log.info("sessionId 为空，创建新会话");
                sessionId = createNewConversation();
            }

            ChatSession session = sessionMapper.selectOne(
                new LambdaQueryWrapper<ChatSession>()
                    .eq(ChatSession::getSessionId, sessionId)
            );
            if (session == null) {
                log.warn("会话不存在，创建新会话: {}", sessionId);
                session = new ChatSession();
                session.setSessionId(sessionId);
                session.setTitle("新对话");
                session.setCreateTime(LocalDateTime.now());
                session.setUpdateTime(LocalDateTime.now());
                sessionMapper.insert(session);
            }

            ChatMessage userChatMessage = new ChatMessage();
            userChatMessage.setSessionId(sessionId);
            userChatMessage.setRole("user");
            userChatMessage.setContent(userMessage);
            userChatMessage.setCreateTime(LocalDateTime.now());
            messageMapper.insert(userChatMessage);
            log.info("用户消息已保存到数据库, messageId: {}", userChatMessage.getId());

            AgentResponseDTO agentResponse = callPythonAgentService(sessionId, userMessage);

            ChatMessage agentChatMessage = new ChatMessage();
            agentChatMessage.setSessionId(sessionId);
            agentChatMessage.setRole("agent");
            agentChatMessage.setContent(agentResponse.getContent());
            agentChatMessage.setRecommendations(agentResponse.getRecommendations());
            agentChatMessage.setCreateTime(LocalDateTime.now());
            messageMapper.insert(agentChatMessage);
            log.info("Agent 消息已保存到数据库, messageId: {}", agentChatMessage.getId());

            ChatResponseDTO response = new ChatResponseDTO();
            response.setContent(agentResponse.getContent());
            response.setRecommendations(agentResponse.getRecommendations());

            log.info("消息处理完成，返回结果给前端");
            return Result.success(response);

        } catch (Exception e) {
            log.error("处理消息时发生异常", e);
            return Result.error("处理消息失败: " + e.getMessage());
        }
    }

    @Override
    public void sendMessageStream(String sessionId, String userMessage, SseEmitter emitter) {
        log.info("开始流式处理消息, sessionId: {}, message: {}", sessionId, userMessage);
        
        try {
            if (sessionId == null || sessionId.isEmpty()) {
                log.info("sessionId 为空，创建新会话");
                sessionId = createNewConversation();
            }
            
            final String finalSessionId = sessionId;
            
            ChatSession session = sessionMapper.selectOne(
                new LambdaQueryWrapper<ChatSession>()
                    .eq(ChatSession::getSessionId, finalSessionId)
            );
            if (session == null) {
                log.warn("会话不存在，创建新会话: {}", finalSessionId);
                session = new ChatSession();
                session.setSessionId(finalSessionId);
                session.setTitle("新对话");
                session.setCreateTime(LocalDateTime.now());
                session.setUpdateTime(LocalDateTime.now());
                sessionMapper.insert(session);
            }
            
            ChatMessage userChatMessage = new ChatMessage();
            userChatMessage.setSessionId(finalSessionId);
            userChatMessage.setRole("user");
            userChatMessage.setContent(userMessage);
            userChatMessage.setCreateTime(LocalDateTime.now());
            messageMapper.insert(userChatMessage);
            log.info("用户消息已保存到数据库, messageId: {}", userChatMessage.getId());
            
            AtomicReference<StringBuilder> contentBuilder = new AtomicReference<>(new StringBuilder());
            AtomicReference<List<CarRecommendation>> recommendations = new AtomicReference<>(new ArrayList<>());
            
            AgentRequestDTO request = new AgentRequestDTO();
            request.setSessionId(finalSessionId);
            request.setMessage(userMessage);
            
            String requestBody = JSONUtil.toJsonStr(request);
            log.info("调用 Python Agent 流式接口, url: {}/api/agent/chat/stream", agentServiceUrl);
            
            Disposable subscription = getWebClient()
                .post()
                .uri("/api/agent/chat/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(requestBody)
                .retrieve()
                .bodyToFlux(String.class)
                .subscribe(
                    sseData -> {
                        try {
                            log.debug("收到 SSE 数据: {}", sseData);

                            JsonNode jsonNode = objectMapper.readTree(sseData);
                            String type = jsonNode.path("type").asText();
                            
                            emitter.send(SseEmitter.event().data(sseData));
                            
                            if ("content".equals(type)) {
                                String text = jsonNode.path("text").asText();
                                contentBuilder.get().append(text);
                            } else if ("done".equals(type)) {
                                String content = jsonNode.path("content").asText();
                                if (content != null && !content.isEmpty()) {
                                    contentBuilder.set(new StringBuilder(content));
                                }
                                
                                JsonNode recsNode = jsonNode.path("recommendations");
                                if (recsNode.isArray()) {
                                    List<CarRecommendation> recs = new ArrayList<>();
                                    for (JsonNode recNode : recsNode) {
                                        CarRecommendation rec = new CarRecommendation();
                                        rec.setId(recNode.path("id").asText());
                                        rec.setName(recNode.path("name").asText());
                                        rec.setPriceRange(recNode.path("priceRange").asText());
                                        rec.setImage(recNode.path("image").asText(""));
                                        rec.setDescription(recNode.path("description").asText());
                                        
                                        List<String> tags = new ArrayList<>();
                                        JsonNode tagsNode = recNode.path("tags");
                                        if (tagsNode.isArray()) {
                                            for (JsonNode tag : tagsNode) {
                                                tags.add(tag.asText());
                                            }
                                        }
                                        rec.setTags(tags);
                                        recs.add(rec);
                                    }
                                    recommendations.set(recs);
                                }
                                
                                saveAgentMessage(finalSessionId, contentBuilder.get().toString(), recommendations.get());
                                
                                emitter.complete();
                                log.info("流式处理完成, sessionId: {}", finalSessionId);
                            } else if ("error".equals(type)) {
                                String errorMsg = jsonNode.path("message").asText();
                                log.error("收到错误事件: {}", errorMsg);
                                emitter.completeWithError(new RuntimeException(errorMsg));
                            }
                        } catch (Exception e) {
                            log.error("处理 SSE 数据异常", e);
                            try {
                                emitter.completeWithError(e);
                            } catch (Exception ex) {
                                log.error("完成 SSE 异常", ex);
                            }
                        }
                    },
                    error -> {
                        log.error("WebClient 订阅错误", error);
                        try {
                            String errorJson = "{\"type\":\"error\",\"message\":\"" + error.getMessage() + "\"}";
                            emitter.send(SseEmitter.event().data(errorJson));
                            emitter.complete();
                        } catch (IOException e) {
                            emitter.completeWithError(e);
                        }
                    },
                    () -> {
                        log.info("WebClient 流完成");
                        if (contentBuilder.get().length() > 0) {
                            saveAgentMessage(finalSessionId, contentBuilder.get().toString(), recommendations.get());
                        }
                        emitter.complete();
                    }
                );
            
            emitter.onCompletion(() -> {
                log.info("SSE 连接完成，取消 WebClient 订阅");
                if (!subscription.isDisposed()) {
                    subscription.dispose();
                }
            });
            
            emitter.onTimeout(() -> {
                log.warn("SSE 连接超时，取消 WebClient 订阅");
                if (!subscription.isDisposed()) {
                    subscription.dispose();
                }
            });
            
        } catch (Exception e) {
            log.error("流式处理异常", e);
            try {
                String errorJson = "{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}";
                emitter.send(SseEmitter.event().data(errorJson));
                emitter.complete();
            } catch (IOException ex) {
                emitter.completeWithError(ex);
            }
        }
    }
    
    private void saveAgentMessage(String sessionId, String content, List<CarRecommendation> recommendations) {
        ChatMessage agentChatMessage = new ChatMessage();
        agentChatMessage.setSessionId(sessionId);
        agentChatMessage.setRole("agent");
        agentChatMessage.setContent(content);
        agentChatMessage.setRecommendations(recommendations);
        agentChatMessage.setCreateTime(LocalDateTime.now());
        messageMapper.insert(agentChatMessage);
        log.info("Agent 消息已保存到数据库, messageId: {}", agentChatMessage.getId());
    }

    private AgentResponseDTO callPythonAgentService(String sessionId, String message) {
        log.info("开始调用 Python Agent 服务, url: {}/api/agent/chat", agentServiceUrl);

        AgentRequestDTO request = new AgentRequestDTO();
        request.setSessionId(sessionId);
        request.setMessage(message);

        String requestBody = JSONUtil.toJsonStr(request);
        log.debug("请求体: {}", requestBody);

        try {
            HttpResponse response = HttpRequest.post(agentServiceUrl + "/api/agent/chat")
                .header("Content-Type", "application/json")
                .timeout(CONNECT_TIMEOUT)
                .setReadTimeout(READ_TIMEOUT)
                .body(requestBody)
                .execute();

            log.info("Python Agent 服务响应状态码: {}", response.getStatus());

            if (!response.isOk()) {
                log.warn("Python Agent 服务返回非200状态码，使用 Mock 数据");
                return getMockAgentResponse();
            }

            String responseBody = response.body();
            log.debug("响应体: {}", responseBody);

            AgentResponseDTO agentResponse = JSONUtil.toBean(responseBody, AgentResponseDTO.class);
            log.info("Python Agent 服务调用成功");
            return agentResponse;

        } catch (Exception e) {
            log.warn("调用 Python Agent 服务失败，使用 Mock 数据。错误信息: {}", e.getMessage());
            return getMockAgentResponse();
        }
    }

    private AgentResponseDTO getMockAgentResponse() {
        log.info("使用 Mock 数据作为 Agent 响应");

        AgentResponseDTO response = new AgentResponseDTO();
        response.setContent("根据您的需求，我为您精心挑选了以下车型，希望能帮助您做出选择：");

        List<CarRecommendation> recommendations = new ArrayList<>();

        CarRecommendation car1 = new CarRecommendation();
        car1.setId("car1");
        car1.setName("比亚迪海豹");
        car1.setPriceRange("18.98-28.98万");
        car1.setImage("");
        car1.setTags(List.of("续航出色", "动力强劲", "科技感强"));
        car1.setDescription("比亚迪海豹基于e平台3.0打造，搭载CTB电池车身一体化技术，零百加速最快3.8秒，CLTC续航最高700km。");
        recommendations.add(car1);

        CarRecommendation car2 = new CarRecommendation();
        car2.setId("car2");
        car2.setName("特斯拉 Model 3");
        car2.setPriceRange("24.59-28.59万");
        car2.setImage("");
        car2.setTags(List.of("品牌影响力", "智能驾驶", "超充网络"));
        car2.setDescription("Model 3是特斯拉的明星车型，拥有出色的自动驾驶能力和完善的超充网络覆盖。");
        recommendations.add(car2);

        response.setRecommendations(recommendations);
        return response;
    }

    @Override
    public List<MessageDTO> getHistory(String sessionId) {
        log.info("查询历史消息, sessionId: {}", sessionId);

        LambdaQueryWrapper<ChatMessage> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ChatMessage::getSessionId, sessionId)
               .orderByAsc(ChatMessage::getCreateTime);

        List<ChatMessage> messages = messageMapper.selectList(wrapper);
        log.info("查询到 {} 条历史消息", messages.size());

        List<MessageDTO> result = new ArrayList<>();
        for (ChatMessage msg : messages) {
            MessageDTO dto = new MessageDTO();
            dto.setId(msg.getId().toString());
            dto.setRole(msg.getRole());
            dto.setContent(msg.getContent());
            dto.setRecommendations(msg.getRecommendations());
            dto.setTimestamp(msg.getCreateTime());
            result.add(dto);
        }

        return result;
    }

    @Override
    public List<ConversationDTO> getConversations() {
        log.info("查询所有会话列表");

        LambdaQueryWrapper<ChatSession> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ChatSession::getDeleted, 0)
               .orderByDesc(ChatSession::getCreateTime);

        List<ChatSession> sessions = sessionMapper.selectList(wrapper);
        log.info("查询到 {} 个会话", sessions.size());

        List<ConversationDTO> result = new ArrayList<>();
        for (ChatSession session : sessions) {
            ConversationDTO dto = new ConversationDTO();
            dto.setId(session.getSessionId());
            dto.setTitle(session.getTitle());
            dto.setCreatedAt(session.getCreateTime());

            LambdaQueryWrapper<ChatMessage> msgWrapper = new LambdaQueryWrapper<>();
            msgWrapper.eq(ChatMessage::getSessionId, session.getSessionId())
                      .orderByDesc(ChatMessage::getCreateTime)
                      .last("LIMIT 1");
            ChatMessage lastMsg = messageMapper.selectOne(msgWrapper);

            if (lastMsg != null) {
                String content = lastMsg.getContent();
                dto.setLastMessage(content.length() > 20 
                    ? content.substring(0, 20) + "..." 
                    : content);
            }

            result.add(dto);
        }

        return result;
    }

    @Override
    public String createNewConversation() {
        log.info("创建新会话");

        String sessionId = IdUtil.fastSimpleUUID();

        ChatSession session = new ChatSession();
        session.setSessionId(sessionId);
        session.setTitle("新对话");
        session.setCreateTime(LocalDateTime.now());
        session.setUpdateTime(LocalDateTime.now());

        sessionMapper.insert(session);
        log.info("新会话创建成功, sessionId: {}", sessionId);

        return sessionId;
    }

    @Override
    public boolean deleteConversation(String sessionId) {
        log.info("删除会话, sessionId: {}", sessionId);

        ChatSession session = sessionMapper.selectOne(
            new LambdaQueryWrapper<ChatSession>()
                .eq(ChatSession::getSessionId, sessionId)
        );

        if (session == null) {
            log.warn("会话不存在: {}", sessionId);
            return false;
        }

        int result = sessionMapper.deleteById(session.getId());
        log.info("会话逻辑删除结果: {}, sessionId: {}", result, sessionId);

        int deletedMessages = messageMapper.delete(
            new LambdaQueryWrapper<ChatMessage>()
                .eq(ChatMessage::getSessionId, sessionId)
        );
        log.info("已删除 {} 条关联消息", deletedMessages);

        return result > 0;
    }
}
