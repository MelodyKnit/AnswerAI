import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    subtitle?: string
    section?: 'marketing' | 'auth' | 'student' | 'teacher' | 'system'
  }
}