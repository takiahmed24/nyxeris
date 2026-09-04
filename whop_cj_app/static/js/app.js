/**
 * CJ Dropshipping for Whop - Tactical Frontend Controller
 */

async function triggerTrackingSync() {
  try {
    const res = await fetch("/api/sync/tracking", { method: "POST" });
    const data = await res.json();
    alert(`Tracking Sync Complete: Checked ${data.checked} orders, updated ${data.updated} tracking records.`);
    window.location.reload();
  } catch (err) {
    alert("Error syncing tracking: " + err.message);
  }
}

async function simulateTestOrder() {
  try {
    const res = await fetch("/api/test/simulate-order", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      alert(`Test Whop Order Placed: ${data.whop_order_id} -> CJ Order: ${data.cj_order_id || 'Submitted'}`);
      window.location.reload();
    } else {
      alert("Simulation failed: " + (data.error || "Unknown error"));
    }
  } catch (err) {
    alert("Error simulating order: " + err.message);
  }
}

async function saveMapping(e) {
  e.preventDefault();
  const payload = {
    whop_product_title: document.getElementById("whop_title").value,
    whop_variant_title: document.getElementById("whop_variant").value,
    whop_product_id: document.getElementById("whop_id").value,
    cj_variant_sku: document.getElementById("cj_sku").value,
    cj_product_title: document.getElementById("cj_title").value,
    cj_estimated_cost: parseFloat(document.getElementById("cj_cost").value) || 0.0
  };

  try {
    const res = await fetch("/api/sku-mapping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      window.location.reload();
    } else {
      const err = await res.json();
      alert("Failed to save mapping: " + (err.detail || "Server error"));
    }
  } catch (err) {
    alert("Error saving mapping: " + err.message);
  }
}

async function deleteMapping(id) {
  if (!confirm("Are you sure you want to remove this SKU mapping?")) return;
  try {
    const res = await fetch(`/api/sku-mapping/${id}`, { method: "DELETE" });
    if (res.ok) {
      window.location.reload();
    }
  } catch (err) {
    alert("Error deleting mapping: " + err.message);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    cj_email: document.getElementById("cj_email").value,
    cj_api_key: document.getElementById("cj_api_key").value,
    whop_api_key: document.getElementById("whop_api_key").value,
    whop_webhook_secret: document.getElementById("whop_secret").value,
    auto_order_enabled: document.getElementById("auto_order").checked
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const alertBox = document.getElementById("save-alert");
      if (alertBox) {
        alertBox.style.display = "flex";
        setTimeout(() => { alertBox.style.display = "none"; }, 3500);
      }
    } else {
      alert("Failed to save settings.");
    }
  } catch (err) {
    alert("Error updating settings: " + err.message);
  }
}
