// llm-models manager
document.addEventListener('DOMContentLoaded', () => {
  loadContent();
});

async function loadContent() {
  try {
    const container = document.getElementById('content');
    container.innerHTML = '<div class="alert alert-info"><i class="fas fa-info-circle"></i><div>This section is being configured</div></div>';
  } catch (error) {
    console.error('Error:', error);
  }
}