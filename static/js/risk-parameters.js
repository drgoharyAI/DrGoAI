// ============================================================================
// DrGoAi - Risk Parameters Management
// ============================================================================

class RiskParametersManager {
  constructor() {
    this.parameters = [];
    this.tableManager = new TableManager('parametersTable');
  }

  async initialize() {
    this.setupEventListeners();
    await this.loadParameters();
  }

  setupEventListeners() {
    const form = document.getElementById('parameterForm');
    if (form) {
      form.addEventListener('submit', (e) => this.handleCreateParameter(e));
    }

    // Real-time weight validation
    const weightInput = document.getElementById('weight');
    if (weightInput) {
      weightInput.addEventListener('input', () => this.validateWeightSum());
    }
  }

  async loadParameters() {
    try {
      this.tableManager.showLoading();
      const data = await api.get('/risk-parameters');
      this.parameters = data;
      this.renderTable();
      this.updateWeightSummary();
    } catch (error) {
      console.error('Error loading risk parameters:', error);
      this.tableManager.showError('Failed to load risk parameters');
      AlertManager.error('Failed to load risk parameters');
    }
  }

  renderTable() {
    const columns = [
      { key: 'param_id', label: 'Parameter ID' },
      { key: 'name', label: 'Name' },
      { key: 'description', label: 'Description' },
      { 
        key: 'weight', 
        label: 'Weight',
        render: (value) => {
          const percentage = (value * 100).toFixed(1);
          return `<span class="table-badge">${percentage}%</span>`;
        }
      },
      { 
        key: 'enabled', 
        label: 'Status',
        render: (value) => value 
          ? '<span class="table-badge enabled">Active</span>' 
          : '<span class="table-badge" style="background: rgba(107, 114, 128, 0.1); color: #6b7280;">Inactive</span>'
      }
    ];

    const actions = [
      { 
        label: 'Edit', 
        icon: 'edit', 
        type: 'warning',
        handler: (param) => this.openEditModal(param) 
      },
      { 
        label: 'Delete', 
        icon: 'trash', 
        type: 'danger',
        handler: (param) => this.deleteParameter(param.param_id) 
      }
    ];

    this.tableManager.render(this.parameters, columns, actions);
  }

  updateWeightSummary() {
    const totalWeight = this.parameters
      .filter(p => p.enabled)
      .reduce((sum, p) => sum + (p.weight || 0), 0);
    
    const summaryElement = document.getElementById('weightSummary');
    if (summaryElement) {
      const percentage = (totalWeight * 100).toFixed(1);
      const isValid = Math.abs(totalWeight - 1.0) < 0.01;
      
      summaryElement.innerHTML = `
        <strong>Total Weight:</strong> 
        <span class="${isValid ? 'text-success' : 'text-danger'}">${percentage}%</span>
        ${isValid 
          ? '<i class="fas fa-check-circle text-success ms-2"></i>' 
          : '<i class="fas fa-exclamation-circle text-danger ms-2"></i> Weights should sum to 100%'
        }
      `;
    }
  }

  validateWeightSum() {
    const totalWeight = this.parameters
      .filter(p => p.enabled)
      .reduce((sum, p) => sum + (p.weight || 0), 0);
    
    return Math.abs(totalWeight - 1.0) < 0.01;
  }

  async handleCreateParameter(event) {
    event.preventDefault();
    const form = new FormManager('parameterForm');

    if (!form.validate()) {
      AlertManager.error('Please fill in all required fields');
      return;
    }

    try {
      const data = form.getData();
      data.weight = parseFloat(data.weight);
      data.enabled = data.enabled === 'true';

      const submitBtn = document.querySelector('#parameterForm button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

      await api.post('/risk-parameters', data);

      AlertManager.success('Risk parameter created successfully');
      form.reset();
      
      const listTab = new bootstrap.Tab(document.getElementById('list-tab'));
      listTab.show();

      await this.loadParameters();

      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Parameter';
    } catch (error) {
      console.error('Error creating risk parameter:', error);
      AlertManager.error('Failed to create risk parameter');
    }
  }

  openEditModal(param) {
    document.getElementById('editParamId').value = param.param_id;
    document.getElementById('editName').value = param.name;
    document.getElementById('editDescription').value = param.description || '';
    document.getElementById('editWeight').value = param.weight;
    document.getElementById('editEnabled').value = param.enabled ? 'true' : 'false';

    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
  }

  async deleteParameter(paramId) {
    if (!confirm('Are you sure you want to delete this risk parameter?')) {
      return;
    }

    try {
      await api.delete(`/risk-parameters/${paramId}`);
      AlertManager.success('Risk parameter deleted successfully');
      await this.loadParameters();
    } catch (error) {
      console.error('Error deleting risk parameter:', error);
      AlertManager.error('Failed to delete risk parameter');
    }
  }
}

async function saveRiskParameter() {
  try {
    const paramId = document.getElementById('editParamId').value;
    const data = {
      name: document.getElementById('editName').value,
      description: document.getElementById('editDescription').value,
      weight: parseFloat(document.getElementById('editWeight').value),
      enabled: document.getElementById('editEnabled').value === 'true'
    };

    await api.put(`/risk-parameters/${paramId}`, data);
    
    AlertManager.success('Risk parameter updated successfully');
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
    
    const manager = window.riskManager;
    if (manager) {
      await manager.loadParameters();
    }
  } catch (error) {
    console.error('Error updating risk parameter:', error);
    AlertManager.error('Failed to update risk parameter');
  }
}

// Initialize
let riskManager;
document.addEventListener('DOMContentLoaded', () => {
  riskManager = new RiskParametersManager();
  riskManager.initialize();
});
