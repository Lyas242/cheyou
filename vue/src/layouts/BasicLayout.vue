<template>
  <el-container class="layout-container">
    <el-header class="layout-header" , height="40px">
      <div class="header-left">
        <span class="logo">车优</span>
        <span class="subtitle">智能选车助手</span>
      </div>
      <div class="header-right">
        <el-dropdown trigger="click">
          <div class="user-avatar">
            <el-avatar :size="30" icon="User" />
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>个人中心</el-dropdown-item>
              <el-dropdown-item divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container class="layout-main">
      <router-view />
    </el-container>
  </el-container>
</template>

<script setup>
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  width: 100%;
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;

  .logo {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 2px;
  }

  .subtitle {
    font-size: 14px;
    opacity: 0.85;
  }
}

.header-right {
  .user-avatar {
    cursor: pointer;
    transition: transform 0.2s;

    &:hover {
      transform: scale(1.05);
    }
  }
}

.layout-main {
  height: calc(100vh - 60px);
  overflow: hidden;
}
</style>
