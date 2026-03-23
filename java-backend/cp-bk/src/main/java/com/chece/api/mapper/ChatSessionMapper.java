package com.chece.api.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.chece.api.entity.ChatSession;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ChatSessionMapper extends BaseMapper<ChatSession> {
}
