<template>
  <aside class="chat-sidebar" :class="{ 'is-drawer-open': dataDrawerOpen }">
    <header class="chat-sidebar__header">
      <h2 class="chat-sidebar__title">Chat</h2>
      <p class="chat-sidebar__subtitle">Ask the knowledge graph</p>
    </header>

    <div class="chat-sidebar__messages" ref="messagesRef">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', `msg--${m.role}`]">
        <div class="msg__bubble">{{ m.content }}</div>
      </div>
    </div>

    <form class="chat-sidebar__composer" @submit.prevent="handleSend">
      <input
        v-model="draft"
        class="composer__input"
        type="text"
        placeholder="Type a message…"
        autocomplete="off"
      />
      <button class="composer__send" type="submit" :disabled="!draft.trim()">Send</button>
    </form>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useUiStore } from '@/stores/uiStore'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

const messages = ref<ChatMessage[]>([
  { role: 'assistant', content: 'Hi! Ask me about nodes, edges, or documents.' }
])

const draft = ref('')
const messagesRef = ref<HTMLElement | null>(null)

// Respect bottom dataset drawer so the composer stays visible
const ui = useUiStore()
const { dataDrawerOpen } = storeToRefs(ui)

function handleSend() {
  const text = draft.value.trim()
  if (!text) return
  messages.value.push({ role: 'user', content: text })
  draft.value = ''

  // Placeholder response (no backend wiring here)
  messages.value.push({ role: 'assistant', content: 'This is a placeholder response.' })

  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
</script>

<style scoped>
.chat-sidebar {
  width: 360px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
  padding: var(--space-14);
  background: var(--surface-1);
  border-left: 1px solid var(--border);
  box-shadow: inset 1px 0 0 var(--border-subtle);
  min-height: 0; /* allow internal scrolling in grid */
}

.chat-sidebar.is-drawer-open { padding-bottom: calc(40vh + 8px); }

.chat-sidebar__header { display: flex; flex-direction: column; gap: 4px; }
.chat-sidebar__title { font-size: var(--font-size-14); font-weight: var(--font-weight-bold); color: var(--color-brand-700); }
.chat-sidebar__subtitle { font-size: var(--font-size-12); color: var(--text-muted); }

.chat-sidebar__messages {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 4px;
}

.msg { display: flex; }
.msg--user { justify-content: flex-end; }
.msg--assistant { justify-content: flex-start; }
.msg__bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: var(--font-size-13);
  line-height: 1.4;
}
.msg--user .msg__bubble { background: var(--action-bg); color: var(--action-fg); border: 1px solid var(--action-bg); border-top-right-radius: 4px; }
.msg--assistant .msg__bubble { background: var(--surface-muted); color: var(--text); border: 1px solid var(--border); border-top-left-radius: 4px; }

.chat-sidebar__composer {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  position: sticky;
  bottom: 0;
  background: var(--surface-1);
}
.composer__input {
  flex: 1 1 auto;
  padding: 10px 12px;
  border-radius: var(--radius-10);
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text);
}
.composer__input::placeholder { color: var(--text-subtle); }
.composer__input:focus { outline: none; box-shadow: var(--focus-ring); }
.composer__send {
  padding: 10px 14px;
  border-radius: var(--radius-10);
  border: 1px solid var(--action-bg);
  background: var(--action-bg);
  color: var(--action-fg);
  font-weight: var(--font-weight-medium);
}

@media (max-width: 1200px) {
  .chat-sidebar { width: 320px; }
}
</style>
