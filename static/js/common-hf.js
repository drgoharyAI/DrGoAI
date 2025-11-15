// ============================================================================
// DrGoAi - API Client (HuggingFace Spaces Ready)
// ============================================================================

class APIClient {
  constructor() {
    // HF Spaces: Use relative paths
    this.baseUrl = this.getBaseUrl();
    this.headers = {
      'Content-Type': 'application/json'
    };
    console.log(`[API] Base URL: ${this.baseUrl}`);
  }

  getBaseUrl() {
    // For HF Spaces, use relative paths
    if (window.location.hostname.includes('huggingface.co')) {
      return '';  // Relative to current domain
    }
    // For local development
    return '';  // Always relative
  }

  getEndpointUrl(endpoint) {
    if (endpoint.startsWith('/api/v1/')) {
      return endpoint;
    }
    if (endpoint.includes('rag') || endpoint.includes('database')) {
      return `/api/v1/rag${endpoint}`;
    }
    if (endpoint.includes('fhir')) {
      return `/api/v1/fhir${endpoint}`;
    }
    return `/api/v1/management${endpoint}`;
  }

  async request(method, endpoint, data = null) {
    try {
      const url = this.getEndpointUrl(endpoint);
      const fullUrl = `${this.baseUrl}${url}`;
      
      const options = {
        method,
        headers: this.headers,
        credentials: 'include'  // Include cookies for CORS
      };

      if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
      }

      console.log(`[API] ${method} ${fullUrl}`);
      const response = await fetch(fullUrl, options);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API ERROR] ${response.status}:`, errorText);
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data_resp = await response.json();
      console.log(`[API OK] ${method} ${url}:`, data_resp);
      return data_resp;
    } catch (error) {
      console.error(`[API FAILED] ${endpoint}:`, error);
      throw error;
    }
  }

  get(endpoint) { return this.request('GET', endpoint); }
  post(endpoint, data) { return this.request('POST', endpoint, data); }
  put(endpoint, data) { return this.request('PUT', endpoint, data); }
  delete(endpoint) { return this.request('DELETE', endpoint); }

  async uploadFile(endpoint, file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const url = this.getEndpointUrl(endpoint);
      const fullUrl = `${this.baseUrl}${url}`;

      const response = await fetch(fullUrl, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (!response.ok) throw new Error(`Upload Error: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('File Upload Error:', error);
      throw error;
    }
  }
}

const api = new APIClient();

// ============================================================================
// Alert Manager
// ============================================================================

class AlertManager {
  static show(message, type = 'info', duration = 4000) {
    const alertContainer = document.getElementById('alertContainer') || this.createContainer();
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} fade-in`;
    alert.innerHTML = `
      <i class="fas fa-${this.getIcon(type)}"></i>
      <div>
        <div class="alert-heading">${this.getTitle(type)}</div>
        <div>${message}</div>
      </div>
      <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alert);
    const closeBtn = alert.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => alert.remove());
    if (duration > 0) setTimeout(() => alert.remove(), duration);
    return alert;
  }

  static success(message) { this.show(message, 'success'); }
  static error(message) { this.show(message, 'danger', 5000); }
  static warning(message) { this.show(message, 'warning'); }
  static info(message) { this.show(message, 'info'); }

  static createContainer() {
    const container = document.createElement('div');
    container.id = 'alertContainer';
    container.style.cssText = `position: fixed; top: 80px; right: 20px; z-index: 9999; max-width: 400px; display: flex; flex-direction: column; gap: 12px;`;
    document.body.appendChild(container);
    return container;
  }

  static getIcon(type) {
    return {success: 'check-circle', danger: 'exclamation-circle', warning: 'exclamation-triangle', info: 'info-circle'}[type] || 'info-circle';
  }

  static getTitle(type) {
    return {success: 'Success', danger: 'Error', warning: 'Warning', info: 'Information'}[type] || 'Notice';
  }
}

// ============================================================================
// Table Manager
// ============================================================================

class TableManager {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.data = [];
  }

  render(data, columns, actions = null) {
    this.data = data;
    if (!data || data.length === 0) {
      this.showEmpty();
      return;
    }
    const table = document.createElement('table');
    table.className = 'table';
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col.label;
      headerRow.appendChild(th);
    });
    if (actions) {
      const th = document.createElement('th');
      th.textContent = 'Actions';
      th.style.textAlign = 'center';
      headerRow.appendChild(th);
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    data.forEach((row, index) => {
      const tr = document.createElement('tr');
      columns.forEach(col => {
        const td = document.createElement('td');
        const value = row[col.key];
        if (col.render) {
          td.innerHTML = col.render(value, row);
        } else if (col.type === 'badge') {
          td.innerHTML = `<span class="table-badge ${value?.toLowerCase() || ''}">${value || 'N/A'}</span>`;
        } else {
          td.textContent = value || 'N/A';
        }
        tr.appendChild(td);
      });
      if (actions) {
        const td = document.createElement('td');
        td.className = 'table-actions';
        actions.forEach(action => {
          const btn = document.createElement('button');
          btn.className = `btn btn-sm btn-${action.type || 'primary'}`;
          btn.innerHTML = `<i class="fas fa-${action.icon}"></i> ${action.label}`;
          btn.onclick = () => action.handler(row, index);
          td.appendChild(btn);
        });
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    this.container.innerHTML = '';
    this.container.appendChild(table);
  }

  showEmpty(title = 'No Data', message = 'No records found') {
    this.container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon"><i class="fas fa-inbox"></i></div>
        <div class="empty-state-title">${title}</div>
        <div class="empty-state-text">${message}</div>
      </div>
    `;
  }

  showLoading() {
    this.container.innerHTML = `
      <div class="empty-state">
        <div class="loading" style="font-size: 48px; margin: 0 auto 1rem;"></div>
        <div class="empty-state-title">Loading</div>
        <div class="empty-state-text">Please wait...</div>
      </div>
    `;
  }

  showError(message = 'Failed to load data') {
    this.container.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-circle"></i>
        <div><div class="alert-heading">Error Loading Data</div><div>${message}</div></div>
      </div>
    `;
  }
}

// ============================================================================
// Form Manager
// ============================================================================

class FormManager {
  constructor(formId) {
    this.form = document.getElementById(formId);
    this.fields = {};
  }

  getData() {
    const formData = new FormData(this.form);
    const data = {};
    for (let [key, value] of formData.entries()) {
      const field = this.form.elements[key];
      if (field.type === 'checkbox') {
        data[key] = field.checked;
      } else if (field.type === 'number') {
        data[key] = parseFloat(value) || 0;
      } else {
        data[key] = value;
      }
    }
    return data;
  }

  setData(data) {
    Object.keys(data).forEach(key => {
      const field = this.form.elements[key];
      if (field) {
        if (field.type === 'checkbox') {
          field.checked = data[key];
        } else {
          field.value = data[key];
        }
      }
    });
  }

  reset() { this.form.reset(); }
  validate() { return this.form.checkValidity(); }

  getErrors() {
    const errors = {};
    const inputs = this.form.querySelectorAll('[required]');
    inputs.forEach(input => {
      if (!input.value.trim()) {
        errors[input.name] = `${input.name} is required`;
      }
    });
    return errors;
  }

  showValidationErrors(errors) {
    Object.keys(errors).forEach(fieldName => {
      const field = this.form.elements[fieldName];
      if (field) {
        field.classList.add('is-invalid');
        const errorMsg = document.createElement('div');
        errorMsg.className = 'invalid-feedback d-block';
        errorMsg.textContent = errors[fieldName];
        field.parentNode.appendChild(errorMsg);
      }
    });
  }

  clearValidationErrors() {
    this.form.querySelectorAll('.is-invalid').forEach(field => {
      field.classList.remove('is-invalid');
    });
    this.form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
  }
}

// ============================================================================
// Utilities
// ============================================================================

const Utils = {
  formatDate(date) {
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleDateString('en-US', {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
  },
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  },
  generateId(prefix = 'ID') {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  },
  capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  },
  debounce(func, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  },
  throttle(func, delay) {
    let lastCall = 0;
    return function (...args) {
      const now = Date.now();
      if (now - lastCall >= delay) {
        func.apply(this, args);
        lastCall = now;
      }
    };
  },
  deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  },
  isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },
  downloadJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'export.json';
    link.click();
    URL.revokeObjectURL(url);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
});
