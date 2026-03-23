package com.chece.api.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CarRecommendation {

    private String id;

    private String name;

    private String priceRange;

    private String image;

    private List<String> tags;

    private String description;
}
