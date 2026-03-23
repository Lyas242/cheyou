package com.chece.api.dto;

import com.chece.api.entity.CarRecommendation;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class MessageDTO {

    private String id;

    private String role;

    private String content;

    private List<CarRecommendation> recommendations;

    private LocalDateTime timestamp;
}
