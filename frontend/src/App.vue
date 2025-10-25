<script setup lang="ts"></script>
<template>
<div class="main">
    <router-view />
</div>
</template>
<style>

.main {
  min-height: 100vh;
  flex-direction: column;
  width: 100%;
  padding: 20px;
  min-width: 1000px;
  font-family: 'Space Mono', monospace;
}
body {
  font-family: 'Space Mono', monospace;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 5rem 0;
}

* {
  font-family: 'Space Mono', monospace;
  margin: 0;
  padding: 0;
}


</style>
