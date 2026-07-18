<template>
    <div class="tickets-page container">
      <div class="state-card">
        <strong>服务工单已整合至智能客服</strong>
        <p>请前往智能客服提交选茶、订单物流或售后问题，系统会保留完整咨询记录。</p>
      </div>
    </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.tickets-page {
  padding: 32px 0;
}

.state-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 32px;
  text-align: center;
}

.state-card strong {
  font-size: 18px;
  color: var(--text);
}

.state-card p {
  margin-top: 8px;
  color: var(--text-muted);
}
</style>
