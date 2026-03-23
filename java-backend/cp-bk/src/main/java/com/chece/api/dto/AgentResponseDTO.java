package com.chece.api.dto;

import com.chece.api.entity.CarRecommendation;
import lombok.Data;

import java.util.List;

@Data
public class AgentResponseDTO {

    private String content;

    private List<CarRecommendation> recommendations;
}
