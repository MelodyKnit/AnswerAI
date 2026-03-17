<script setup lang="ts">
import { RouterView } from 'vue-router'
import GlobalFeedbackHost from '@/components/common/GlobalFeedbackHost.vue'
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="page-enter" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </RouterView>
  <GlobalFeedbackHost />
</template>
