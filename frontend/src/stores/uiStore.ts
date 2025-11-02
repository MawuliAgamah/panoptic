import { ref } from 'vue'
import { defineStore } from 'pinia'

export type DetailsTab = 'inspector' | 'documents'

export const useUiStore = defineStore('ui', () => {
  const detailsOpen = ref(false)
  const activeTab = ref<DetailsTab>('inspector')

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

  return { detailsOpen, activeTab, openDetails, closeDetails, setActiveTab }
})

