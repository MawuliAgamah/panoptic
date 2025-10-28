<template>
  <Teleport to="body">
    <div
      v-if="visible && position"
      class="context-menu"
      :style="{
        top: `${position.y}px`,
        left: `${position.x}px`
      }"
      @click.stop
    >
      <header class="context-menu__header">
        <h4>{{ nodeLabel }}</h4>
        <p>Node actions</p>
      </header>
      <ul class="context-menu__list">
        <li>
          <button type="button" @click="handleAction('link')">Link document…</button>
        </li>
        <li>
          <button type="button" @click="handleAction('extract')">Extract knowledge</button>
        </li>
        <li>
          <button type="button" @click="handleAction('merge')">Merge with another node…</button>
        </li>
      </ul>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{
  visible: boolean
  position: { x: number; y: number } | null
  nodeLabel: string
}>()

const emit = defineEmits<{
  (event: 'action', payload: 'link' | 'extract' | 'merge'): void
}>()

function handleAction(action: 'link' | 'extract' | 'merge') {
  emit('action', action)
}
</script>

<style scoped>
.context-menu {
  position: fixed;
  min-width: 220px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(15, 49, 103, 0.15);
  box-shadow: 0 18px 40px rgba(15, 49, 103, 0.2);
  padding: 12px;
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.context-menu__header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f3167;
}

.context-menu__header p {
  margin: 0;
  font-size: 12px;
  color: rgba(18, 20, 23, 0.6);
}

.context-menu__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.context-menu__list li {
  margin: 0;
}

.context-menu__list button {
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border: none;
  background: transparent;
  font-size: 13px;
  border-radius: 8px;
  color: #0f3167;
  cursor: pointer;
}

.context-menu__list button:hover {
  background: rgba(15, 49, 103, 0.08);
}
</style>
