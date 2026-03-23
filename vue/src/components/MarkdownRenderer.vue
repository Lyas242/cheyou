<template>
  <div class="markdown-wrapper">
    <div class="markdown-content" v-html="renderedContent"></div>
    <span v-if="isStreaming" class="streaming-cursor"></span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  isStreaming: {
    type: Boolean,
    default: false
  }
})

marked.setOptions({
  breaks: true,
  gfm: true
})

const renderedContent = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content)
})
</script>

<style lang="scss">
.markdown-wrapper {
  display: inline-flex;
  align-items: flex-start;
  gap: 2px;
}

.markdown-content {
  line-height: 1.8;
  font-size: 14px;
  color: #303133;
  padding: 12px 16px;
  background: #fff;
  border-radius: 16px 16px 16px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  max-width: 600px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 16px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #ebeef5;

    &:first-child {
      margin-top: 0;
    }
  }

  h4 {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin: 12px 0 8px 0;
  }

  p {
    margin: 8px 0;
    line-height: 1.8;
  }

  strong {
    font-weight: 600;
    color: #409eff;
  }

  ul, ol {
    margin: 8px 0;
    padding-left: 20px;
  }

  li {
    margin: 6px 0;
    line-height: 1.7;
  }

  code {
    background: #f5f7fa;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    color: #e6a23c;
  }

  pre {
    background: #f5f7fa;
    padding: 12px 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 12px 0;

    code {
      background: transparent;
      padding: 0;
      color: #303133;
    }
  }

  blockquote {
    border-left: 4px solid #409eff;
    padding-left: 12px;
    margin: 12px 0;
    color: #606266;
    background: #ecf5ff;
    padding: 8px 12px;
    border-radius: 0 8px 8px 0;
  }

  hr {
    border: none;
    border-top: 1px solid #ebeef5;
    margin: 16px 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;

    th, td {
      border: 1px solid #ebeef5;
      padding: 8px 12px;
      text-align: left;
    }

    th {
      background: #f5f7fa;
      font-weight: 600;
    }

    tr:nth-child(even) {
      background: #fafafa;
    }
  }

  a {
    color: #409eff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 18px;
  background: #409eff;
  animation: blink 1s infinite;
  vertical-align: middle;
  margin-top: 14px;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}
</style>
