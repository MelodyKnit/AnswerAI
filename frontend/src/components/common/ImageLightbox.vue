<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: boolean
  src: string
  alt?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const close = () => {
  emit('update:modelValue', false)
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    close()
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      window.addEventListener('keydown', handleKeydown)
      return
    }
    window.removeEventListener('keydown', handleKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <teleport to="body">
    <div v-if="modelValue && src" class="image-lightbox" @click.self="close">
      <button class="lightbox-close" aria-label="关闭图片预览" @click="close">
        <X :size="18" />
      </button>
      <div class="lightbox-frame">
        <img :src="src" :alt="alt || '放大图片'" class="lightbox-image" />
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(4px);
}

.lightbox-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.lightbox-frame {
  max-width: min(1200px, 100%);
  max-height: min(92vh, 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-image {
  max-width: 100%;
  max-height: 92vh;
  object-fit: contain;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}

@media (max-width: 768px) {
  .image-lightbox {
    padding: 14px;
  }

  .lightbox-close {
    top: 14px;
    right: 14px;
  }

  .lightbox-image {
    border-radius: 12px;
  }
}
</style>