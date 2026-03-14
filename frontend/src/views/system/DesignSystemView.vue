<template>
  <div class="coming-soon-view">
    <div class="message">
      <h2>UI 设计系统</h2>
      <p>模块正在开发中...</p>
    </div>
  </div>
</template>

<style scoped>
.coming-soon-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--bg);
  border-radius: var(--radius-md);
  border: 1px dashed var(--line);
  padding: 40px;
}
.message {
  text-align: center;
}
h2 {
  font-size: 18px;
  font-weight: 500;
  color: var(--ink);
  margin-bottom: 8px;
}
p {
  font-size: 14px;
  color: var(--ink-soft);
}
</style>
