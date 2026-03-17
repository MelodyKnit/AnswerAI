<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, CheckCircle2, CircleAlert, MessageSquareText, XCircle } from 'lucide-vue-next'
import { useUiDialog } from '@/composables/useUiDialog'

const dialog = useUiDialog()
const state = dialog.state

const isPrompt = computed(() => state.dialog.kind === 'prompt')
const isConfirm = computed(() => state.dialog.kind === 'confirm')

const iconMap = {
  info: CircleAlert,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
}

const dialogIcon = computed(() => iconMap[state.dialog.tone] || MessageSquareText)

const handleConfirm = () => {
  if (state.dialog.kind === 'prompt') {
    dialog.resolvePrompt(state.dialog.inputValue.trim())
    return
  }
  if (state.dialog.kind === 'confirm') {
    dialog.resolveConfirm(true)
    return
  }
  dialog.resolveAlert()
}

const handleCancel = () => {
  if (state.dialog.kind === 'prompt') {
    dialog.resolvePrompt(null)
    return
  }
  dialog.resolveConfirm(false)
}
</script>

<template>
  <Teleport to="body">
    <div class="feedback-toast-stack">
      <TransitionGroup name="toast-slide">
        <div v-for="item in state.toasts" :key="item.id" class="toast-item" :class="`tone-${item.tone}`">
          <component :is="iconMap[item.tone] || MessageSquareText" :size="16" />
          <span>{{ item.message }}</span>
        </div>
      </TransitionGroup>
    </div>

    <Transition name="dialog-fade">
      <div v-if="state.dialog.open" class="dialog-mask" @click.self="state.dialog.kind === 'alert' ? handleConfirm() : handleCancel()">
        <div class="dialog-card" :class="`tone-${state.dialog.tone}`">
          <div class="dialog-head">
            <div class="dialog-title-wrap">
              <component :is="dialogIcon" :size="18" />
              <strong>{{ state.dialog.title }}</strong>
            </div>
          </div>

          <p class="dialog-message">{{ state.dialog.message }}</p>

          <label v-if="isPrompt" class="dialog-input-wrap">
            <input
              v-model="state.dialog.inputValue"
              class="dialog-input"
              type="text"
              :placeholder="state.dialog.placeholder || '请输入内容'"
              @keydown.enter="handleConfirm"
            />
          </label>

          <div class="dialog-actions">
            <button v-if="isConfirm || isPrompt" class="dialog-btn dialog-btn--ghost" @click="handleCancel">
              {{ state.dialog.cancelText }}
            </button>
            <button class="dialog-btn dialog-btn--primary" @click="handleConfirm">
              {{ state.dialog.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.feedback-toast-stack {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: min(92vw, 420px);
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dbe4f0;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
  color: #162033;
  font-size: 13px;
  line-height: 1.5;
}

.toast-item.tone-success { border-color: #b8e3cd; color: #0f6b46; }
.toast-item.tone-warning { border-color: #f0d484; color: #8a6502; }
.toast-item.tone-error { border-color: #f0b9bb; color: #ab2530; }
.toast-item.tone-info { border-color: #cbdcf9; color: #1d4ed8; }

.dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 1999;
  background: rgba(15, 23, 42, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.dialog-card {
  width: min(92vw, 440px);
  border-radius: 22px;
  border: 1px solid #dbe4f0;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.dialog-card.tone-warning {
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.12), transparent 34%),
    linear-gradient(180deg, #fffef9 0%, #fff9eb 100%);
}

.dialog-card.tone-error {
  background:
    radial-gradient(circle at top right, rgba(239, 68, 68, 0.1), transparent 34%),
    linear-gradient(180deg, #fffefe 0%, #fff5f5 100%);
}

.dialog-card.tone-success {
  background:
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.1), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f1fbf7 100%);
}

.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #162033;
}

.dialog-message {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #556274;
  white-space: pre-wrap;
}

.dialog-input-wrap {
  display: block;
}

.dialog-input {
  width: 100%;
  box-sizing: border-box;
  height: 44px;
  border-radius: 12px;
  border: 1px solid #d7e2ef;
  background: #fff;
  padding: 0 14px;
  font-size: 14px;
  outline: none;
}

.dialog-input:focus {
  border-color: #9bb8f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-btn {
  min-width: 88px;
  height: 40px;
  border-radius: 999px;
  padding: 0 16px;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.dialog-btn--ghost {
  background: #fff;
  color: #4b5563;
  border-color: #d6dee8;
}

.dialog-btn--primary {
  background: #1d4ed8;
  color: #fff;
}

.toast-slide-enter-active,
.toast-slide-leave-active,
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: all 0.22s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>