<script setup lang="ts">
/**
 * 通用「AI 处理中」弹窗（管理端）。
 *
 * 凡是走大模型 / 向量库、耗时可能超过 2 秒的操作都用它盖住，
 * 避免运营以为点了没反应（检索测试、解析入库等）。
 */
defineProps<{
  modelValue: boolean
  title?: string
  hint?: string
  elapsed?: number
  slow_after?: number
}>()

defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    width="300px"
    align-center
    append-to-body
    class="ai-loading-dialog"
    @update:model-value="(value: boolean) => $emit('update:modelValue', value)"
  >
    <div class="ai-loading">
      <div class="ai-orb">
        <span class="ripple" />
        <span class="ripple" />
        <span class="ripple" />
        <span class="core">✦</span>
      </div>

      <div class="ai-title">{{ title || 'AI 正在处理' }}</div>

      <div class="ai-dots">
        <i /><i /><i />
      </div>

      <div class="ai-hint">
        {{ hint }}
        <template v-if="typeof elapsed === 'number'">（已等待 {{ elapsed }} 秒）</template>
      </div>

      <div
        v-if="typeof elapsed === 'number' && slow_after && elapsed >= slow_after"
        class="ai-slow"
      >
        模型这会儿有点忙，通常再等几秒就好，请不要关闭页面
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.ai-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 14px 4px 6px;
}

.ai-orb {
  position: relative;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #6366f1, #4338ca);
  box-shadow: 0 0 0 10px rgba(99, 102, 241, 0.1);
  margin-bottom: 22px;
}

.core {
  font-size: 26px;
  color: #fff;
  animation: core_breathe 2.4s ease-in-out infinite;
}

.ripple {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px solid rgba(129, 140, 248, 0.55);
  animation: ripple_out 2.1s ease-out infinite;
}

.ripple:nth-child(2) {
  animation-delay: 0.7s;
}

.ripple:nth-child(3) {
  animation-delay: 1.4s;
}

@keyframes ripple_out {
  0% {
    transform: scale(1);
    opacity: 0.75;
  }
  100% {
    transform: scale(2.3);
    opacity: 0;
  }
}

@keyframes core_breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 0.9;
  }
  50% {
    transform: scale(1.16);
    opacity: 1;
  }
}

.ai-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2330;
  margin-bottom: 12px;
}

.ai-dots {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.ai-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #818cf8;
  animation: dot_bounce 1.2s infinite ease-in-out;
}

.ai-dots i:nth-child(2) {
  animation-delay: 0.15s;
}

.ai-dots i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes dot_bounce {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.45;
  }
  40% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

.ai-hint {
  font-size: 12px;
  line-height: 1.7;
  color: #8a94a8;
  max-width: 240px;
}

.ai-slow {
  margin-top: 10px;
  font-size: 11px;
  line-height: 1.6;
  color: #c98a2e;
  background: #fff8e6;
  border: 1px solid #ffe1a8;
  border-radius: 8px;
  padding: 6px 10px;
}

@media (prefers-reduced-motion: reduce) {
  .ripple,
  .core,
  .ai-dots i {
    animation: none !important;
  }
}
</style>
