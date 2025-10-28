<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @keydown.esc="handleClose" tabindex="-1">
      <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="node-dialog-title">
        <header class="dialog__header">
          <h2 id="node-dialog-title">Create Node</h2>
          <button class="dialog__close" type="button" @click="handleClose">×</button>
        </header>

        <form class="dialog__form" @submit.prevent="handleSubmit">
          <label class="dialog__label" for="node-label">Label</label>
          <input
            id="node-label"
            v-model="formState.label"
            class="dialog__input"
            placeholder="e.g. Machine Learning"
            required
          />

          <label class="dialog__label" for="node-type">Type</label>
          <select id="node-type" v-model="formState.type" class="dialog__input">
            <option v-for="option in NODE_TYPES" :key="option" :value="option">
              {{ option }}
            </option>
          </select>

          <label class="dialog__label" for="node-description">Description</label>
          <textarea
            id="node-description"
            v-model="formState.description"
            class="dialog__input dialog__textarea"
            rows="3"
            placeholder="Optional context for this node."
          />

          <div class="dialog__footer">
            <button class="dialog__button dialog__button--ghost" type="button" @click="handleClose">
              Cancel
            </button>
            <button class="dialog__button" type="submit">Create</button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { NodeType } from '@/types/graph'

const NODE_TYPES: NodeType[] = ['person', 'organization', 'concept', 'event', 'location', 'other']
const DEFAULT_NODE_TYPE: NodeType = 'concept'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (
    event: 'submit',
    payload: { label: string; type: NodeType; description?: string }
  ): void
}>()

const formState = reactive({
  label: '',
  type: DEFAULT_NODE_TYPE,
  description: ''
})

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      formState.label = ''
      formState.type = DEFAULT_NODE_TYPE
      formState.description = ''
    }
  }
)

function handleClose() {
  emit('close')
}

function handleSubmit() {
  if (!formState.label) return
  emit('submit', {
    label: formState.label,
    type: formState.type,
    description: formState.description || undefined
  })
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(11, 19, 33, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
}

.dialog {
  width: min(420px, 90vw);
  background: #fff;
  border-radius: 18px;
  padding: 20px 24px;
  box-shadow: 0 24px 60px rgba(15, 49, 103, 0.25);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog__close {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
  color: rgba(18, 20, 23, 0.5);
}

.dialog__form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dialog__label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(18, 20, 23, 0.6);
}

.dialog__input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 49, 103, 0.2);
  font-size: 14px;
}

.dialog__textarea {
  resize: vertical;
}

.dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.dialog__button {
  padding: 8px 16px;
  border-radius: 10px;
  border: none;
  background: #0f3167;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.dialog__button--ghost {
  background: rgba(15, 49, 103, 0.12);
  color: #0f3167;
}
</style>
