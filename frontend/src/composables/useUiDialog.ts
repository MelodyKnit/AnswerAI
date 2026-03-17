import { reactive } from 'vue'

export type UiToastTone = 'info' | 'success' | 'warning' | 'error'
type DialogKind = 'alert' | 'confirm' | 'prompt'

type DialogOptions = {
  title?: string
  confirmText?: string
  cancelText?: string
  tone?: UiToastTone
}

type PromptOptions = DialogOptions & {
  placeholder?: string
  defaultValue?: string
}

type ToastItem = {
  id: number
  message: string
  tone: UiToastTone
}

type DialogState = {
  open: boolean
  kind: DialogKind
  title: string
  message: string
  confirmText: string
  cancelText: string
  placeholder: string
  inputValue: string
  tone: UiToastTone
  resolver: ((value: boolean | string | null) => void) | null
}

const state = reactive({
  toasts: [] as ToastItem[],
  dialog: {
    open: false,
    kind: 'alert',
    title: '',
    message: '',
    confirmText: '知道了',
    cancelText: '取消',
    placeholder: '',
    inputValue: '',
    tone: 'info',
    resolver: null,
  } as DialogState,
})

let toastSeed = 1

const openDialog = (
  kind: DialogKind,
  message: string,
  options: DialogOptions | PromptOptions = {},
) => {
  if (state.dialog.open && state.dialog.resolver) {
    state.dialog.resolver(null)
  }

  state.dialog.open = true
  state.dialog.kind = kind
  state.dialog.message = message
  state.dialog.title = options.title || (kind === 'prompt' ? '请输入内容' : kind === 'confirm' ? '请确认操作' : '提示')
  state.dialog.confirmText = options.confirmText || (kind === 'confirm' ? '确认' : '知道了')
  state.dialog.cancelText = options.cancelText || '取消'
  state.dialog.placeholder = 'placeholder' in options ? options.placeholder || '' : ''
  state.dialog.inputValue = 'defaultValue' in options ? options.defaultValue || '' : ''
  state.dialog.tone = options.tone || 'info'

  return new Promise<boolean | string | null>((resolve) => {
    state.dialog.resolver = resolve
  })
}

const closeDialog = (value: boolean | string | null) => {
  const resolver = state.dialog.resolver
  state.dialog.open = false
  state.dialog.resolver = null
  if (resolver) {
    resolver(value)
  }
}

const pushToast = (message: string, tone: UiToastTone = 'info', duration = 2600) => {
  const id = toastSeed++
  state.toasts.push({ id, message, tone })
  window.setTimeout(() => {
    const index = state.toasts.findIndex((item) => item.id === id)
    if (index >= 0) {
      state.toasts.splice(index, 1)
    }
  }, duration)
}

export const uiDialog = {
  state,
  toast: pushToast,
  alert: async (message: string, options?: DialogOptions) => {
    await openDialog('alert', message, options)
  },
  confirm: async (message: string, options?: DialogOptions) => {
    const result = await openDialog('confirm', message, options)
    return result === true
  },
  prompt: async (message: string, options?: PromptOptions) => {
    const result = await openDialog('prompt', message, options)
    return typeof result === 'string' ? result : null
  },
  resolveAlert: () => closeDialog(true),
  resolveConfirm: (accepted: boolean) => closeDialog(accepted),
  resolvePrompt: (value: string | null) => closeDialog(value),
}

export const useUiDialog = () => uiDialog