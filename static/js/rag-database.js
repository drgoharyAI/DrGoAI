// RAG Database Management - Complete Implementation
const API_BASE = '/api/v1/rag';
let selectedFiles = [];
let deleteTarget = null;
let chatHistory = [];

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
  setupEventListeners();
  loadStats();
  loadDocuments();
  checkHealth();
});

// Initialize application
function initializeApp() {
  console.log('RAG Database Management initialized');
}

// Setup all event listeners
function setupEventListeners() {
  // Upload area
  const uploadArea = document.getElementById('uploadArea');
  const fileInput = document.getElementById('fileInput');
  
  uploadArea.addEventListener('click', () => fileInput.click());
  uploadArea.addEventListener('dragover', handleDragOver);
  uploadArea.addEventListener('dragleave', handleDragLeave);
  uploadArea.addEventListener('drop', handleDrop);
  
  fileInput.addEventListener('change', handleFileSelect);
  
  // Buttons
  document.getElementById('uploadBtn').addEventListener('click', uploadFiles);
  document.getElementById('refreshDocsBtn').addEventListener('click', loadDocuments);
  document.getElementById('reindexBtn').addEventListener('click', reindexDocuments);
  document.getElementById('clearDbBtn').addEventListener('click', showClearDbModal);
  document.getElementById('confirmClearDbBtn').addEventListener('click', clearDatabase);
  document.getElementById('confirmDeleteBtn').addEventListener('click', deleteDocument);
  
  // Chat
  document.getElementById('chatForm').addEventListener('submit', handleChatSubmit);
  
  // Clear DB modal checkbox
  document.getElementById('clearConfirmCheck').addEventListener('change', (e) => {
    document.getElementById('confirmClearDbBtn').disabled = !e.target.checked;
  });
}

// Drag and drop handlers
function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.remove('dragover');
  
  const files = Array.from(e.dataTransfer.files);
  processSelectedFiles(files);
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  processSelectedFiles(files);
}

function processSelectedFiles(files) {
  selectedFiles = files.filter(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return ['pdf', 'docx', 'txt', 'md'].includes(ext);
  });
  
  if (selectedFiles.length === 0) {
    showAlert('No valid files selected. Supported: PDF, DOCX, TXT, MD', 'warning');
    return;
  }
  
  displaySelectedFiles();
  document.getElementById('uploadBtn').disabled = false;
}

function displaySelectedFiles() {
  const fileList = document.getElementById('fileList');
  const uploadQueue = document.getElementById('uploadQueue');
  
  fileList.innerHTML = selectedFiles.map(f => `
    <div class="badge bg-secondary me-2 mb-2">
      <i class="fas fa-file"></i> ${f.name} (${(f.size / 1024).toFixed(1)} KB)
    </div>
  `).join('');
  
  uploadQueue.style.display = 'block';
}

// Upload files
async function uploadFiles() {
  if (selectedFiles.length === 0) return;
  
  const uploadBtn = document.getElementById('uploadBtn');
  const progressDiv = document.getElementById('uploadProgress');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  
  uploadBtn.disabled = true;
  progressDiv.style.display = 'block';
  progressBar.style.width = '0%';
  
  const formData = new FormData();
  selectedFiles.forEach(file => formData.append('files', file));
  formData.append('policy_type', document.getElementById('policyType').value);
  formData.append('policy_version', document.getElementById('policyVersion').value);
  formData.append('auto_process', 'true');
  
  try {
    progressBar.style.width = '50%';
    progressText.textContent = 'Uploading and processing...';
    
    const response = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    progressBar.style.width = '100%';
    progressText.textContent = 'Complete!';
    
    if (result.uploaded_count > 0) {
      showAlert(`Successfully uploaded ${result.uploaded_count} file(s)`, 'success');
      selectedFiles = [];
      document.getElementById('uploadQueue').style.display = 'none';
      document.getElementById('fileInput').value = '';
      await loadStats();
      await loadDocuments();
    }
    
    if (result.failed_count > 0) {
      const failed = result.results.filter(r => r.status === 'error');
      showAlert(`Failed to upload ${result.failed_count} file(s): ${failed.map(f => f.filename).join(', ')}`, 'warning');
    }
    
  } catch (error) {
    console.error('Upload error:', error);
    showAlert('Error uploading files: ' + error.message, 'danger');
  } finally {
    setTimeout(() => {
      progressDiv.style.display = 'none';
      uploadBtn.disabled = false;
    }, 2000);
  }
}

// Load statistics
async function loadStats() {
  try {
    const response = await fetch(`${API_BASE}/database/stats`);
    const data = await response.json();
    
    if (!data.initialized) {
      // System not initialized - show error
      document.getElementById('statDocs').textContent = '0';
      document.getElementById('statChunks').textContent = '0';
      document.getElementById('statSize').textContent = '0.00 MB';
      
      const errorMsg = data.error || 'Not initialized';
      document.getElementById('statModel').textContent = 'Error';
      document.getElementById('statModel').title = errorMsg;
      
      showAlert(`RAG System Error: ${errorMsg}. Check logs for details.`, 'danger');
      return;
    }
    
    document.getElementById('statDocs').textContent = data.unique_documents || 0;
    document.getElementById('statChunks').textContent = data.total_chunks || 0;
    
    // Calculate total size from documents
    let totalSize = 0;
    if (data.documents && Array.isArray(data.documents)) {
      totalSize = data.documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0);
    }
    document.getElementById('statSize').textContent = (totalSize / (1024 * 1024)).toFixed(2) + ' MB';
    
    const modelName = data.embedding_model || 'Not loaded';
    document.getElementById('statModel').textContent = modelName.split('/').pop();
    
  } catch (error) {
    console.error('Error loading stats:', error);
    showAlert('Failed to load statistics. Is the server running?', 'danger');
  }
}

// Load documents list
async function loadDocuments() {
  try {
    const response = await fetch(`${API_BASE}/documents`);
    const data = await response.json();
    
    const docsList = document.getElementById('documentsList');
    
    if (!data.documents || data.documents.length === 0) {
      docsList.innerHTML = `
        <div class="text-center text-muted py-4">
          <i class="fas fa-folder-open fa-3x mb-2"></i>
          <p>No documents uploaded</p>
        </div>
      `;
      return;
    }
    
    docsList.innerHTML = data.documents.map(doc => `
      <div class="doc-item border-bottom p-3">
        <div class="d-flex justify-content-between align-items-start">
          <div class="flex-grow-1">
            <h6 class="mb-1">
              <i class="fas fa-file-${getFileIcon(doc.extension)} me-2"></i>
              ${doc.filename}
            </h6>
            <div class="small text-muted">
              <span><i class="fas fa-hdd"></i> ${doc.file_size_mb} MB</span>
              <span class="ms-3"><i class="fas fa-clock"></i> ${formatDate(doc.created_at)}</span>
            </div>
          </div>
          <button class="btn btn-sm btn-outline-danger" onclick="showDeleteModal('${doc.filename}')">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    `).join('');
    
  } catch (error) {
    console.error('Error loading documents:', error);
    showAlert('Error loading documents', 'danger');
  }
}

// Get file icon based on extension
function getFileIcon(ext) {
  const icons = {
    '.pdf': 'pdf',
    '.docx': 'word',
    '.txt': 'text',
    '.md': 'markdown'
  };
  return icons[ext] || 'alt';
}

// Format date
function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Show delete modal
function showDeleteModal(filename) {
  deleteTarget = filename;
  document.getElementById('deleteFilename').textContent = filename;
  new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

// Delete document
async function deleteDocument() {
  if (!deleteTarget) return;
  
  try {
    const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(deleteTarget)}?delete_from_db=true`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    
    if (result.success) {
      showAlert(`Deleted ${deleteTarget} and ${result.chunks_deleted} chunks`, 'success');
      bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
      await loadStats();
      await loadDocuments();
    } else {
      showAlert('Error deleting document', 'danger');
    }
    
  } catch (error) {
    console.error('Delete error:', error);
    showAlert('Error deleting document: ' + error.message, 'danger');
  }
}

// Show clear database modal
function showClearDbModal() {
  document.getElementById('clearConfirmCheck').checked = false;
  document.getElementById('confirmClearDbBtn').disabled = true;
  new bootstrap.Modal(document.getElementById('clearDbModal')).show();
}

// Clear database
async function clearDatabase() {
  try {
    const response = await fetch(`${API_BASE}/database/clear?confirm=true`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    
    if (result.success) {
      showAlert(`Database cleared: ${result.chunks_deleted} chunks deleted`, 'warning');
      bootstrap.Modal.getInstance(document.getElementById('clearDbModal')).hide();
      await loadStats();
      chatHistory = [];
      displayChatWelcome();
    } else {
      showAlert('Error clearing database', 'danger');
    }
    
  } catch (error) {
    console.error('Clear database error:', error);
    showAlert('Error clearing database: ' + error.message, 'danger');
  }
}

// Reindex documents
async function reindexDocuments() {
  const btn = document.getElementById('reindexBtn');
  const originalHTML = btn.innerHTML;
  
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Reindexing...';
  
  try {
    const response = await fetch(`${API_BASE}/database/reindex`, {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (result.success) {
      showAlert(`Reindexed ${result.files_processed} files, ${result.total_chunks} chunks`, 'success');
      await loadStats();
    } else {
      showAlert('Error reindexing documents', 'danger');
    }
    
  } catch (error) {
    console.error('Reindex error:', error);
    showAlert('Error reindexing: ' + error.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
  }
}

// Chat functionality
function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  
  if (!query) return;
  
  input.value = '';
  addChatMessage(query, 'user');
  sendChatQuery(query);
}

function addChatMessage(content, role) {
  const chatContainer = document.getElementById('chatContainer');
  
  // Remove welcome message if exists
  if (chatHistory.length === 0) {
    chatContainer.innerHTML = '';
  }
  
  chatHistory.push({ role, content });
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message chat-${role}`;
  
  if (role === 'user') {
    messageDiv.innerHTML = `
      <div class="d-flex align-items-start">
        <i class="fas fa-user-circle fa-2x text-primary me-2"></i>
        <div class="flex-grow-1">
          <strong>You</strong>
          <p class="mb-0 mt-1">${escapeHtml(content)}</p>
        </div>
      </div>
    `;
  } else {
    messageDiv.innerHTML = `
      <div class="d-flex align-items-start">
        <i class="fas fa-robot fa-2x text-success me-2"></i>
        <div class="flex-grow-1">
          <strong>RAG Assistant</strong>
          ${content}
        </div>
      </div>
    `;
  }
  
  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendChatQuery(query) {
  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;
  sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  
  // Add loading message
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'chat-message chat-assistant';
  loadingDiv.id = 'loading-message';
  loadingDiv.innerHTML = `
    <div class="d-flex align-items-start">
      <i class="fas fa-robot fa-2x text-success me-2"></i>
      <div class="flex-grow-1">
        <strong>RAG Assistant</strong>
        <p class="mb-0 mt-1"><i class="fas fa-spinner fa-spin"></i> Searching documents...</p>
      </div>
    </div>
  `;
  document.getElementById('chatContainer').appendChild(loadingDiv);
  
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query: query,
        top_k: 5,
        include_metadata: true
      })
    });
    
    const result = await response.json();
    
    // Remove loading message
    loadingDiv.remove();
    
    // Format response with sources
    let formattedAnswer = `<p class="mb-2">${escapeHtml(result.answer || 'No relevant information found.')}</p>`;
    
    if (result.sources && result.sources.length > 0) {
      formattedAnswer += '<div class="mt-3"><small class="text-muted"><strong>Sources:</strong></small>';
      result.sources.forEach((source, idx) => {
        const confidence = (source.relevance_score * 100).toFixed(0);
        const confidenceColor = confidence > 70 ? 'success' : confidence > 50 ? 'warning' : 'secondary';
        formattedAnswer += `
          <div class="mt-2 p-2 bg-light rounded">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <small class="fw-bold">[${idx + 1}] ${escapeHtml(source.source.split('/').pop())}</small>
              <span class="badge bg-${confidenceColor}">${confidence}%</span>
            </div>
            <small class="text-muted">${escapeHtml(source.content)}</small>
          </div>
        `;
      });
      formattedAnswer += '</div>';
      
      formattedAnswer += `<div class="mt-2"><small class="text-muted">Average confidence: ${(result.average_confidence * 100).toFixed(0)}%</small></div>`;
    }
    
    addChatMessage(formattedAnswer, 'assistant');
    
  } catch (error) {
    console.error('Chat error:', error);
    loadingDiv.remove();
    addChatMessage('<p class="text-danger">Error processing query. Please try again.</p>', 'assistant');
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
  }
}

function displayChatWelcome() {
  const chatContainer = document.getElementById('chatContainer');
  chatContainer.innerHTML = `
    <div class="text-center text-muted py-5">
      <i class="fas fa-robot fa-3x mb-3"></i>
      <h5>Ask about your documents!</h5>
      <p class="small">I'll search and provide answers with references.</p>
    </div>
  `;
}

// Check system health
async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    
    const statusEl = document.getElementById('dbStatus');
    
    if (data.status === 'healthy' && data.initialized) {
      statusEl.innerHTML = '<i class="fas fa-circle text-success"></i> <span>Online</span>';
      statusEl.title = 'RAG system operational';
    } else if (data.status === 'error') {
      statusEl.innerHTML = '<i class="fas fa-circle text-danger"></i> <span>Error</span>';
      statusEl.title = data.error || 'Initialization failed';
      
      // Show detailed error only once
      if (!sessionStorage.getItem('rag_error_shown')) {
        showAlert(`RAG System Error: ${data.error || 'Unknown error'}. Please check server logs.`, 'danger');
        sessionStorage.setItem('rag_error_shown', 'true');
      }
    } else {
      statusEl.innerHTML = '<i class="fas fa-circle text-warning"></i> <span>Initializing</span>';
      statusEl.title = 'System starting up...';
      
      // Retry after a delay
      setTimeout(checkHealth, 5000);
    }
    
  } catch (error) {
    const statusEl = document.getElementById('dbStatus');
    statusEl.innerHTML = '<i class="fas fa-circle text-danger"></i> <span>Offline</span>';
    statusEl.title = 'Cannot connect to server';
    console.error('Health check error:', error);
  }
}

// Utility functions
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showAlert(message, type = 'info') {
  const alertContainer = document.getElementById('alertContainer');
  const alertId = 'alert-' + Date.now();
  
  const alert = document.createElement('div');
  alert.id = alertId;
  alert.className = `alert alert-${type} alert-dismissible fade show mx-4 mt-3`;
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  
  alertContainer.appendChild(alert);
  
  setTimeout(() => {
    const alertEl = document.getElementById(alertId);
    if (alertEl) {
      bootstrap.Alert.getInstance(alertEl)?.close();
    }
  }, 5000);
}

// Auto-refresh stats every 30 seconds
setInterval(loadStats, 30000);
