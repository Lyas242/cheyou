package com.chece.api.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.chece.api.entity.ChatMessage;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ChatMessageMapper extends BaseMapper<ChatMessage> {
}
