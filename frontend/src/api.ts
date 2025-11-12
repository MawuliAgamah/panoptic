import { ref } from 'vue'

// Reactive variables
export const lastResponse = ref(null)
export const lastError = ref('')
export const showFileInput = ref(false)
export const selectedFile = ref<File | null>(null)
export const fileInput = ref<HTMLInputElement | null>(null)

const API_BASE_URL = (import.meta as any).env?.VITE_BACKEND_URL ?? 'http://127.0.0.1:8001'



// Test echo POST endpoint
export const testEcho = async () => {
    try {
        lastError.value = ''
        const testMessage = {
            message: "Hello from frontend!",
            timestamp: new Date().toISOString(),
            test_data: { key1: "value1", key2: 123 }
        }
        
        const response = await fetch(`${API_BASE_URL}/api/echo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(testMessage)
        })
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        lastResponse.value = data
        console.log('Echo response:', data)
    } catch (error) {
        lastError.value = `Echo test failed: ${error}`
        console.error('Echo error:', error)
    }
}

// Show file input for upload test
export const testFileUpload = () => {
    showFileInput.value = !showFileInput.value
    lastError.value = ''
}

// Handle file selection
export const onFileSelected = (event: Event) => {
    const target = event.target as HTMLInputElement
    const files = target.files
    if (!files || files.length === 0) {
        selectedFile.value = null
        return
    }
    selectedFile.value = files.item(0)
}

// Upload selected file
export const uploadSelectedFile = async () => {
    if (!selectedFile.value) {
        lastError.value = 'No file selected'
        return
    }
    const file = selectedFile.value as File
    
    try {
        lastError.value = ''
        const formData = new FormData()
        formData.append('file', file as Blob, file.name)
        formData.append('domain', 'test')
        formData.append('tags', JSON.stringify(['frontend', 'test'])) // Server expects JSON string
        formData.append('document_id', `test_${Date.now()}`) // Add document ID
        
        const response = await fetch(`${API_BASE_URL}/api/extract-kg`, {
            method: 'POST',
            body: formData
        })
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        lastResponse.value = data
        
        // Enhanced logging for debugging
        console.log('🔍 Upload response received:', data)
        console.log('🔍 Response success:', data.success)
        console.log('🔍 Response message:', data.message)
        console.log('🔍 Entity count:', data.entity_count)
        console.log('🔍 Relation count:', data.relation_count)
        console.log('🔍 KG data keys:', data.kg_data ? Object.keys(data.kg_data) : 'No kg_data')
        console.log('🔍 First 3 entities:', data.kg_data?.entities?.slice(0, 3))
        console.log('🔍 First 3 relations:', data.kg_data?.relations?.slice(0, 3))
        
        // Reset file input
        selectedFile.value = null
        if (fileInput.value) {
            fileInput.value.value = ''
        }
    } catch (error) {
        lastError.value = `File upload failed: ${error}`
        console.error('Upload error:', error)
    }
}

// Knowledgebase API
export interface CreateKnowledgebasePayload {
  name: string
  owner_id?: string
  description?: string
}

export interface KnowledgebaseModel {
  id: string
  name: string
  slug?: string
  owner_id?: string
  description?: string
}

export async function createKnowledgebase(payload: CreateKnowledgebasePayload): Promise<KnowledgebaseModel> {
  const res = await fetch(`${API_BASE_URL}/api/knowledgebases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    throw new Error(`Failed to create knowledgebase: ${res.status} ${res.statusText}`)
  }
  const data = await res.json() as { success: boolean; knowledgebase: KnowledgebaseModel }
  return data.knowledgebase
}

export interface UploadDocumentResult {
  success: boolean
  message?: string
  document_id?: string // pipeline id
  submitted_document_id?: string
  knowledgebase_id?: string
  filename?: string
  content_type?: string
}

export async function uploadDocument(
  file: File,
  opts: { document_id?: string; knowledgebase_id?: string } = {}
): Promise<UploadDocumentResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  if (opts.document_id) form.append('document_id', opts.document_id)
  if (opts.knowledgebase_id) form.append('knowledgebase_id', opts.knowledgebase_id)

  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    body: form
  })
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`)
  }
  return await res.json() as UploadDocumentResult
}
