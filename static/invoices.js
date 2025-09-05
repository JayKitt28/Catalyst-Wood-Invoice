const projectId = Number.parseInt(location.pathname.split('/').pop(), 10);


function update_display(){
    document.getElementById('title').innerHTML = `Invoice for Project ${projectId}`
    document.getElementById('back_button').href = `projects/${projectId}`
}

async function generate_invoices_display(){
    const res = await fetch(`/api/invoices/${projectId}`);
    if(!res.ok) throw new Error('Failed to load invoices');
    const i = await res.json()
    console.log(i)
    invoice_holder = document.getElementById("invoice_holder").innerHTML
    let html = '';
    
    if (i.length === 0) {
        html = '<div class="no-invoices">No invoices found for this project.</div>';
    } else {
        for(const invoice of i){
            html += `
                <div class="invoice-card">
                    <div class="invoice-header">
                        <h3>Invoice #${invoice.invoice_number || 'N/A'}</h3>
                        <div class="invoice-total">$${invoice.total_price || '0.00'}</div>
                    </div>
                    <div class="invoice-details">
                        <div class="detail-row">
                            <span class="label">Address:</span>
                            <span class="value">${invoice.adress || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Status:</span>
                            <span class="value used">Used</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Items Count:</span>
                            <span class="value">${invoice.items ? invoice.items.length : 0}</span>
                        </div>
                    </div>
                    ${invoice.items && invoice.items.length > 0 ? `
                        <div class="invoice-items">
                            <h4>Items:</h4>
                            <div class="items-list">
                                ${invoice.items.map(item => `
                                    <div class="item-row">
                                        <div class="item-description">${item.description || 'N/A'}</div>
                                        <div class="item-details">
                                            <span>Qty: ${item.ordered || '0'}</span>
                                            <span>Price: $${item.price_per || '0.00'}</span>
                                            <span>Total: $${item.extension || '0.00'}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
    }
    document.getElementById("invoice_holder").innerHTML = html;
}

generate_invoices_display()