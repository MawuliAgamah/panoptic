<template>
  <div class="dashboard-shell">
    <TopNav />
    <div class="dashboard-shell__body">
      <Sidebar />
      <main class="dashboard-shell__main">
        <slot>
          <GraphCanvas />
        </slot>
      </main>
      <DetailsPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import TopNav from './TopNav.vue'
import Sidebar from './Sidebar.vue'
import DetailsPanel from './DetailsPanel.vue'
import GraphCanvas from '../graph/GraphCanvas.vue'
</script>

<style scoped>
.dashboard-shell {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.dashboard-shell__body {
  flex: 1;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0;
  min-height: 0;
  overflow: hidden;
}

.dashboard-shell__main {
  display: flex;
  padding: 24px;
}

@media (max-width: 1400px) {
  .dashboard-shell__body {
    grid-template-columns: 300px minmax(0, 1fr) 320px;
  }
}
</style>
