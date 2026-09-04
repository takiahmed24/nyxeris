/**
 * Nyxeris Admin Cockpit & Dropshipping Operations Controller
 */

const AdminCockpit = {
  orders: [],
  products: [],

  init() {
    this.fetchStats();
    this.fetchOrders();
    this.fetchProducts();
    this.fetchTitanSkills();
  },

  switchTab(tabId, btn) {
    document.querySelectorAll('.admin-nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));

    btn.classList.add('active');
    const targetPane = document.getElementById(`tab-${tabId}`);
    if (targetPane) targetPane.classList.add('active');

    if (tabId === 'titan') {
      this.fetchTitanSkills();
      this.fetchTitanLogs();
    }
  },

  async fetchStats() {
    try {
      const res = await fetch('/api/admin/stats');
      if (!res.ok) return;
      const data = await res.json();
      document.getElementById('stat-revenue').textContent = `$${data.total_revenue.toFixed(2)}`;
      document.getElementById('stat-orders').textContent = data.paid_orders_count;
      document.getElementById('stat-unfulfilled').textContent = data.pending_fulfillment_count;
      document.getElementById('stat-mode').textContent = data.whop_status;
    } catch (e) {
      console.error(e);
    }
  },

  async fetchOrders() {
    const tbody = document.getElementById('admin-orders-table-body');
    if (!tbody) return;

    try {
      const res = await fetch('/api/admin/orders');
      if (!res.ok) throw new Error('Failed to fetch orders');
      this.orders = await res.json();
      this.renderOrdersTable();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red;">Error: ${err.message}</td></tr>`;
    }
  },

  renderOrdersTable() {
    const tbody = document.getElementById('admin-orders-table-body');
    if (!tbody) return;

    if (this.orders.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
            No customer orders recorded yet. Visit the storefront to place a test order.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.orders.map(order => {
      const itemsDesc = (order.items || []).map(i => `${i.quantity}x ${i.product_title} (${i.variant_title || 'Std'})`).join(', ');
      const destination = `${order.shipping_address_line1}, ${order.shipping_city}, ${order.shipping_state} ${order.shipping_postal_code}, ${order.shipping_country}`;

      return `
        <tr>
          <td>
            <strong style="color: #ffffff; font-family: 'JetBrains Mono', monospace;">${order.order_id}</strong>
            <div style="font-size: 11px; color: var(--text-muted);">${order.created_at || ''}</div>
          </td>
          <td>
            <div style="font-weight: 700; color: #ffffff;">${order.customer_name}</div>
            <div style="font-size: 11.5px; color: var(--text-muted); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${destination}</div>
            <div style="font-size: 11px; color: var(--accent-cyan);">${order.customer_email}</div>
          </td>
          <td style="max-width: 220px; font-size: 12px;">
            ${order.packaging_tier === 'premium' ? '<span style="display:inline-block; background: rgba(0, 229, 255, 0.15); color: #00e5ff; border: 1px solid rgba(0, 229, 255, 0.4); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-bottom: 4px; letter-spacing: 0.05em;">★ LUXURY BOX (+$2.99)</span><br/>' : ''}
            ${itemsDesc}
          </td>
          <td style="font-weight: 700; color: #ffffff;">
            $${order.total_amount.toFixed(2)}
          </td>
          <td>
            <span class="tag-status ${order.payment_status}">${order.payment_status}</span>
          </td>
          <td>
            <span class="tag-status ${order.fulfillment_status}">${order.fulfillment_status}</span>
            ${order.tracking_number ? `<div style="font-size: 10.5px; color: var(--text-muted); margin-top: 2px;">#${order.tracking_number}</div>` : ''}
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <a href="/api/orders/${order.order_id}/receipt" target="_blank" class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" title="Official Nyxeris PDF Receipt">
                PDF
              </a>
              <button type="button" class="btn-primary" style="padding: 4px 10px; font-size: 11px;" onclick="AdminCockpit.openFulfillmentModal('${order.order_id}')">
                Fulfill
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async fetchProducts() {
    const tbody = document.getElementById('admin-products-table-body');
    if (!tbody) return;

    try {
      const res = await fetch('/api/products');
      if (!res.ok) return;
      this.products = await res.json();

      tbody.innerHTML = this.products.map(p => {
        const cost = p.cost_price || 0;
        const profit = p.price - cost;
        const margin = p.price > 0 ? ((profit / p.price) * 100).toFixed(1) : 0;

        return `
          <tr>
            <td>
              <div style="display: flex; align-items: center; gap: 10px;">
                <img src="${p.image_url}" style="width: 38px; height: 38px; border-radius: 4px; object-fit: cover; background: #141418;" />
                <div>
                  <div style="font-weight: 700; color: #ffffff;">${p.title}</div>
                  <a href="${p.supplier_url || '#'}" target="_blank" style="font-size: 11px; color: var(--accent-cyan); text-decoration: none;">CJ Supplier Link ↗</a>
                </div>
              </div>
            </td>
            <td style="font-family: 'JetBrains Mono', monospace; font-size: 11.5px;">${p.sku}</td>
            <td>${p.category}</td>
            <td style="font-weight: 700; color: #ffffff;">$${p.price.toFixed(2)}</td>
            <td style="color: var(--text-muted);">$${cost.toFixed(2)}</td>
            <td>
              <span style="font-weight: 700; color: ${p.stock_quantity > 10 ? '#10b981' : '#f59e0b'};">
                ${p.stock_quantity}
              </span>
            </td>
            <td>
              <span style="color: #10b981; font-weight: 700;">+${margin}%</span>
              <span style="font-size: 11px; color: var(--text-muted);">($${profit.toFixed(2)})</span>
            </td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  },

  exportCJDropshippingCSV() {
    if (this.orders.length === 0) {
      alert("No orders available to export.");
      return;
    }

    // Filter paid orders that need fulfillment
    const eligibleOrders = this.orders.filter(o => o.payment_status === 'paid');
    if (eligibleOrders.length === 0) {
      alert("No paid orders available for CJ Dropshipping fulfillment.");
      return;
    }

    // Standard CJ Dropshipping Bulk Import Format
    let csv = "OrderNumber,ProductSKU,Quantity,RecipientName,AddressLine1,AddressLine2,City,StateProvince,PostalCode,Country,Phone,ShippingMethod,CustomNote\n";

    eligibleOrders.forEach(o => {
      (o.items || []).forEach(item => {
        const row = [
          `"${o.order_id}"`,
          `"${item.sku || item.product_id}"`,
          item.quantity,
          `"${o.customer_name.replace(/"/g, '""')}"`,
          `"${o.shipping_address_line1.replace(/"/g, '""')}"`,
          `"${(o.shipping_address_line2 || '').replace(/"/g, '""')}"`,
          `"${o.shipping_city.replace(/"/g, '""')}"`,
          `"${o.shipping_state.replace(/"/g, '""')}"`,
          `"${o.shipping_postal_code}"`,
          `"${o.shipping_country}"`,
          `"${o.customer_phone || ''}"`,
          `"CJPacket Ordinary / Fast"`,
          `"Nyxeris Blind Dropshipping - No Supplier Invoices"`
        ];
        csv += row.join(',') + "\n";
      });
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `Nyxeris_CJDropshipping_Orders_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  openFulfillmentModal(orderId) {
    const order = this.orders.find(o => o.order_id === orderId);
    if (!order) return;

    document.getElementById('fulfill_order_id').value = order.order_id;
    document.getElementById('modal-order-title').textContent = `Fulfill Order ${order.order_id}`;
    document.getElementById('fulfill_status').value = order.fulfillment_status || 'processing';
    document.getElementById('fulfill_carrier').value = order.carrier || 'USPS';
    document.getElementById('fulfill_tracking').value = order.tracking_number || '';
    document.getElementById('fulfill_tracking_url').value = order.tracking_url || '';

    const modal = document.getElementById('fulfillment-modal-overlay');
    if (modal) modal.classList.add('open');
  },

  closeFulfillmentModal() {
    const modal = document.getElementById('fulfillment-modal-overlay');
    if (modal) modal.classList.remove('open');
  },

  async submitFulfillment(e) {
    e.preventDefault();
    const orderId = document.getElementById('fulfill_order_id').value;
    const payload = {
      fulfillment_status: document.getElementById('fulfill_status').value,
      carrier: document.getElementById('fulfill_carrier').value,
      tracking_number: document.getElementById('fulfill_tracking').value,
      tracking_url: document.getElementById('fulfill_tracking_url').value
    };

    try {
      const res = await fetch(`/api/admin/orders/${orderId}/fulfillment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Failed to update fulfillment');
      this.closeFulfillmentModal();
      this.fetchOrders();
      this.fetchStats();
      alert(`Order ${orderId} updated to ${payload.fulfillment_status}!`);
    } catch (err) {
      alert(err.message);
    }
  },

  async fetchTitanSkills() {
    const grid = document.getElementById('titan-skills-grid');
    if (!grid) return;

    try {
      const res = await fetch('/api/admin/titan/skills');
      if (!res.ok) throw new Error('Failed to load Titan skills');
      const data = await res.json();
      this.renderTitanSkills(data.skills || []);
    } catch (e) {
      grid.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-muted); text-align: center; padding: 20px;">Error loading skills: ${e.message}</div>`;
    }
  },

  renderTitanSkills(skills) {
    const grid = document.getElementById('titan-skills-grid');
    if (!grid) return;

    if (skills.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-muted); text-align: center; padding: 20px;">No skills learned yet. Use the form below to teach Titan a workflow.</div>`;
      return;
    }

    grid.innerHTML = skills.map(s => {
      const triggers = (s.trigger_keywords || []).map(t => `<span style="background: rgba(0,240,255,0.1); color: #00f0ff; padding: 2px 6px; border-radius: 4px; font-size: 10.5px;">${t}</span>`).join(' ');
      const isMastered = s.status === 'MASTERED';

      return `
        <div style="background: rgba(20,20,24,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; transition: border-color var(--transition-fast);">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 6px;">
              <span style="font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 700;">${s.category || 'Automation'}</span>
              <span style="background: ${isMastered ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)'}; color: ${isMastered ? '#10b981' : '#f59e0b'}; border: 1px solid ${isMastered ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}; font-size: 10.5px; font-weight: 800; padding: 2px 7px; border-radius: 4px;">
                ${s.status || 'READY'} (${s.mastery_score || 90}%)
              </span>
            </div>
            <h4 style="font-size: 15px; font-weight: 700; color: #ffffff; margin-bottom: 6px; line-height: 1.35;">${s.name}</h4>
            <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">${s.description}</p>
            
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">Triggers:</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 12px;">
              ${triggers}
            </div>

            <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px 10px; font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">
              <div>Executed: <strong style="color: #ffffff;">${s.execution_count || 0} times</strong></div>
              ${s.last_executed ? `<div>Last Run: ${s.last_executed.slice(0,16).replace('T', ' ')}</div>` : ''}
            </div>
          </div>

          <button type="button" class="btn-primary" style="width: 100%; justify-content: center; font-size: 12px; padding: 8px 14px;" onclick="AdminCockpit.runTitanSkill('${s.id}', '${s.name.replace(/'/g, "\\'")}')">
            ⚡ Run Skill Automatically
          </button>
        </div>
      `;
    }).join('');
  },

  async runTitanSkill(skillId, skillName) {
    if (!confirm(`Are you sure you want Titan-One to run '${skillName}' automatically?`)) return;

    try {
      const res = await fetch(`/api/admin/titan/run/${skillId}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Execution failed');
      }
      const data = await res.json();
      alert(`[TITAN EXECUTION SUCCESS]\nSkill: ${data.skill_name}\nTime: ${data.elapsed_seconds}s\nResult: ${data.result}`);
      this.fetchTitanSkills();
      this.fetchTitanLogs();
    } catch (e) {
      alert(`Error running skill: ${e.message}`);
    }
  },

  async teachTitanSkill(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-teach-titan');
    const name = document.getElementById('teach_skill_name').value.trim();
    const category = document.getElementById('teach_skill_category').value;
    const triggersRaw = document.getElementById('teach_skill_triggers').value.trim();
    const desc = document.getElementById('teach_skill_desc').value.trim();
    const stepsRaw = document.getElementById('teach_skill_steps').value.trim();

    if (!name || !desc || !stepsRaw) {
      alert('Please fill out all required fields.');
      return;
    }

    const steps = stepsRaw.split('\n').map(s => s.trim()).filter(s => s.length > 0);
    const triggers = triggersRaw ? triggersRaw.split(',').map(t => t.trim()).filter(t => t.length > 0) : [];

    try {
      if (btn) {
        btn.disabled = true;
        btn.textContent = '🧠 Titan-One Internalizing Skill...';
      }

      const res = await fetch('/api/admin/titan/teach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: name,
          description: desc,
          category: category,
          steps: steps,
          trigger_keywords: triggers
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to teach skill');
      }

      const result = await res.json();
      alert(`🎉 [TITAN MASTERED SKILL]\nSkill: ${result.skill.name}\nMastery Score: ${result.skill.mastery_score}%\nStatus: ${result.skill.status}\n\nTitan internalized this workflow and added it to its autonomous library.`);

      // Reset form
      document.getElementById('teach_skill_name').value = '';
      document.getElementById('teach_skill_desc').value = '';
      document.getElementById('teach_skill_steps').value = '';
      document.getElementById('teach_skill_triggers').value = '';

      this.fetchTitanSkills();
      this.fetchTitanLogs();
    } catch (err) {
      alert(`Error teaching Titan: ${err.message}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '🎓 Internalize & Teach Titan-One';
      }
    }
  },

  async fetchTitanLogs() {
    const stream = document.getElementById('titan-logs-stream');
    if (!stream) return;

    try {
      const res = await fetch('/api/admin/titan/logs');
      if (!res.ok) return;
      const data = await res.json();
      const logs = data.logs || [];

      if (logs.length === 0) {
        stream.innerHTML = `<div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">No logs recorded yet.</div>`;
        return;
      }

      stream.innerHTML = logs.map(l => {
        const statusColor = l.status === 'APPROVED' ? '#10b981' : '#f59e0b';
        let outputSnippet = typeof l.titan_output === 'object' ? JSON.stringify(l.titan_output, null, 2) : String(l.titan_output);
        if (outputSnippet.length > 250) outputSnippet = outputSnippet.slice(0, 250) + '...';

        return `
          <div style="background: rgba(16,16,20,0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px 12px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 700; color: #ffffff; text-transform: uppercase; font-size: 11px;">${l.task_type}</span>
              <span style="color: ${statusColor}; font-weight: 700; font-size: 10.5px;">${l.status}</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 11.5px; margin-bottom: 6px;">${l.prompt_summary}</div>
            <pre style="background: rgba(0,0,0,0.4); padding: 6px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #a1a1a6; overflow-x: auto; white-space: pre-wrap;">${outputSnippet}</pre>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px; text-align: right;">${(l.timestamp || '').slice(0, 19).replace('T', ' ')}</div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  AdminCockpit.init();
});
