import { createRouter, createWebHistory } from 'vue-router'
import Home from './Home.vue'
import KG_Extract from './KGExtract.vue'


const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/visualisation',
    name: 'visualisation',
    component: KG_Extract
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router