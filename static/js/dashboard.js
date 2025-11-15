// ============================================================================
// DrGoAi - Dashboard Management
// ============================================================================

class Dashboard {
  constructor() {
    this.refreshInterval = null;
    this.systemStatus = null;
  }

  async initialize() {
    await this.loadSystemStatus();
    this.startAutoRefresh();
  }

  async loadSystemStatus() {
    try {
      const status = await api.get('/system-status');
      this.systemStatus = status;
      this.renderStats();
      this.updateStatusIndicator(status.status);
    } catch (error) {
      console.error('Error loading system status:', error);
      this.showError('Failed to load system status');
    }
  }

  renderStats() {
    if (!this.systemStatus || !this.systemStatus.database) {
      return;
    }

    const { database } = this.systemStatus;

    // Render Status Cards
    this.renderStatusCards(database);
    
    // Render System Status
    this.renderSystemStatus(database);
  }

  renderStatusCards(database) {
    const statusCards = document.getElementById('statusCards');
    if (!statusCards) return;

    const cards = [
      {
        title: 'Medical Rules',
        total: database.medical_rules?.total || 0,
        active: database.medical_rules?.active || 0,
        icon: 'gavel',
        color: '#3b82f6'
      },
      {
        title: 'HD Conditions',
        total: database.hd_conditions || 0,
        icon: 'stethoscope',
        color: '#10b981'
      },
      {
        title: 'Fraud Rules',
        total: database.fraud_rules || 0,
        icon: 'shield-alt',
        color: '#f59e0b'
      },
      {
        title: 'Risk Parameters',
        total: database.risk_parameters || 0,
        icon: 'chart-line',
        color: '#8b5cf6'
      }
    ];

    statusCards.innerHTML = cards.map(card => `
      <div class="col-12 col-md-6 col-lg-3 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-3">
              <div>
                <h6 class="text-muted mb-1">${card.title}</h6>
                <h2 class="mb-0">${card.total}</h2>
                ${card.active !== undefined ? `<small class="text-success">${card.active} active</small>` : ''}
              </div>
              <div style="width: 48px; height: 48px; border-radius: 12px; background: ${card.color}20; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-${card.icon}" style="color: ${card.color}; font-size: 24px;"></i>
              </div>
            </div>
          </div>
        </div>
      </div>
    `).join('');
  }

  renderSystemStatus(database) {
    const systemStatus = document.getElementById('systemStatus');
    if (!systemStatus) return;

    const ragStatus = this.systemStatus.rag_system === 'operational' 
      ? '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Operational</span>'
      : '<span class="badge bg-warning"><i class="fas fa-exclamation-circle"></i> Not Initialized</span>';

    systemStatus.innerHTML = `
      <div class="row g-3">
        <div class="col-md-6">
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">System Status</span>
            <span class="badge bg-success"><i class="fas fa-circle"></i> Operational</span>
          </div>
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">RAG System</span>
            ${ragStatus}
          </div>
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">Database</span>
            <span class="badge bg-success"><i class="fas fa-database"></i> Connected</span>
          </div>
        </div>
        <div class="col-md-6">
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">Total Records</span>
            <strong>${(database.medical_rules?.total || 0) + (database.hd_conditions || 0) + (database.fraud_rules || 0) + (database.risk_parameters || 0)}</strong>
          </div>
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">Audit Logs</span>
            <strong>${database.audit_logs || 0}</strong>
          </div>
          <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <span class="text-muted">Last Updated</span>
            <strong>${new Date().toLocaleTimeString()}</strong>
          </div>
        </div>
      </div>
    `;
  }

  updateStat(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value;
    }
  }

  updateStatusIndicator(status) {
    const indicator = document.getElementById('systemStatusIndicator');
    if (indicator) {
      if (status === 'operational') {
        indicator.innerHTML = '<i class="fas fa-circle text-success"></i> System Operational';
        indicator.className = 'text-success';
      } else {
        indicator.innerHTML = '<i class="fas fa-circle text-warning"></i> System Warning';
        indicator.className = 'text-warning';
      }
    }
  }

  updateLastUpdated() {
    const element = document.getElementById('lastUpdated');
    if (element) {
      const now = new Date();
      element.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
  }

  startAutoRefresh() {
    // Refresh every 30 seconds
    this.refreshInterval = setInterval(() => {
      this.loadSystemStatus();
    }, 30000);
  }

  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  showError(message) {
    const container = document.getElementById('dashboardContent');
    if (container) {
      container.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-circle"></i>
          <div>
            <div class="alert-heading">Error Loading Dashboard</div>
            <div>${message}</div>
          </div>
        </div>
      `;
    }
  }

  async refreshDashboard() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    }

    await this.loadSystemStatus();

    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
    }

    AlertManager.success('Dashboard refreshed successfully');
  }
}

// Initialize Dashboard
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
  dashboard = new Dashboard();
  dashboard.initialize();

  // Setup refresh button
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => dashboard.refreshDashboard());
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (dashboard) {
      dashboard.stopAutoRefresh();
    }
  });
});
