<script setup lang="ts"></script>
<template>
<div class="main">
    <router-view />
</div>
</template>
<style>

.main {
  min-height: 100vh;
  max-width: 100vw;
  flex-direction: column;
  width: 100%;
  padding: 20px;
  overflow-y: hidden;
  /* min-width: 1000px; */
  font-family: 'Space Mono', monospace;

}
body {
  height: 100vh;
  overflow: hidden;
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
