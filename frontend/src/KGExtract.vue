<template>
    <div class="kg-extract-container">
        <h1>KG Extract</h1>
        <div class="test-controls">
            <h3>Backend API Tests</h3>
                <div class="button-group">
                    <button @click="testHealth" class="test-btn">Test Health Check</button>
                    <button @click="testEndpoint" class="test-btn">Test API Endpoint</button>
                    <button @click="testEcho" class="test-btn">Test Echo (POST)</button>
                    <button @click="testFileUpload" class="test-btn">Test File Upload</button>
                </div>
            <!-- File input for testing upload -->
            <div class="file-upload" v-if="showFileInput">
                <input type="file" ref="fileInput" @change="onFileSelected" />
                <button @click="uploadSelectedFile" class="test-btn" :disabled="!selectedFile">Upload File</button>
            </div>
            <!-- Response display -->
            <div class="response-display" v-if="lastResponse">
                <h4>Last Response:</h4>
                <pre>{{ JSON.stringify(lastResponse, null, 2) }}</pre>
            </div>
            <!-- Error display -->
            <div class="error-display" v-if="lastError">
                <h4>Error:</h4>
                <pre>{{ lastError }}</pre>
            </div>
        </div>
        <div class="main-content">
                <div class="vis-container">
                </div>
                <div class="side_bar">      
                </div>
            <div class="setting"> </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { 
    lastResponse, 
    lastError, 
    showFileInput, 
    selectedFile, 
    fileInput,
    testHealth, 
    testEndpoint, 
    testEcho, 
    testFileUpload, 
    onFileSelected, 
    uploadSelectedFile 
} from './api'
</script>

<style scoped>

/* -------------------------------------------------------------- */

.kg-extract-container{
    overflow: hidden;
    width: 100%;
    display: flex;
    flex-direction: column;
}

.test-controls {
    background: #f5f5f5;
    padding-top: 20px;
    padding: 20px;
    /* margin-bottom: 20px; */
    border-radius: 8px;
    border: 1px solid #ddd;
}

.test-controls h3 {
    margin-top: 0;
    color: #333;
}

.button-group {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 20px;
    margin-bottom: 20px;
}

.test-btn {
    padding: 10px 20px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.2s;
}

.test-btn:hover:not(:disabled) {
    background: #0056b3;
}

.test-btn:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

.file-upload {
    background: #e9ecef;
    padding: 15px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.file-upload input[type="file"] {
    margin-right: 10px;
    margin-bottom: 10px;
}

.response-display {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 10px;
}

.response-display h4 {
    margin-top: 0;
    color: #155724;
}

.response-display pre {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
}

.error-display {
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 10px;
}

.error-display h4 {
    margin-top: 0;
    color: #721c24;
}

.error-display pre {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
    color: #721c24;
}



/* -------------------------------------------------------------- */

.main-content {
    display: flex;
    flex-direction: row;
    justify-content: center;
    height: 500px;
    width: 100%;
}

.vis-container {
    border-style: solid;
    border-color: black;
    border-width: 1px;
    border-radius: 4px; 
    margin-top: 40px;
    width: 100%;
}
.side_bar {
    border-style: solid;
    border-color: black;
    border-radius: 4px;
    border-width: 1px;
    margin-top: 40px;
    width: 80px;
    margin-left: 80px;
    
}
</style>