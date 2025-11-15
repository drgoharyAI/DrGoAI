// ============================================================================
// DrGoAi - Fraud Rules Management
// ============================================================================

class FraudRulesManager {
  constructor() {
    this.rules = [];
    this.tableManager = new TableManager('fraudRulesTable');
  }

  async initialize() {
    this.setupEventListeners();
    await this.loadRules();
  }

  setupEventListeners() {
    const form = document.getElementById('fraudRuleForm');
    if (form) {
      form.addEventListener('submit', (e) => this.handleCreateRule(e));
    }
  }

  async loadRules() {
    try {
      this.tableManager.showLoading();
      const data = await api.get('/fraud-rules');
      this.rules = data;
      this.renderTable();
    } catch (error) {
      console.error('Error loading fraud rules:', error);
      this.tableManager.showError('Failed to load fraud rules');
      AlertManager.error('Failed to load fraud rules');
    }
  }

  renderTable() {
    const columns = [
      { key: 'rule_id', label: 'Rule ID' },
      { key: 'name', label: 'Name' },
      { key: 'description', label: 'Description' },
      { 
        key: 'threshold', 
        label: 'Threshold',
        render: (value) => `<span class="table-badge">${(value * 100).toFixed(0)}%</span>`
      },
      { key: 'pattern_type', label: 'Pattern Type' },
      { 
        key: 'enabled', 
        label: 'Status',
        render: (value) => value 
          ? '<span class="table-badge enabled">Enabled</span>' 
          : '<span class="table-badge" style="background: rgba(107, 114, 128, 0.1); color: #6b7280;">Disabled</span>'
      }
    ];

    const actions = [
      { 
        label: 'Edit', 
        icon: 'edit', 
        type: 'warning',
        handler: (rule) => this.openEditModal(rule) 
      },
      { 
        label: 'Toggle', 
        icon: 'power-off', 
        type: 'info',
        handler: (rule) => this.toggleRule(rule.rule_id) 
      },
      { 
        label: 'Delete', 
        icon: 'trash', 
        type: 'danger',
        handler: (rule) => this.deleteRule(rule.rule_id) 
      }
    ];

    this.tableManager.render(this.rules, columns, actions);
  }

  async handleCreateRule(event) {
    event.preventDefault();
    const form = new FormManager('fraudRuleForm');

    if (!form.validate()) {
      AlertManager.error('Please fill in all required fields');
      return;
    }

    try {
      const data = form.getData();
      data.threshold = parseFloat(data.threshold);
      data.enabled = data.enabled === 'true';

      const submitBtn = document.querySelector('#fraudRuleForm button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

      await api.post('/fraud-rules', data);

      AlertManager.success('Fraud rule created successfully');
      form.reset();
      
      const listTab = new bootstrap.Tab(document.getElementById('list-tab'));
      listTab.show();

      await this.loadRules();

      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Create Rule';
    } catch (error) {
      console.error('Error creating fraud rule:', error);
      AlertManager.error('Failed to create fraud rule');
    }
  }

  openEditModal(rule) {
    document.getElementById('editRuleId').value = rule.rule_id;
    document.getElementById('editName').value = rule.name;
    document.getElementById('editDescription').value = rule.description || '';
    document.getElementById('editThreshold').value = rule.threshold;
    document.getElementById('editPatternType').value = rule.pattern_type || '';
    document.getElementById('editEnabled').value = rule.enabled ? 'true' : 'false';

    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
  }

  async toggleRule(ruleId) {
    try {
      const result = await api.post(`/fraud-rules/${ruleId}/toggle`);
      AlertManager.success(`Rule ${result.enabled ? 'enabled' : 'disabled'} successfully`);
      await this.loadRules();
    } catch (error) {
      console.error('Error toggling fraud rule:', error);
      AlertManager.error('Failed to toggle fraud rule');
    }
  }

  async deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this fraud rule?')) {
      return;
    }

    try {
      await api.delete(`/fraud-rules/${ruleId}`);
      AlertManager.success('Fraud rule deleted successfully');
      await this.loadRules();
    } catch (error) {
      console.error('Error deleting fraud rule:', error);
      AlertManager.error('Failed to delete fraud rule');
    }
  }
}

async function saveFraudRule() {
  try {
    const ruleId = document.getElementById('editRuleId').value;
    const data = {
      name: document.getElementById('editName').value,
      description: document.getElementById('editDescription').value,
      threshold: parseFloat(document.getElementById('editThreshold').value),
      pattern_type: document.getElementById('editPatternType').value,
      enabled: document.getElementById('editEnabled').value === 'true'
    };

    await api.put(`/fraud-rules/${ruleId}`, data);
    
    AlertManager.success('Fraud rule updated successfully');
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
    
    const manager = window.fraudManager;
    if (manager) {
      await manager.loadRules();
    }
  } catch (error) {
    console.error('Error updating fraud rule:', error);
    AlertManager.error('Failed to update fraud rule');
  }
}

// Initialize
let fraudManager;
document.addEventListener('DOMContentLoaded', () => {
  fraudManager = new FraudRulesManager();
  fraudManager.initialize();
});
