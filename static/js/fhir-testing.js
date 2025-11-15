// ============================================================================
// DrGoAi - FHIR Testing & AI Processing Engine
// ============================================================================

class FHIRTestingEngine {
  constructor() {
    this.currentFHIR = null;
    this.currentValidation = null;
    this.currentResults = null;
    this.init();
  }

  init() {
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Upload zone
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fhirFile');

    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
      uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadZone.classList.remove('dragover');
      
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        this.handleFileUpload(files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });
  }

  handleFileUpload(file) {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        this.loadFHIRData(data);
      } catch (error) {
        AlertManager.error('Invalid JSON format: ' + error.message);
      }
    };

    reader.readAsText(file);
  }

  loadFHIRData(data) {
    this.currentFHIR = data;
    this.displayFHIRData(data);
    this.showProcessingControls();
  }

  displayFHIRData(data) {
    const viewer = document.getElementById('jsonViewer');
    viewer.innerHTML = this.formatJSON(data);

    // Show summary
    const summary = this.extractSummary(data);
    this.displaySummary(summary);
  }

  formatJSON(obj, depth = 0) {
    if (obj === null) return '<span class="json-null">null</span>';
    if (obj === undefined) return '<span class="json-null">undefined</span>';

    if (typeof obj === 'string') {
      return `<span class="json-string">"${obj}"</span>`;
    }

    if (typeof obj === 'number') {
      return `<span class="json-number">${obj}</span>`;
    }

    if (typeof obj === 'boolean') {
      return `<span class="json-boolean">${obj}</span>`;
    }

    if (Array.isArray(obj)) {
      if (obj.length === 0) return '[]';
      
      const items = obj.slice(0, 3).map(item => {
        if (typeof item === 'object') {
          return `<div class="tree-item">${this.formatJSON(item, depth + 1)}</div>`;
        }
        return `<div class="tree-item">${this.formatJSON(item, depth + 1)}</div>`;
      }).join('');

      const more = obj.length > 3 ? `<div class="tree-item"><span class="json-null">... ${obj.length - 3} more items</span></div>` : '';
      return `[<div style="margin-left: 1rem;">${items}${more}</div>]`;
    }

    if (typeof obj === 'object') {
      const keys = Object.keys(obj).slice(0, 10);
      const items = keys.map(key => {
        return `<div class="tree-item"><span class="json-key">"${key}"</span>: ${this.formatJSON(obj[key], depth + 1)}</div>`;
      }).join('');

      const more = Object.keys(obj).length > 10 ? `<div class="tree-item"><span class="json-null">... ${Object.keys(obj).length - 10} more fields</span></div>` : '';
      return `{<div style="margin-left: 1rem;">${items}${more}</div>}`;
    }

    return String(obj);
  }

  extractSummary(data) {
    return {
      claim_id: data.id || 'N/A',
      total: data.total?.value || 0,
      items: data.item?.length || 0,
      diagnosis: data.diagnosis?.length || 0,
      provider: data.provider?.reference || 'N/A'
    };
  }

  displaySummary(summary) {
    document.getElementById('claimSummary').style.display = 'block';
    document.getElementById('summaryClaimId').textContent = summary.claim_id;
    document.getElementById('summaryTotal').textContent = summary.total.toFixed(2) + ' SAR';
    document.getElementById('summaryItems').textContent = summary.items;
    document.getElementById('summaryDiagnosis').textContent = summary.diagnosis;
  }

  showProcessingControls() {
    document.getElementById('validateBtn').style.display = 'block';
    document.getElementById('processBtn').style.display = 'block';
  }

  async validateFHIR() {
    if (!this.currentFHIR) {
      AlertManager.error('No FHIR data loaded');
      return;
    }

    try {
      const btn = document.getElementById('validateBtn');
      btn.disabled = true;
      btn.innerHTML = '<div class="processing-spinner"></div> Validating...';

      const response = await api.post('/test/validate-fhir', {
        fhir_data: this.currentFHIR
      });

      this.currentValidation = response.validation;

      if (response.validation.valid) {
        AlertManager.success('FHIR data is valid! Ready for processing.');
      } else {
        const errors = response.validation.errors.join(', ');
        AlertManager.warning('FHIR validation issues: ' + errors);
      }

      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-check-circle"></i> Validate Only';
    } catch (error) {
      AlertManager.error('Validation failed: ' + error.message);
      document.getElementById('validateBtn').disabled = false;
      document.getElementById('validateBtn').innerHTML = '<i class="fas fa-check-circle"></i> Validate Only';
    }
  }

  async processClaim() {
    if (!this.currentFHIR) {
      AlertManager.error('No FHIR data loaded');
      return;
    }

    try {
      const btn = document.getElementById('processBtn');
      btn.disabled = true;
      btn.innerHTML = '<div class="processing-spinner"></div> Processing with AI...';

      const request = {
        fhir_data: this.currentFHIR,
        process_medical_rules: document.getElementById('processRules').checked,
        process_fraud_detection: document.getElementById('processFraud').checked,
        process_risk_assessment: document.getElementById('processRisk').checked
      };

      const response = await api.post('/test/process-claim', request);

      this.currentResults = response;
      this.displayResults(response);

      AlertManager.success('Claim processing completed successfully');

      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-brain"></i> Process with AI';
    } catch (error) {
      AlertManager.error('Processing failed: ' + error.message);
      document.getElementById('processBtn').disabled = false;
      document.getElementById('processBtn').innerHTML = '<i class="fas fa-brain"></i> Process with AI';
    }
  }

  displayResults(results) {
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';

    // Display final decision
    this.displayFinalDecision(results.final_decision);

    // Display medical rules results
    if (results.medical_rules_result) {
      this.displayMedicalRulesResults(results.medical_rules_result);
    }

    // Display fraud detection results
    if (results.fraud_detection_result) {
      this.displayFraudResults(results.fraud_detection_result);
    }

    // Display risk assessment results
    if (results.risk_assessment_result) {
      this.displayRiskResults(results.risk_assessment_result);
    }

    // Display processing time
    document.getElementById('processingTime').textContent = results.processing_time_ms;

    // Scroll to results
    setTimeout(() => {
      document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }

  displayFinalDecision(decision) {
    const icon = document.getElementById('decisionIcon');
    const decisionEl = document.getElementById('finalDecision');

    // Set color based on decision
    icon.className = 'result-icon';
    if (decision.recommendation === 'APPROVED') {
      icon.classList.add('status-approved');
      icon.innerHTML = '<i class="fas fa-check"></i>';
      decisionEl.textContent = 'APPROVED';
      decisionEl.style.color = '#16a34a';
    } else if (decision.recommendation === 'REJECTED') {
      icon.classList.add('status-rejected');
      icon.innerHTML = '<i class="fas fa-times"></i>';
      decisionEl.textContent = 'REJECTED';
      decisionEl.style.color = '#dc2626';
    } else if (decision.recommendation === 'REQUIRES_REVIEW') {
      icon.classList.add('status-review');
      icon.innerHTML = '<i class="fas fa-exclamation"></i>';
      decisionEl.textContent = 'REQUIRES REVIEW';
      decisionEl.style.color = '#ea580c';
    }

    // Display reasoning
    const reasonsEl = document.getElementById('decisionReasons');
    reasonsEl.innerHTML = decision.reasoning.map((reason, idx) => `
      <div class="timeline-item">
        <strong>${reason}</strong>
      </div>
    `).join('');
  }

  displayMedicalRulesResults(results) {
    const content = document.getElementById('rulesContent');

    let html = `
      <div class="result-section">
        <div class="result-header">
          <div class="result-icon" style="background: rgba(37, 99, 235, 0.1); color: #2563eb;">
            <i class="fas fa-gavel"></i>
          </div>
          <div>
            <div style="font-size: 16px; font-weight: 700;">Medical Rules Processing</div>
            <small class="text-muted">${results.rules_applied} rules applied</small>
          </div>
        </div>

        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">${results.coverage_analysis.covered}</div>
            <div class="metric-label">Approved</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${results.coverage_analysis.denied}</div>
            <div class="metric-label">Denied</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${results.coverage_analysis.requires_review}</div>
            <div class="metric-label">Review</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${(results.coverage_analysis.covered / (results.coverage_analysis.total_items || 1) * 100).toFixed(0)}%</div>
            <div class="metric-label">Coverage</div>
          </div>
        </div>

        <div style="margin-top: 1.5rem;">
          <h5>Item Analysis</h5>
          <table class="detail-table">
            ${results.decisions.map((decision, idx) => `
              <tr>
                <td>Item ${decision.item_index + 1}</td>
                <td>
                  <span class="table-badge approved">${decision.decision}</span>
                </td>
              </tr>
            `).join('')}
          </table>
        </div>
      </div>
    `;

    content.innerHTML = html;
  }

  displayFraudResults(results) {
    const content = document.getElementById('fraudContent');

    const riskClass = {
      'LOW': 'risk-low',
      'MEDIUM': 'risk-medium',
      'HIGH': 'risk-high'
    }[results.risk_level] || 'risk-low';

    let html = `
      <div class="result-section">
        <div class="result-header">
          <div class="result-icon" style="background: rgba(220, 38, 38, 0.1); color: #dc2626;">
            <i class="fas fa-shield-alt"></i>
          </div>
          <div>
            <div style="font-size: 16px; font-weight: 700;">Fraud Detection Analysis</div>
            <small class="text-muted">Anomaly & pattern detection</small>
          </div>
        </div>

        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">${(results.fraud_risk_score * 100).toFixed(0)}</div>
            <div class="metric-label">Risk Score</div>
          </div>
          <div class="metric-card">
            <div style="padding: 0.5rem;">
              <div class="risk-indicator ${riskClass}">
                <i class="fas fa-circle"></i> ${results.risk_level}
              </div>
            </div>
            <div class="metric-label">Risk Level</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${results.red_flags.length}</div>
            <div class="metric-label">Red Flags</div>
          </div>
        </div>

        ${results.red_flags.length > 0 ? `
          <div style="margin-top: 1.5rem;">
            <h5>Red Flags Detected</h5>
            <ul class="flag-list">
              ${results.red_flags.map(flag => `<li>${flag}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <div style="margin-top: 1.5rem;">
          <h5>Provider Analysis</h5>
          <table class="detail-table">
            <tr>
              <td>Provider</td>
              <td>${results.provider_analysis.provider_id}</td>
            </tr>
            <tr>
              <td>Pattern</td>
              <td>${results.provider_analysis.submission_pattern}</td>
            </tr>
            <tr>
              <td>Frequency Score</td>
              <td>${(results.provider_analysis.frequency_score * 100).toFixed(0)}%</td>
            </tr>
          </table>
        </div>
      </div>
    `;

    content.innerHTML = html;
  }

  displayRiskResults(results) {
    const content = document.getElementById('riskContent');

    let html = `
      <div class="result-section">
        <div class="result-header">
          <div class="result-icon" style="background: rgba(234, 88, 12, 0.1); color: #ea580c;">
            <i class="fas fa-chart-line"></i>
          </div>
          <div>
            <div style="font-size: 16px; font-weight: 700;">Risk Assessment</div>
            <small class="text-muted">Financial & member risk analysis</small>
          </div>
        </div>

        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">${(results.overall_risk_score * 100).toFixed(0)}</div>
            <div class="metric-label">Overall Risk</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${results.financial_risk.amount_at_risk.toFixed(2)}</div>
            <div class="metric-label">Amount at Risk</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${results.financial_risk.coverage_probability.toFixed(0)}%</div>
            <div class="metric-label">Coverage Prob</div>
          </div>
        </div>

        <div style="margin-top: 1.5rem;">
          <h5>Financial Risk</h5>
          <table class="detail-table">
            <tr>
              <td>Amount at Risk</td>
              <td>${results.financial_risk.amount_at_risk.toFixed(2)} SAR</td>
            </tr>
            <tr>
              <td>Coverage Probability</td>
              <td>${results.financial_risk.coverage_probability.toFixed(0)}%</td>
            </tr>
          </table>
        </div>

        <div style="margin-top: 1.5rem;">
          <h5>Member Risk Profile</h5>
          <table class="detail-table">
            <tr>
              <td>Diagnosis Severity</td>
              <td>${results.member_risk.diagnosis_severity}</td>
            </tr>
            <tr>
              <td>Healthcare Cost Prediction</td>
              <td>${results.member_risk.healthcare_cost_prediction.toFixed(2)} SAR</td>
            </tr>
          </table>
        </div>

        ${results.recommendations.length > 0 ? `
          <div style="margin-top: 1.5rem;">
            <h5>Recommendations</h5>
            <ul class="flag-list">
              ${results.recommendations.map(rec => `
                <li style="color: #2563eb;">
                  <i class="fas fa-lightbulb" style="margin-right: 0.5rem;"></i> ${rec}
                </li>
              `).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;

    content.innerHTML = html;
  }
}

// Global instance
let fhirEngine;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  fhirEngine = new FHIRTestingEngine();
});

// Function to load sample FHIR
async function loadSampleFHIR() {
  try {
    const response = await api.get('/test/sample-fhir');
    if (fhirEngine) {
      fhirEngine.loadFHIRData(response);
      AlertManager.success('Sample FHIR claim loaded successfully');
    }
  } catch (error) {
    AlertManager.error('Failed to load sample FHIR: ' + error.message);
  }
}

// Exported functions for inline onclick handlers
function validateFHIR() {
  if (fhirEngine) {
    fhirEngine.validateFHIR();
  }
}

function processClaim() {
  if (fhirEngine) {
    fhirEngine.processClaim();
  }
}
