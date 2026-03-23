package com.chece.api.service;

import com.chece.api.common.Result;
import com.chece.api.dto.ChatResponseDTO;
import com.chece.api.dto.ConversationDTO;
import com.chece.api.dto.MessageDTO;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

public interface ChatService {

    Result<ChatResponseDTO> sendMessage(String sessionId, String userMessage);

    void sendMessageStream(String sessionId, String userMessage, SseEmitter emitter);

    List<MessageDTO> getHistory(String sessionId);

    List<ConversationDTO> getConversations();

    String createNewConversation();

    boolean deleteConversation(String sessionId);
}
