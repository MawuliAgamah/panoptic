import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import OntologyCreator from '@/views/OntologyCreator.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/ontology-creator',
      name: 'ontologyCreator',
      component: OntologyCreator
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: { name: 'dashboard' }
    }
  ]
})

export default router
