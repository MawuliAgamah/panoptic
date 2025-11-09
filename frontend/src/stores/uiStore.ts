import { ref } from 'vue'
import { defineStore } from 'pinia'

export type DetailsTab = 'inspector' | 'documents'

export const useUiStore = defineStore('ui', () => {
  const detailsOpen = ref(false)
  const activeTab = ref<DetailsTab>('inspector')
  // Bottom dataset drawer
  const dataDrawerOpen = ref(false)

  function openDetails(tab?: DetailsTab) {
    if (tab) activeTab.value = tab
    detailsOpen.value = true
  }

  function closeDetails() {
    detailsOpen.value = false
  }

  function setActiveTab(tab: DetailsTab) {
    activeTab.value = tab
  }

  function openDataDrawer() {
    dataDrawerOpen.value = true
  }

  function closeDataDrawer() {
    dataDrawerOpen.value = false
  }

  function toggleDataDrawer() {
    dataDrawerOpen.value = !dataDrawerOpen.value
  }

  return {
    detailsOpen,
    activeTab,
    openDetails,
    closeDetails,
    setActiveTab,
    // dataset drawer
    dataDrawerOpen,
    openDataDrawer,
    closeDataDrawer,
    toggleDataDrawer
  }
})
