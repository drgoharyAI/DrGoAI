// Patch for RAG Database - Handle initialization gracefully

async function loadStats() {
  try {
    const response = await fetch('/api/v1/rag/stats');
    const data = await response.json();
    
    if (!data.initialized) {
      document.getElementById('totalDocs').textContent = 0;
      document.getElementById('totalChunks').textContent = 0;
      document.getElementById('totalSize').textContent = '0.00 MB';
      document.getElementById('embeddingModel').textContent = 'Not Initialized';
      
      showAlert(
        `RAG System Status: ${data.stats.error || 'Initializing...'}. ` +
        `This is normal on first startup. Upload documents to activate.`,
        'info',
        10000
      );
      return;
    }
    
    // RAG initialized - show stats
    const stats = data.stats;
    document.getElementById('totalDocs').textContent = stats.total_documents || 0;
    document.getElementById('totalChunks').textContent = stats.total_chunks || 0;
    document.getElementById('totalSize').textContent = (stats.total_size_mb || 0).toFixed(2) + ' MB';
    document.getElementById('embeddingModel').textContent = stats.embedding_model || 'Default';
    
  } catch (error) {
    console.error('Error loading stats:', error);
    document.getElementById('totalDocs').textContent = 0;
    document.getElementById('totalChunks').textContent = 0;
    document.getElementById('totalSize').textContent = '0.00 MB';
    document.getElementById('embeddingModel').textContent = 'Error';
  }
}

async function checkHealth() {
  try {
    const response = await fetch('/api/v1/rag/health');
    const data = await response.json();
    
    if (!data.initialized && data.error) {
      console.warn('RAG not initialized:', data.error);
    }
  } catch (error) {
    console.error('Health check error:', error);
  }
}

async function loadDocuments() {
  try {
    const tableBody = document.getElementById('documentsTable');
    if (!tableBody) return;
    
    const response = await fetch('/api/v1/rag/documents');
    const data = await response.json();
    
    if (!data.initialized) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4">
            <div class="text-muted">
              <i class="fas fa-info-circle"></i> RAG System initializing...
              <br><small>Upload documents to get started</small>
            </div>
          </td>
        </tr>
      `;
      return;
    }
    
    if (!data.documents || data.documents.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4">
            <div class="text-muted">
              <i class="fas fa-inbox"></i> No documents yet
              <br><small>Upload documents using the form above</small>
            </div>
          </td>
        </tr>
      `;
      return;
    }
    
    tableBody.innerHTML = data.documents.map((doc, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${doc.id || 'N/A'}</td>
        <td>${doc.metadata?.filename || 'Unknown'}</td>
        <td>${(doc.metadata?.size || 0) / 1024 | 0} KB</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="deleteDoc('${doc.id}')">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading documents:', error);
  }
}

function showAlert(message, type = 'info', duration = 4000) {
  const alertHTML = document.getElementById('alertContainer') || createAlertContainer();
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} fade-in`;
  alert.innerHTML = `
    <i class="fas fa-${getAlertIcon(type)}"></i>
    <div>${message}</div>
  `;
  alertHTML.appendChild(alert);
  
  if (duration > 0) {
    setTimeout(() => alert.remove(), duration);
  }
}

function getAlertIcon(type) {
  const icons = {
    'success': 'check-circle',
    'danger': 'exclamation-circle',
    'warning': 'exclamation-triangle',
    'info': 'info-circle'
  };
  return icons[type] || 'info-circle';
}

function createAlertContainer() {
  const container = document.createElement('div');
  container.id = 'alertContainer';
  container.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 9999;
    max-width: 400px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  `;
  document.body.appendChild(container);
  return container;
}

// Override interval to be more friendly on initialization
setInterval(loadStats, 30000);
setTimeout(() => checkHealth(), 1000);
