package com.chece.api;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.chece.api.mapper")
public class CpBkApplication {

    public static void main(String[] args) {
        SpringApplication.run(CpBkApplication.class, args);
    }
}
