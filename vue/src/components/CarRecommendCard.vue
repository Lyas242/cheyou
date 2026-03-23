<template>
  <el-card class="car-recommend-card" shadow="hover">
    <div class="card-header">
      <div class="car-image">
        <el-icon :size="48"><Picture /></el-icon>
        <span class="placeholder-text">车型图片</span>
      </div>
      <div class="car-info">
        <h3 class="car-name">{{ car.name }}</h3>
        <div class="car-price">
          <el-icon><PriceTag /></el-icon>
          <span>{{ car.priceRange }}</span>
        </div>
      </div>
    </div>
    <div class="card-tags">
      <el-tag
        v-for="tag in car.tags"
        :key="tag"
        type="success"
        effect="light"
        size="small"
      >
        {{ tag }}
      </el-tag>
    </div>
    <div class="card-description">
      {{ car.description }}
    </div>
    <div class="card-actions">
      <el-button type="primary" size="small" text>
        <el-icon><InfoFilled /></el-icon>
        查看详情
      </el-button>
      <el-button type="warning" size="small" text>
        <el-icon><Star /></el-icon>
        加入对比
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  car: {
    type: Object,
    required: true,
    default: () => ({
      id: '',
      name: '',
      priceRange: '',
      image: '',
      tags: [],
      description: ''
    })
  }
})
</script>

<style lang="scss" scoped>
.car-recommend-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;

  :deep(.el-card__body) {
    padding: 16px;
  }
}

.card-header {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.car-image {
  width: 100px;
  height: 75px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  flex-shrink: 0;

  .placeholder-text {
    font-size: 10px;
    margin-top: 4px;
  }
}

.car-info {
  flex: 1;
  min-width: 0;
}

.car-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.car-price {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #f56c6c;
  font-weight: 500;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.card-description {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f2f5;
}
</style>
