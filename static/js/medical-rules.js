// DrGoAi - Medical Rules Management

class MedicalRulesManager {
  constructor() {
    this.rules = [];
    this.tableManager = new TableManager('rulesTable');
  }

  async initialize() {
    this.setupEventListeners();
    await this.loadRules();
  }

  setupEventListeners() {
    const form = document.getElementById('ruleForm');
    if (form) {
      form.addEventListener('submit', (e) => this.handleCreateRule(e));
    }
  }

  async loadRules() {
    try {
      this.tableManager.showLoading();
      const data = await api.get('/medical-rules');
      this.rules = data;
      this.renderTable();
    } catch (error) {
      console.error('Error loading medical rules:', error);
      this.tableManager.showError('Failed to load medical rules');
      AlertManager.error('Failed to load medical rules');
    }
  }

  renderTable() {
    const columns = [
      { key: 'rule_id', label: 'Rule ID' },
      { key: 'name', label: 'Name' },
      { key: 'description', label: 'Description' },
      { key: 'action', label: 'Action', render: (value) => `<span class="badge bg-primary">${value}</span>` },
      { key: 'priority', label: 'Priority' },
      { 
        key: 'enabled', 
        label: 'Status',
        render: (value) => value ? '<span class="badge bg-success">Enabled</span>' : '<span class="badge bg-secondary">Disabled</span>'
      }
    ];

    const actions = [
      { label: 'Edit', icon: 'edit', type: 'warning', handler: (rule) => this.openEditModal(rule) },
      { label: 'Delete', icon: 'trash', type: 'danger', handler: (rule) => this.deleteRule(rule.rule_id) }
    ];

    this.tableManager.render(this.rules, columns, actions);
  }

  async handleCreateRule(event) {
    event.preventDefault();
    const form = new FormManager('ruleForm');

    if (!form.validate()) {
      AlertManager.error('Please fill in all required fields');
      return;
    }

    try {
      const data = form.getData();
      data.enabled = data.enabled === 'true';
      data.priority = parseInt(data.priority);
      data.conditions = data.condition ? [data.condition] : [];
      delete data.condition;

      const submitBtn = document.querySelector('#ruleForm button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
      }

      await api.post('/medical-rules', data);
      AlertManager.success('Medical rule created successfully');
      form.reset();
      
      const listTab = new bootstrap.Tab(document.getElementById('list-tab'));
      listTab.show();
      await this.loadRules();

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Rule';
      }
    } catch (error) {
      console.error('Error creating medical rule:', error);
      AlertManager.error('Failed to create medical rule');
      const submitBtn = document.querySelector('#ruleForm button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Rule';
      }
    }
  }

  openEditModal(rule) {
    document.getElementById('editRuleId').value = rule.rule_id;
    document.getElementById('editName').value = rule.name;
    document.getElementById('editDescription').value = rule.description || '';
    document.getElementById('editCondition').value = rule.conditions ? rule.conditions.join(', ') : '';
    document.getElementById('editAction').value = rule.action;
    document.getElementById('editPriority').value = rule.priority;
    document.getElementById('editEnabled').value = rule.enabled ? 'true' : 'false';

    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
  }

  async deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this medical rule?')) {
      return;
    }

    try {
      await api.delete(`/medical-rules/${ruleId}`);
      AlertManager.success('Medical rule deleted successfully');
      await this.loadRules();
    } catch (error) {
      console.error('Error deleting medical rule:', error);
      AlertManager.error('Failed to delete medical rule');
    }
  }
}

async function saveMedicalRule() {
  try {
    const ruleId = document.getElementById('editRuleId').value;
    const conditionValue = document.getElementById('editCondition').value;
    
    const data = {
      name: document.getElementById('editName').value,
      description: document.getElementById('editDescription').value,
      conditions: conditionValue ? [conditionValue] : [],
      action: document.getElementById('editAction').value,
      priority: parseInt(document.getElementById('editPriority').value),
      enabled: document.getElementById('editEnabled').value === 'true'
    };

    await api.put(`/medical-rules/${ruleId}`, data);
    AlertManager.success('Medical rule updated successfully');
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
    
    if (window.rulesManager) {
      await window.rulesManager.loadRules();
    }
  } catch (error) {
    console.error('Error updating medical rule:', error);
    AlertManager.error('Failed to update medical rule');
  }
}

let rulesManager;
document.addEventListener('DOMContentLoaded', () => {
  rulesManager = new MedicalRulesManager();
  window.rulesManager = rulesManager;
  rulesManager.initialize();
});
