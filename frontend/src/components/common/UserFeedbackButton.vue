<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Loader2, MessageSquareWarning, Plus, Send, X } from 'lucide-vue-next'
import { uploadImage } from '@/api/upload'
import { submitUserFeedback, type FeedbackCategory } from '@/api/feedback'

const props = withDefaults(
  defineProps<{
    contextLabel?: string
    compact?: boolean
  }>(),
  {
    contextLabel: '',
    compact: false,
  },
)

const route = useRoute()

const showDialog = ref(false)
const submitting = ref(false)
const uploadBusy = ref(false)
const msg = ref('')

const category = ref<FeedbackCategory>('bug')
const content = ref('')
const imageUrls = ref<string[]>([])

const categoryOptions: Array<{ value: FeedbackCategory; label: string }> = [
  { value: 'bug', label: 'BUG反馈' },
  { value: 'product', label: '软件反馈' },
  { value: 'design', label: '设计建议' },
  { value: 'other', label: '其他' },
]

const categoryLabel = computed(() => categoryOptions.find((item) => item.value === category.value)?.label || '反馈')

const openDialog = () => {
  msg.value = ''
  showDialog.value = true
}

const closeDialog = () => {
  if (submitting.value || uploadBusy.value) return
  showDialog.value = false
}

const removeImage = (index: number) => {
  imageUrls.value.splice(index, 1)
}

const handlePickImage = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (imageUrls.value.length >= 6) {
    msg.value = '最多上传 6 张图片'
    return
  }
  try {
    uploadBusy.value = true
    msg.value = ''
    const res: any = await uploadImage(file)
    const url = String(res?.url || '').trim()
    if (!url) {
      msg.value = '上传失败，请重试'
      return
    }
    imageUrls.value.push(url)
  } catch (error: any) {
    msg.value = error?.message || '图片上传失败，请稍后重试'
  } finally {
    uploadBusy.value = false
  }
}

const resetForm = () => {
  category.value = 'bug'
  content.value = ''
  imageUrls.value = []
}

const submitFeedback = async () => {
  msg.value = ''
  if (content.value.trim().length < 5) {
    msg.value = '请至少填写 5 个字，描述你遇到的问题或建议'
    return
  }
  try {
    submitting.value = true
    await submitUserFeedback({
      category: category.value,
      content: content.value.trim(),
      images: imageUrls.value,
      page_path: route.fullPath,
    })
    msg.value = '反馈已提交，感谢你的帮助'
    resetForm()
  } catch (error: any) {
    msg.value = error?.message || '提交失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="feedback-entry">
    <button class="feedback-btn" :class="{ compact }" type="button" @click="openDialog">
      <MessageSquareWarning :size="16" />
      <span>功能反馈</span>
    </button>

    <teleport to="body">
      <div v-if="showDialog" class="feedback-overlay" @click.self="closeDialog">
        <section class="feedback-modal" role="dialog" aria-modal="true" aria-label="功能反馈">
          <header class="feedback-head">
            <div>
              <p class="feedback-kicker">帮助我们优化产品</p>
              <h3>提交功能反馈</h3>
              <p v-if="contextLabel" class="feedback-context">当前页面：{{ contextLabel }}</p>
            </div>
            <button class="icon-btn" type="button" @click="closeDialog" :disabled="submitting || uploadBusy">
              <X :size="16" />
            </button>
          </header>

          <div class="feedback-body">
            <label class="field">
              <span>反馈类型</span>
              <select v-model="category">
                <option v-for="item in categoryOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>

            <label class="field">
              <span>问题描述</span>
              <textarea
                v-model="content"
                rows="4"
                placeholder="请写清楚：你期望看到什么、实际发生了什么、如何复现（如有）"
              />
            </label>

            <div class="field">
              <span>问题截图（可选，最多6张）</span>
              <div class="upload-row">
                <label class="upload-btn" :class="{ disabled: uploadBusy || imageUrls.length >= 6 }">
                  <Loader2 v-if="uploadBusy" :size="14" class="spin" />
                  <Plus v-else :size="14" />
                  上传图片
                  <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" :disabled="uploadBusy || imageUrls.length >= 6" @change="handlePickImage" />
                </label>
                <span class="muted">已上传 {{ imageUrls.length }}/6</span>
              </div>

              <div v-if="imageUrls.length" class="image-grid">
                <div v-for="(url, idx) in imageUrls" :key="`${url}-${idx}`" class="image-item">
                  <img :src="url" alt="反馈截图" />
                  <button type="button" class="remove-btn" @click="removeImage(idx)">删除</button>
                </div>
              </div>
            </div>

            <div class="tips">
              <span class="tip-pill" :class="category">{{ categoryLabel }}</span>
              <span class="muted">建议附上截图，能更快定位问题。</span>
            </div>

            <p v-if="msg" class="msg">{{ msg }}</p>
          </div>

          <footer class="feedback-foot">
            <button class="button ghost" type="button" @click="closeDialog" :disabled="submitting || uploadBusy">取消</button>
            <button class="button primary" type="button" @click="submitFeedback" :disabled="submitting || uploadBusy || !content.trim()">
              <Loader2 v-if="submitting" :size="14" class="spin" />
              <Send v-else :size="14" />
              提交反馈
            </button>
          </footer>
        </section>
      </div>
    </teleport>
  </div>
</template>

<style scoped>
.feedback-btn {
  border: 1px solid #d8e2ee;
  background: #ffffff;
  color: #55657a;
  border-radius: 10px;
  height: 34px;
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
}

.feedback-btn.compact {
  height: 30px;
  padding: 0 9px;
  font-size: 12px;
}

.feedback-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(2, 6, 23, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 12px;
}

.feedback-modal {
  width: min(640px, 100%);
  max-height: min(88vh, 760px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid #d7e2df;
  background: #f7fbfa;
}

.feedback-head {
  padding: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid #e2ece9;
}

.feedback-kicker {
  margin: 0;
  font-size: 11px;
  color: #60716b;
}

.feedback-head h3 {
  margin: 2px 0 0;
  font-size: 20px;
  color: #182320;
}

.feedback-context {
  margin: 4px 0 0;
  color: #60716b;
  font-size: 12px;
}

.icon-btn {
  border: 1px solid #d6e1de;
  border-radius: 8px;
  background: #fff;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #334155;
}

.feedback-body {
  padding: 12px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 12px;
  color: #4b5f58;
}

.field select,
.field textarea {
  border: 1px solid #cfdbd7;
  border-radius: 10px;
  background: #fff;
  padding: 8px 10px;
  font-size: 14px;
  color: #17211d;
}

.field textarea {
  resize: vertical;
  min-height: 104px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-btn {
  position: relative;
  border: 1px dashed #9fb5ad;
  color: #0f766e;
  background: #fff;
  border-radius: 9px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.upload-btn.disabled {
  opacity: 0.6;
}

.upload-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.image-item {
  border: 1px solid #d3dfdb;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.image-item img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.remove-btn {
  width: 100%;
  border: none;
  border-top: 1px solid #e2ece9;
  background: #fff;
  color: #b91c1c;
  font-size: 12px;
  padding: 6px;
}

.feedback-foot {
  border-top: 1px solid #e2ece9;
  padding: 10px 12px 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.button {
  border-radius: 9px;
  height: 34px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.button.ghost {
  border: 1px solid #cfdad6;
  background: #fff;
  color: #334155;
}

.button.primary {
  border: none;
  background: #0f766e;
  color: #fff;
}

.msg {
  margin: 0;
  font-size: 12px;
  color: #475569;
}

.tips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tip-pill {
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 11px;
  color: #fff;
}

.tip-pill.bug {
  background: #dc2626;
}

.tip-pill.product {
  background: #2563eb;
}

.tip-pill.design {
  background: #0f766e;
}

.tip-pill.other {
  background: #64748b;
}

.muted {
  color: #60716b;
  font-size: 12px;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (min-width: 769px) {
  .feedback-overlay {
    align-items: center;
  }
}
</style>
