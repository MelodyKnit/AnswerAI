type RenderRichContentOptions = {
  apiBase?: string
  imageClassName?: string
  imageAlt?: string
  textClassName?: string
}

const DEFAULT_UPLOAD_IMAGE_DIR = '/uploads/subject-import'

const getBackendOrigin = (apiBase: string) => {
  if (/^https?:\/\//i.test(apiBase)) {
    try {
      return new URL(apiBase).origin
    } catch {
      return ''
    }
  }
  return ''
}

const escapeHtml = (value: string) => {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export const normalizeAssetUrl = (rawUrl: string, apiBase = '/api/v1') => {
  const trimmed = String(rawUrl || '').trim()
  if (!trimmed) return ''
  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith('//') || trimmed.startsWith('blob:')) {
    return trimmed
  }

  const backendOrigin = getBackendOrigin(apiBase)
  if (trimmed.startsWith('/')) {
    return backendOrigin ? `${backendOrigin}${trimmed}` : trimmed
  }

  if (/\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(trimmed)) {
    const path = `${DEFAULT_UPLOAD_IMAGE_DIR}/${trimmed.replace(/^\/+/, '')}`
    return backendOrigin ? `${backendOrigin}${path}` : path
  }

  return backendOrigin ? `${backendOrigin}/${trimmed.replace(/^\/+/, '')}` : trimmed
}

export const renderRichContent = (value: unknown, options: RenderRichContentOptions = {}) => {
  const apiBase = options.apiBase || '/api/v1'
  const imageClassName = options.imageClassName || 'rich-image'
  const imageAlt = options.imageAlt || '图片'
  const textClassName = options.textClassName || 'rich-text'

  const raw = String(value ?? '')
  if (!raw.trim()) return ''

  const trimmed = raw.trim()
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    try {
      const blocks = JSON.parse(trimmed)
      if (Array.isArray(blocks)) {
        return blocks
          .map((item: any) => {
            const blockType = String(item?.type || '').toLowerCase()
            const blockContent = String(item?.content || '')
            if (blockType === 'image') {
              const src = normalizeAssetUrl(blockContent, apiBase)
              return src ? `<img class="${imageClassName}" src="${src}" alt="${imageAlt}" />` : ''
            }
            return `<span class="${textClassName}">${escapeHtml(blockContent)}</span>`
          })
          .filter(Boolean)
          .join('')
      }
    } catch {
      // Fall through to markdown/plain text rendering.
    }
  }

  return escapeHtml(raw)
    .replace(/!\[[^\]]*\]\(([^)]+)\)/g, (_, src) => {
      const normalized = normalizeAssetUrl(String(src || ''), apiBase)
      return normalized ? `<img class="${imageClassName}" src="${normalized}" alt="${imageAlt}" />` : ''
    })
    .replace(/\n/g, '<br />')
}
