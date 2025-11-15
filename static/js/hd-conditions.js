// ============================================================================
// DrGoAi - Health Declaration Conditions Management
// ============================================================================

class HDConditionsManager {
  constructor() {
    this.conditions = [];
    this.selectedCondition = null;
    this.tableManager = new TableManager('conditionsTable');
  }

  async initialize() {
    this.setupEventListeners();
    await this.loadConditions();
  }

  setupEventListeners() {
    const form = document.getElementById('conditionForm');
    if (form) {
      form.addEventListener('submit', (e) => this.handleCreateCondition(e));
    }
  }

  async loadConditions() {
    try {
      this.tableManager.showLoading();
      const data = await api.get('/hd-conditions');
      this.conditions = data;
      this.renderTable();
    } catch (error) {
      console.error('Error loading HD conditions:', error);
      this.tableManager.showError('Failed to load HD conditions');
      AlertManager.error('Failed to load HD conditions');
    }
  }

  renderTable() {
    const columns = [
      { key: 'condition_id', label: 'Condition ID' },
      { key: 'name', label: 'Name' },
      { key: 'icd_code', label: 'ICD Code' },
      { key: 'waiting_period_months', label: 'Waiting Period (Months)' },
      { 
        key: 'coverage_percentage', 
        label: 'Coverage %',
        render: (value) => `<span class="table-badge">${value}%</span>`
      },
      {
        key: 'severity',
        label: 'Severity',
        render: (value) => {
          const colors = {
            'LOW': 'rgba(34, 197, 94, 0.1)',
            'MEDIUM': 'rgba(234, 179, 8, 0.1)',
            'HIGH': 'rgba(239, 68, 68, 0.1)',
            'CRITICAL': 'rgba(127, 29, 29, 0.1)'
          };
          const textColors = {
            'LOW': '#22c55e',
            'MEDIUM': '#eab308',
            'HIGH': '#ef4444',
            'CRITICAL': '#7f1d1d'
          };
          return `<span class="table-badge" style="background: ${colors[value] || colors.MEDIUM}; color: ${textColors[value] || textColors.MEDIUM};">${value || 'MEDIUM'}</span>`;
        }
      }
    ];

    const actions = [
      { 
        label: 'Edit', 
        icon: 'edit', 
        type: 'warning',
        handler: (condition) => this.openEditModal(condition) 
      },
      { 
        label: 'Delete', 
        icon: 'trash', 
        type: 'danger',
        handler: (condition) => this.deleteCondition(condition.condition_id) 
      }
    ];

    this.tableManager.render(this.conditions, columns, actions);
  }

  async handleCreateCondition(event) {
    event.preventDefault();
    const form = new FormManager('conditionForm');

    if (!form.validate()) {
      AlertManager.error('Please fill in all required fields');
      return;
    }

    try {
      const data = form.getData();
      data.waiting_period_months = parseInt(data.waiting_period_months);
      data.coverage_percentage = parseInt(data.coverage_percentage);

      const submitBtn = document.querySelector('#conditionForm button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

      await api.post('/hd-conditions', data);

      AlertManager.success('HD condition created successfully');
      form.reset();
      
      const listTab = new bootstrap.Tab(document.getElementById('list-tab'));
      listTab.show();

      await this.loadConditions();

      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Condition';
    } catch (error) {
      console.error('Error creating HD condition:', error);
      AlertManager.error('Failed to create HD condition');
    }
  }

  openEditModal(condition) {
    this.selectedCondition = condition;
    
    document.getElementById('editConditionId').value = condition.condition_id;
    document.getElementById('editName').value = condition.name;
    document.getElementById('editIcdCode').value = condition.icd_code || '';
    document.getElementById('editWaitingPeriod').value = condition.waiting_period_months;
    document.getElementById('editCoverage').value = condition.coverage_percentage;
    document.getElementById('editSeverity').value = condition.severity || 'MEDIUM';

    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
  }

  async deleteCondition(conditionId) {
    if (!confirm('Are you sure you want to delete this HD condition?')) {
      return;
    }

    try {
      await api.delete(`/hd-conditions/${conditionId}`);
      AlertManager.success('HD condition deleted successfully');
      await this.loadConditions();
    } catch (error) {
      console.error('Error deleting HD condition:', error);
      AlertManager.error('Failed to delete HD condition');
    }
  }
}

async function saveHDCondition() {
  try {
    const conditionId = document.getElementById('editConditionId').value;
    const data = {
      name: document.getElementById('editName').value,
      icd_code: document.getElementById('editIcdCode').value,
      waiting_period_months: parseInt(document.getElementById('editWaitingPeriod').value),
      coverage_percentage: parseInt(document.getElementById('editCoverage').value),
      severity: document.getElementById('editSeverity').value
    };

    await api.put(`/hd-conditions/${conditionId}`, data);
    
    AlertManager.success('HD condition updated successfully');
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
    
    const manager = window.hdManager;
    if (manager) {
      await manager.loadConditions();
    }
  } catch (error) {
    console.error('Error updating HD condition:', error);
    AlertManager.error('Failed to update HD condition');
  }
}

// Initialize
let hdManager;
document.addEventListener('DOMContentLoaded', () => {
  hdManager = new HDConditionsManager();
  hdManager.initialize();
});
