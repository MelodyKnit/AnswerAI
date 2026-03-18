<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

type DropdownValue = string | number

type DropdownOption = {
  label: string
  value: DropdownValue
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: DropdownValue | null | undefined
    options: DropdownOption[]
    placeholder?: string
    disabled?: boolean
    ariaLabel?: string
  }>(),
  {
    placeholder: '请选择',
    disabled: false,
    ariaLabel: '下拉选择',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: DropdownValue): void
  (e: 'change', value: DropdownValue): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const menuOpen = ref(false)

const displayLabel = computed(() => {
  const hit = props.options.find((item) => item.value === props.modelValue)
  return hit?.label || props.placeholder
})

const toggleMenu = () => {
  if (props.disabled) return
  menuOpen.value = !menuOpen.value
}

const chooseOption = (option: DropdownOption) => {
  if (option.disabled) return
  emit('update:modelValue', option.value)
  emit('change', option.value)
  menuOpen.value = false
}

const closeMenu = () => {
  menuOpen.value = false
}

const onDocumentPointerDown = (event: Event) => {
  const target = event.target as Node | null
  if (!target) return
  if (!rootRef.value?.contains(target)) {
    closeMenu()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})
</script>

<template>
  <div ref="rootRef" class="app-dropdown" :class="{ open: menuOpen, disabled: disabled }">
    <button
      type="button"
      class="app-dropdown-trigger"
      :disabled="disabled"
      :aria-label="ariaLabel"
      @click="toggleMenu"
    >
      <span class="app-dropdown-label">{{ displayLabel }}</span>
      <ChevronDown :size="16" class="app-dropdown-icon" :class="{ open: menuOpen }" />
    </button>

    <div v-if="menuOpen" class="app-dropdown-menu">
      <button
        v-for="item in options"
        :key="String(item.value)"
        type="button"
        class="app-dropdown-item"
        :class="{ active: modelValue === item.value, disabled: item.disabled }"
        :disabled="item.disabled"
        @click="chooseOption(item)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.app-dropdown {
  position: relative;
  width: 100%;
}

.app-dropdown-trigger {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--line, #dbe4f0);
  border-radius: 12px;
  background: #fff;
  color: var(--ink, #162033);
  font-size: 14px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
}

.app-dropdown-trigger:hover {
  border-color: var(--border-hover, #c7d5ea);
}

.app-dropdown-trigger:focus-visible {
  outline: none;
  border-color: var(--accent, #2563eb);
}

.app-dropdown-label {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.app-dropdown-icon {
  color: var(--ink-soft, #66758c);
  transition: transform 0.2s ease;
}

.app-dropdown-icon.open {
  transform: rotate(180deg);
}

.app-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--line, #dbe4f0);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.12);
  padding: 6px;
  z-index: 30;
}

.app-dropdown-item {
  width: 100%;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ink, #162033);
  text-align: left;
  font-size: 14px;
  padding: 8px 10px;
  cursor: pointer;
}

.app-dropdown-item:hover,
.app-dropdown-item.active {
  background: #eff6ff;
  color: var(--accent, #2563eb);
}

.app-dropdown-item.disabled,
.app-dropdown-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.app-dropdown.disabled .app-dropdown-trigger {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
