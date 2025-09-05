async function fetchProjects() {
    const projectsListEl = document.getElementById('projectsList');

    projectsListEl.innerHTML = '<div class="badge">Loading...</div>';

    try {
      const res = await fetch('/api/projects');
      if (!res.ok) throw new Error('Failed to load projects');
      const projects = await res.json();
      if (!Array.isArray(projects) || projects.length === 0) {
        projectsListEl.innerHTML = '<div class="empty">No projects yet. Create one on the left.</div>';
        return;
      }
      
      projectsListEl.innerHTML = '';
      for (const p of projects) {
        const item = document.createElement('div');
        item.className = 'project-item';
        const created = new Date(p.createdAt);
        const budget = (p.budgetItems || []).map(b => `${(b.received ?? 0)}/${b.quantity} ${b.materialName}`).join(', ');
        item.innerHTML = `
          <div class="project-head">
            <div class="project-name"><a href="/projects/${p.id}" style="color:inherit;text-decoration:none;">${escapeHtml(p.name)}</a></div>
            <div style="display:flex; align-items:center; gap:8px;">
              <div class="project-date">${created.toLocaleString()}</div>
              <button class="btn ghost small" data-delete="${p.id}">Delete</button>
            </div>
          </div>
          <div class="budget">Budget: ${budget || '—'}</div>
        `;
        projectsListEl.appendChild(item);
      }
      // attach delete handlers
      projectsListEl.querySelectorAll('button[data-delete]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-delete');
          const confirmed = window.confirm('Delete this project? This cannot be undone.');
          if (!confirmed) return;
          try {
            const res = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
            if (!res.ok && res.status !== 204) {
              const t = await res.text();
              throw new Error(t || 'Failed to delete');
            }
            await fetchProjects();
          } catch (err) {
            alert('Error: ' + err.message);
          }
        });
      });
    } catch (err) {
      projectsListEl.innerHTML = `<div class="error">${err.message}</div>`;
    }
  }

  function addBudgetRow(sku = '', material = '', quantity = '', received = '0') {
    const container = document.getElementById('budgetRows');
    const row = document.createElement('div');
    row.className = 'row budget-item-row';
    row.innerHTML = `
      <input class="sku-input" type="text" placeholder="SKU (e.g., 2481D)" value="${escapeAttr(sku)}" style="flex: 1" />
      <input class="material-input" type="text" placeholder="Material (e.g., 2x4)" value="${escapeAttr(material)}" style="flex: 2" />
      <input class="quantity-input" type="number" min="0" step="1" placeholder="Budget qty" value="${escapeAttr(quantity)}" style="flex: 1" />
      <input class="received-input" type="number" min="0" step="1" placeholder="Received" value="${escapeAttr(received)}" style="flex: 1" />
      <button type="button" class="btn ghost small" onclick="this.parentElement.remove()">Remove</button>
    `;
    container.appendChild(row);
  }

  function collectBudgetItems() {
    const rows = Array.from(document.querySelectorAll('.budget-item-row'));
    const items = [];
    for (const row of rows) {
      const sku = row.querySelector('.sku-input').value.trim();
      const material = row.querySelector('.material-input').value.trim();
      const quantityStr = row.querySelector('.quantity-input').value.trim();
      const receivedStr = row.querySelector('.received-input').value.trim();
      if (!sku && !material && !quantityStr && !receivedStr) continue;
      const quantity = Number.parseInt(quantityStr || '0', 10);
      const received = Number.parseInt(receivedStr || '0', 10);
      if (!sku) {
        throw new Error('Each budget row needs a SKU');
      }
      if (!material) {
        throw new Error('Each budget row needs a material name');
      }
      if (Number.isNaN(quantity) || quantity < 0) {
        throw new Error('Each budget row needs a non-negative quantity');
      }
      if (Number.isNaN(received) || received < 0) {
        throw new Error('Each budget row needs a non-negative received amount');
      }
      // Allow received to exceed quantity (over budget)
      items.push({ sku, materialName: material, quantity, received });
    }
    return items;
  }

  async function onCreateProject(ev) {
    ev.preventDefault();
    const statusEl = document.getElementById('createStatus');
    statusEl.textContent = '';
    const nameInput = document.getElementById('projectName');
    const name = nameInput.value.trim();
    if (!name) { statusEl.textContent = 'Project name is required'; statusEl.className = 'error'; return; }
    let items;
    try { items = collectBudgetItems(); }
    catch (err) { statusEl.textContent = err.message; statusEl.className = 'error'; return; }
    // Budget items are now optional - no validation needed
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, budgetItems: items })
      });
      if (res.status === 409) { statusEl.textContent = 'A project with that name already exists'; statusEl.className = 'error'; return; }
      if (!res.ok) { const t = await res.text(); throw new Error(t || 'Failed to create project'); }
      statusEl.textContent = 'Project created'; statusEl.className = 'success';
      nameInput.value = '';
      document.getElementById('budgetRows').innerHTML = '';
      // Don't add default budget row - budget items are optional
      await fetchProjects();
    } catch (err) {
      statusEl.textContent = err.message;
      statusEl.className = 'error';
    }
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"]?/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[s]||s));
  }
  function escapeAttr(str) {
    return String(str).replace(/["<>&]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[s]||s));
  }

  async function processInvoices() {
    const button = document.getElementById('processInvoicesBtn');
    const originalText = button.textContent;
    
    // Disable button and show loading state
    button.disabled = true;
    button.textContent = 'Processing...';
    
    try {
      const response = await fetch('/api/process-invoices', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log(response)
      const data = await response.json();
      
      if (response.ok) {
        alert(`${data.message}`);
        // Refresh the projects list to show any new data
        await fetchProjects();
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      // Re-enable button
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('addRowBtn').addEventListener('click', () => addBudgetRow());
    document.getElementById('createForm').addEventListener('submit', onCreateProject);
    document.getElementById('processInvoicesBtn').addEventListener('click', processInvoices);
    // No default budget row - budget items are optional
    fetchProjects();
  });