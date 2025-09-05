
const projectId = Number.parseInt(location.pathname.split('/').pop(), 10);

function escapeAttr(str){
    return String(str).replace(/["<>&]/g, s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[s]||s)); 
}

function addBudgetRow(sku = '', material = '', quantity = '', received = '0', total_price = '') {

  const container = document.getElementById('budgetRows');
  const row = document.createElement('div');
  row.className = 'row budget-item-row';
  row.innerHTML = `
    <input class="sku-input" type="text" placeholder="SKU" value="${escapeAttr(sku)}" />
    <input class="material-input" type="text" placeholder="Material" value="${escapeAttr(material)}" />
    <input class="quantity-input" type="number" min="0" step="1" placeholder="Budget qty" value="${escapeAttr(quantity)}" />
    <input class="received-input" type="number" min="0" step="1" placeholder="Received" value="${escapeAttr(received)}" />
    <input class="remaining-output" type="number" placeholder="Remaining"  readonly />
    <input class="total-cost" type="string" placeholder="$0" value='${escapeAttr(total_price)}' min="0" step="0.01"/>
    <button type="button" class="btn ghost small" onclick="this.parentElement.remove()">Remove</button>
  `;
  container.appendChild(row);

  
  const skuInput = row.querySelector('.sku-input');
  let hasConfirmedEdit = false;
  
  skuInput.addEventListener('focus', () => {
    if (skuInput.value.trim() && !hasConfirmedEdit) {
      const confirmed = confirm('⚠️ WARNING: Editing SKU may cause issues with PDF processing and invoice tracking. Are you sure you want to continue?');
      if (!confirmed) {
        skuInput.blur();
        return false;
      } else {
        hasConfirmedEdit = true;
      }
    }
  });

  const qtyEl = row.querySelector('.quantity-input');
  const recEl = row.querySelector('.received-input');
  const remEl = row.querySelector('.remaining-output');
  const updateRemaining = () => {
    const q = Number.parseInt(qtyEl.value || '0', 10);
    const r = Number.parseInt(recEl.value || '0', 10);
    if (!Number.isNaN(q) && !Number.isNaN(r)) {
      const remaining = q - r;
      remEl.value = String(remaining);
      // Apply red styling if remaining is negative
      if (remaining < 0) {
        remEl.style.color = 'var(--danger)';
        remEl.style.fontWeight = 'bold';
      } else {
        remEl.style.color = 'var(--text)';
        remEl.style.fontWeight = 'normal';
      }
    } else {
      remEl.value = '';
      remEl.style.color = 'var(--text)';
      remEl.style.fontWeight = 'normal';
    }
  };
  qtyEl.addEventListener('input', updateRemaining);
  recEl.addEventListener('input', updateRemaining);
  updateRemaining();
}

function collectBudgetItems(){
  const rows = Array.from(document.querySelectorAll('.budget-item-row'));
  const items = [];
  for (const row of rows) {
    const sku = row.querySelector('.sku-input').value.trim();
    const material = row.querySelector('.material-input').value.trim();
    const qStr = row.querySelector('.quantity-input').value.trim();
    const rStr = row.querySelector('.received-input').value.trim();
    const tcStr = row.querySelector('.total-cost').value.trim();
    if (!sku && !material && !qStr && !rStr) continue;
    const q = Number.parseInt(qStr || '0', 10);
    const r = Number.parseInt(rStr || '0', 10);
    const tc = Number.parseFloat(tcStr || '0');
    if (!sku || !material || Number.isNaN(q) || q < 0 || Number.isNaN(r) || r < 0) {
      throw new Error('Each row needs SKU, material, non-negative quantity, and non-negative received amount');
    }
    items.push({ sku, materialName: material, quantity: q, received: r, total_payed: tc });
  }
  return items;
}

async function loadProject(){
  
  document.getElementById("invoice_page_button").querySelector("a").href = `/invoices/${projectId}`;

  const title = document.getElementById('title');
  const status = document.getElementById('status');
  const rows = document.getElementById('budgetRows');
  rows.innerHTML = '';
  status.textContent = '';
  try {
    const res = await fetch(`/api/projects/${projectId}`);
    if (!res.ok) throw new Error('Failed to load project');
    const p = await res.json();
    document.getElementById('name').value = p.name;
    title.textContent = `Project: ${p.name}`;
    document.getElementById('total-cost').value = "$" + p.total_cost
    console.log(p);
    (p.budgetItems || []).forEach(b => addBudgetRow(b.sku || '', b.materialName, String(b.quantity), String(b.received ?? 0), "$" + String(b.total_payed)));
    // Don't add default budget row - budget items are optional
    
    // Apply styling to all existing rows after loading
    setTimeout(() => {
      document.querySelectorAll('.budget-item-row').forEach(row => {
        const qtyEl = row.querySelector('.quantity-input');
        const recEl = row.querySelector('.received-input');
        const remEl = row.querySelector('.remaining-output');
        if (qtyEl && recEl && remEl) {
          const q = Number.parseInt(qtyEl.value || '0', 10);
          const r = Number.parseInt(recEl.value || '0', 10);
          if (!Number.isNaN(q) && !Number.isNaN(r)) {
            const remaining = q - r;
            if (remaining < 0) {
              remEl.style.color = 'var(--danger)';
              remEl.style.fontWeight = 'bold';
            } else {
              remEl.style.color = 'var(--text)';
              remEl.style.fontWeight = 'normal';
            }
          }
        }
        
        // Add warning popup for existing SKU inputs
        const skuInput = row.querySelector('.sku-input');
        if (skuInput) {
          let hasConfirmedEdit = false;
          skuInput.addEventListener('focus', () => {
            if (skuInput.value.trim() && !hasConfirmedEdit) {
              const confirmed = confirm('⚠️ WARNING: Editing SKU may cause issues with PDF processing and invoice tracking. Are you sure you want to continue?');
              if (!confirmed) {
                skuInput.blur();
                return false;
              } else {
                hasConfirmedEdit = true;
              }
            }
          });
        }
      });
    }, 100);
  } catch (err) {
    status.textContent = err.message;
    status.className = 'help error';
  }
}

async function saveProject(ev){
  ev.preventDefault();
  const status = document.getElementById('status');
  status.textContent='';
  const name = document.getElementById('name').value.trim();
  if (!name){ status.textContent='Name required'; status.className='help error'; return; }
  let items;
  try { items = collectBudgetItems(); }
  catch(err){ status.textContent = err.message; status.className='help error'; return; }
  try{
    const res = await fetch(`/api/projects/${projectId}`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name, budgetItems: items })
    });
    if (res.status === 409){ status.textContent = 'A project with that name already exists'; status.className='help error'; return; }
    if (!res.ok && res.status !== 204){ const t = await res.text(); throw new Error(t || 'Failed to save'); }
    status.textContent = 'Saved'; status.className='help success';
    await loadProject();
  } catch(err){
    status.textContent = err.message; status.className='help error';
  }
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('form').addEventListener('submit', saveProject);
  document.getElementById('addRowBtn').addEventListener('click', ()=> addBudgetRow());
  const applyBtn = document.getElementById('applyPdfBtn');
  if (applyBtn) {
    applyBtn.addEventListener('click', async () => {
      const fileInput = document.getElementById('pdfFile');
      const status = document.getElementById('pdfStatus');
      status.textContent = '';
      if (!fileInput.files || fileInput.files.length === 0) { status.textContent = 'Choose a PDF file first'; return; }
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      try {
        const res = await fetch(`/api/projects/${projectId}/apply-pdf`, { method: 'POST', body: fd });
        const data = await res.json();
        let msg = ""
        if (!res.ok) { throw new Error(data.error || 'Failed to apply PDF'); }
        
        status.textContent = `Updated ${data.items ? data.items.length : 0} items`;
        if (data.error != "") {status.textContent = data.error}
        await loadProject();
      } catch (err) {
        status.textContent = err.message;
      }
    });
  }
  loadProject();
});