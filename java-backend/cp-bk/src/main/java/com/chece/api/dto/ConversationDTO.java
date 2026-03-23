package com.chece.api.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ConversationDTO {

    private String id;

    private String title;

    private String lastMessage;

    private LocalDateTime createdAt;
}
