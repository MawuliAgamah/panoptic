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
      <ChatSidebar />
    </div>
    <!-- Bottom dataset drawer and toggle -->
    <DataDrawer />
  </div>
</template>

<script setup lang="ts">
import TopNav from './TopNav.vue'
import Sidebar from './Sidebar.vue'
import GraphCanvas from '../graph/GraphCanvas.vue'
import DataDrawer from './DataDrawer.vue'
import ChatSidebar from './ChatSidebar.vue'
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
  /* Ensure the working area fits in one viewport height below the top nav */
  height: calc(100vh - var(--topnav-height, 64px));
}

.dashboard-shell__main {
  display: flex;
  flex-direction: column;
  padding: 24px;
  min-height: 0;
}

@media (max-width: 1400px) {
  .dashboard-shell__body {
    grid-template-columns: 300px minmax(0, 1fr) auto;
  }
}
</style>
