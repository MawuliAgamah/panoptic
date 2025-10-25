import { ref } from 'vue'

// Reactive variables
export const lastResponse = ref(null)
export const lastError = ref('')
export const showFileInput = ref(false)
export const selectedFile = ref<File | null>(null)
export const fileInput = ref<HTMLInputElement>()

const BASE_URL = 'http://127.0.0.1:8001'

// Test health endpoint - Fixed: Use /health not /api/health
export const testHealth = async () => {
    try {
        lastError.value = ''
        console.log('Making health check request to:', `${BASE_URL}/health`)
        
        const response = await fetch(`${BASE_URL}/health`)
        console.log('Health check response status:', response.status)
        console.log('Health check response headers:', response.headers)
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        lastResponse.value = data
        console.log('Health check response data:', data)
    } catch (error) {
        lastError.value = `Health check failed: ${error}`
        console.error('Health check error:', error)
    }
}

// Test basic API endpoint
export const testEndpoint = async () => {
    try {
        lastError.value = ''
        console.log('Making test endpoint request to:', `${BASE_URL}/api/test`)
        
        const response = await fetch(`${BASE_URL}/api/test`)
        console.log('Test endpoint response status:', response.status)
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        lastResponse.value = data
        console.log('Test endpoint response data:', data)
    } catch (error) {
        lastError.value = `Test endpoint failed: ${error}`
        console.error('Test endpoint error:', error)
    }
}

// Test echo POST endpoint
export const testEcho = async () => {
    try {
        lastError.value = ''
        const testMessage = {
            message: "Hello from frontend!",
            timestamp: new Date().toISOString(),
            test_data: { key1: "value1", key2: 123 }
        }
        
        const response = await fetch(`${BASE_URL}/api/echo`, {
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
    if (target.files && target.files.length > 0) {
        selectedFile.value = target.files[0]
    }
}

// Upload selected file
export const uploadSelectedFile = async () => {
    if (!selectedFile.value) {
        lastError.value = 'No file selected'
        return
    }
    
    try {
        lastError.value = ''
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('domain', 'test')
        formData.append('tags', JSON.stringify(['frontend', 'test'])) // Server expects JSON string
        formData.append('document_id', `test_${Date.now()}`) // Add document ID
        
        const response = await fetch(`${BASE_URL}/api/extract-kg`, {
            method: 'POST',
            body: formData
        })
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        lastResponse.value = data
        console.log('Upload response:', data)
        
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