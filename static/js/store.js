/**
 * Nyxeris Official Storefront Engine
 * Engineered to match the Insta360 / Apple industrial luxury interaction design.
 * Zero AI glows, pure tactile responsiveness.
 */

const NyxerisStore = {
  cart: [],
  products: [],
  currentUser: null,
  freeShippingThreshold: 150.00,
  taxRate: 0.08,
  defaultShippingFee: 14.99,
  selectedCountry: 'United States',
  selectedPackaging: 'standard',
  premiumPackagingFee: 2.99,

  // Interactive modes data (like Insta360 20mm vs 60mm demo)
  modesData: {
    rapid: {
      tag: "Ultra-Competitive Mode",
      title: "0.1mm Rapid Trigger Actuation",
      desc: "The switch resets the microsecond your finger lifts upward by 0.1mm. Execute consecutive keystrokes at maximum physical speed with zero mechanical rebound delay.",
      actuation: "0.1mm – 4.0mm Continuous",
      reset: "0.05mm Dynamic Return",
      force: "38g Initial / 50g Bottom-out",
      image: "https://images.unsplash.com/photo-1595225476474-87563907a212?w=800&auto=format&fit=crop&q=80"
    },
    studio: {
      tag: "Tactile Writing & Coding",
      title: "2.0mm Deep Studio Actuation",
      desc: "Calibrated for focused creative writing and software engineering. Prevents accidental keystrokes while delivering a deep, satisfying acoustic thock.",
      actuation: "2.0mm Fixed Pre-Travel",
      reset: "1.2mm Standard Release",
      force: "45g Smooth Linear",
      image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80"
    },
    hybrid: {
      tag: "Dual-Point Macro Sensing",
      title: "Dynamic Dual-Action Keystroke",
      desc: "Trigger one command on a shallow press (1.5mm) and a secondary action on full bottom-out (3.6mm). Advanced tactile automation without secondary hotkeys.",
      actuation: "Dual Stage (1.5mm / 3.6mm)",
      reset: "Dynamic Multi-Level",
      force: "Progressive Resistance",
      image: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800&auto=format&fit=crop&q=80"
    }
  },

  init() {
    this.loadCartFromStorage();
    this.fetchProducts();
    this.bindEvents();
    this.updateCartUI();
    this.initMotionEngine();
    this.initPipelineEngine();
    this.initAuth();
  },

  loadCartFromStorage() {
    try {
      const saved = localStorage.getItem('nyxeris_cart');
      if (saved) {
        this.cart = JSON.parse(saved);
      }
    } catch (e) {
      this.cart = [];
    }
  },

  saveCartToStorage() {
    localStorage.setItem('nyxeris_cart', JSON.stringify(this.cart));
    this.updateCartUI();
  },

  getDeliveryCountdown() {
    const now = new Date();
    const cutoff = new Date();
    if (now.getHours() >= 18) {
      cutoff.setDate(cutoff.getDate() + 1);
    }
    cutoff.setHours(18, 0, 0, 0);
    const diffMs = cutoff - now;
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${mins}m`;
  },

  getEstimatedDeliveryRange() {
    const now = new Date();
    const d1 = new Date(now);
    d1.setDate(d1.getDate() + 3);
    const d2 = new Date(now);
    d2.setDate(d2.getDate() + 6);
    const m1 = d1.toLocaleDateString('en-US', { month: 'short' });
    const day1 = d1.getDate();
    const m2 = d2.toLocaleDateString('en-US', { month: 'short' });
    const day2 = d2.getDate();
    return m1 === m2 ? `${m1} ${day1} – ${day2}` : `${m1} ${day1} – ${m2} ${day2}`;
  },

  selectQuickPill(category, btnEl) {
    document.querySelectorAll('.catalog-quick-pill').forEach(el => el.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    this.currentCategory = category;
    this.applyFilters();
  },

  allProducts: [],
  filteredProducts: [],
  displayCount: 24,
  currentCategory: 'All',
  searchDept: 'All',
  searchQuery: '',
  priceFilter: 'all',
  customMin: null,
  customMax: null,
  dealsOnly: false,
  ratingFilter: 0,
  inStockOnly: true,
  fastDispatchOnly: false,
  sortOrder: 'featured',
  viewMode: 'grid',

  async fetchProducts() {
    const grid = document.getElementById('products-grid');
    if (!grid) return;

    try {
      const res = await fetch('/api/products');
      if (!res.ok) throw new Error('Failed to load products');
      this.allProducts = await res.json();
      this.products = this.allProducts;
      this.populateCategorySidebar();
      this.applyFilters();
      this.renderPipelineSections();
    } catch (err) {
      console.error(err);
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
        Error loading catalog. Please refresh the page.
      </div>`;
    }
  },

  // Deterministic product review rating & count based on SKU/ID hash
  getProductRating(prod) {
    let hash = 0;
    const str = prod.sku || prod.id || prod.title;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0;
    }
    const score = (4.6 + (Math.abs(hash) % 4) * 0.1).toFixed(1);
    const count = 75 + (Math.abs(hash) % 210);
    return { score: Number(score), count };
  },

  // Calculate compare-at price & savings
  getProductPricing(prod) {
    const price = Number(prod.price);
    const comparePrice = prod.compare_at_price 
      ? Number(prod.compare_at_price) 
      : Math.round((price * 1.35) * 100) / 100;
    const savings = Math.max(0, Math.round((comparePrice - price) * 100) / 100);
    const percent = Math.round((savings / comparePrice) * 100);
    return { price, comparePrice, savings, percent };
  },

  populateCategorySidebar() {
    const container = document.getElementById('category-filter-list');
    if (!container) return;

    const categoryCounts = {};
    this.allProducts.forEach(p => {
      const cat = p.category || 'Curated Goods';
      categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
    });

    const sortedCats = Object.keys(categoryCounts).sort((a, b) => categoryCounts[b] - categoryCounts[a]);
    const categories = ['All', ...sortedCats];
    const counts = { 'All': this.allProducts.length, ...categoryCounts };

    container.innerHTML = categories.map(cat => {
      const isChecked = this.currentCategory === cat ? 'checked' : '';
      const count = counts[cat] || 0;
      const label = cat === 'All' ? 'All Departments' : cat;
      return `
        <label class="filter-radio-label">
          <input type="radio" name="dept_sidebar" value="${cat}" ${isChecked} onchange="NyxerisStore.selectCategoryFromSidebar('${cat}')" />
          <span>${label}</span>
          <span class="cat-count-badge">(${count})</span>
        </label>
      `;
    }).join('');
  },

  selectCategoryFromSidebar(category) {
    this.currentCategory = category;
    this.searchDept = category;
    this.syncCategoryControls();
    this.displayCount = 24;
    this.applyFilters();
  },

  selectCategoryFromNav(category, btn) {
    this.currentCategory = category;
    this.searchDept = category;
    this.syncCategoryControls();
    this.displayCount = 24;
    this.applyFilters();
    const catEl = document.getElementById('catalog');
    if (catEl) catEl.scrollIntoView({ behavior: 'smooth' });
  },

  handleSearchDeptChange(dept) {
    this.searchDept = dept;
    this.currentCategory = dept;
    this.syncCategoryControls();
    this.applyFilters();
  },

  syncCategoryControls() {
    // Sync header dropdown
    const deptSelect = document.getElementById('search-dept-select');
    if (deptSelect) deptSelect.value = this.currentCategory;

    // Sync sub-ribbon
    document.querySelectorAll('.dept-link').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-cat') === this.currentCategory);
    });

    // Sync sidebar radio
    const radio = document.querySelector(`input[name="dept_sidebar"][value="${this.currentCategory}"]`);
    if (radio) radio.checked = true;
  },

  handleOmniSearch(query) {
    this.searchQuery = (query || '').toLowerCase().trim();
    const clearBtn = document.getElementById('btn-clear-search');
    if (clearBtn) clearBtn.style.display = this.searchQuery ? 'block' : 'none';

    this.renderLiveSearchResults();
    this.displayCount = 24;
    this.applyFilters();
  },

  clearSearch() {
    const input = document.getElementById('global-search-input');
    if (input) input.value = '';
    const clearBtn = document.getElementById('btn-clear-search');
    if (clearBtn) clearBtn.style.display = 'none';
    this.searchQuery = '';
    this.hideLiveSearchResults();
    this.applyFilters();
  },

  showLiveSearchResults() {
    if (this.searchQuery) {
      this.renderLiveSearchResults();
    }
  },

  hideLiveSearchResults() {
    const popup = document.getElementById('live-search-results');
    if (popup) popup.style.display = 'none';
  },

  renderLiveSearchResults() {
    const popup = document.getElementById('live-search-results');
    if (!popup) return;

    if (!this.searchQuery) {
      popup.style.display = 'none';
      return;
    }

    let matches = this.allProducts.filter(p => {
      const matchText = (p.title + ' ' + p.category + ' ' + p.sku).toLowerCase();
      const inDept = this.searchDept === 'All' || p.category === this.searchDept;
      return inDept && matchText.includes(this.searchQuery);
    }).slice(0, 5);

    if (matches.length === 0) {
      popup.innerHTML = `
        <div style="padding: 14px; text-align: center; color: var(--text-muted); font-size: 12.5px;">
          No direct matches found for "${this.searchQuery}"
        </div>
      `;
      popup.style.display = 'block';
      return;
    }

    popup.innerHTML = `
      <div style="padding: 8px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); border-bottom: 1px solid #e8e8e8;">
        Top Suggestions (${matches.length})
      </div>
      ${matches.map(p => `
        <div class="live-search-item" onclick="NyxerisStore.openQuickView('${p.id}'); NyxerisStore.hideLiveSearchResults();">
          <img src="${p.image_url}" alt="${p.title}" class="live-search-thumb" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
          <div class="live-search-info">
            <div class="live-search-title">${p.title}</div>
            <div class="live-search-meta">${p.category} • ${p.sku}</div>
          </div>
          <div class="live-search-price">$${Number(p.price).toFixed(2)}</div>
        </div>
      `).join('')}
      <div style="padding: 8px; text-align: center; border-top: 1px solid #e8e8e8; font-size: 12px;">
        <a href="#catalog" onclick="NyxerisStore.hideLiveSearchResults();" style="color: #1f1919; text-decoration: underline; font-weight: 600;">
          View all results in Catalog ↓
        </a>
      </div>
    `;
    popup.style.display = 'block';
  },

  setPriceFilter(range) {
    this.priceFilter = range;
    this.customMin = null;
    this.customMax = null;
    const minInput = document.getElementById('price-min-input');
    const maxInput = document.getElementById('price-max-input');
    if (minInput) minInput.value = '';
    if (maxInput) maxInput.value = '';
    this.displayCount = 24;
    this.applyFilters();
  },

  applyCustomPrice() {
    const minInput = document.getElementById('price-min-input');
    const maxInput = document.getElementById('price-max-input');
    const minVal = minInput && minInput.value ? parseFloat(minInput.value) : 0;
    const maxVal = maxInput && maxInput.value ? parseFloat(maxInput.value) : 99999;

    this.customMin = isNaN(minVal) ? 0 : minVal;
    this.customMax = isNaN(maxVal) ? 99999 : maxVal;
    this.priceFilter = 'custom';

    // Uncheck preset radio buttons
    document.querySelectorAll('input[name="price_range"]').forEach(r => r.checked = false);
    this.displayCount = 24;
    this.applyFilters();
  },

  toggleDealsOnly(val) {
    this.dealsOnly = val;
    this.displayCount = 24;
    this.applyFilters();
  },

  filterDealsOnly(btn) {
    this.dealsOnly = true;
    const chk = document.getElementById('filter-deals-only');
    if (chk) chk.checked = true;
    document.querySelectorAll('.dept-link').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    this.displayCount = 24;
    this.applyFilters();
    const catEl = document.getElementById('catalog');
    if (catEl) catEl.scrollIntoView({ behavior: 'smooth' });
  },

  setRatingFilter(val) {
    this.ratingFilter = parseFloat(val) || 0;
    this.displayCount = 24;
    this.applyFilters();
  },

  toggleInStockOnly(val) {
    this.inStockOnly = val;
    this.displayCount = 24;
    this.applyFilters();
  },

  toggleFastDispatch(val) {
    this.fastDispatchOnly = val;
    this.displayCount = 24;
    this.applyFilters();
  },

  handleSortChange(val) {
    this.sortOrder = val;
    this.applySorting();
    this.renderProducts();
  },

  setViewMode(mode) {
    this.viewMode = mode;
    const gridBtn = document.getElementById('btn-view-grid');
    const listBtn = document.getElementById('btn-view-list');
    const container = document.getElementById('products-grid');

    if (gridBtn) gridBtn.classList.toggle('active', mode === 'grid');
    if (listBtn) listBtn.classList.toggle('active', mode === 'list');
    if (container) {
      container.className = `products-grid ${mode === 'grid' ? 'grid-mode' : 'list-mode'}`;
    }
    this.renderProducts();
  },

  resetAllFilters() {
    this.currentCategory = 'All';
    this.searchDept = 'All';
    this.searchQuery = '';
    this.priceFilter = 'all';
    this.customMin = null;
    this.customMax = null;
    this.dealsOnly = false;
    this.ratingFilter = 0;
    this.inStockOnly = true;
    this.fastDispatchOnly = false;
    this.sortOrder = 'featured';

    // Reset Form Controls
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) searchInput.value = '';
    const clearBtn = document.getElementById('btn-clear-search');
    if (clearBtn) clearBtn.style.display = 'none';

    const deptSelect = document.getElementById('search-dept-select');
    if (deptSelect) deptSelect.value = 'All';

    const priceAllRadio = document.querySelector('input[name="price_range"][value="all"]');
    if (priceAllRadio) priceAllRadio.checked = true;

    const minInput = document.getElementById('price-min-input');
    const maxInput = document.getElementById('price-max-input');
    if (minInput) minInput.value = '';
    if (maxInput) maxInput.value = '';

    const dealsChk = document.getElementById('filter-deals-only');
    if (dealsChk) dealsChk.checked = false;

    const ratingAllRadio = document.querySelector('input[name="rating_filter"][value="0"]');
    if (ratingAllRadio) ratingAllRadio.checked = true;

    const stockChk = document.getElementById('filter-in-stock');
    if (stockChk) stockChk.checked = true;

    const fastChk = document.getElementById('filter-fast-dispatch');
    if (fastChk) fastChk.checked = false;

    const sortSelect = document.getElementById('catalog-sort-select');
    if (sortSelect) sortSelect.value = 'featured';

    this.syncCategoryControls();
    this.applyFilters();
  },

  applyFilters() {
    let list = [...this.allProducts];

    // Department / Category filter
    if (this.currentCategory && this.currentCategory !== 'All') {
      list = list.filter(p => p.category === this.currentCategory);
    }

    // Search query filter
    if (this.searchQuery) {
      list = list.filter(p => {
        const text = (p.title + ' ' + p.sku + ' ' + p.category + ' ' + (p.description || '')).toLowerCase();
        return text.includes(this.searchQuery);
      });
    }

    // Price range filter
    if (this.priceFilter === '0-25') {
      list = list.filter(p => p.price < 25);
    } else if (this.priceFilter === '25-50') {
      list = list.filter(p => p.price >= 25 && p.price <= 50);
    } else if (this.priceFilter === '50-100') {
      list = list.filter(p => p.price > 50 && p.price <= 100);
    } else if (this.priceFilter === '100-9999') {
      list = list.filter(p => p.price > 100);
    } else if (this.priceFilter === 'custom') {
      const min = this.customMin !== null ? this.customMin : 0;
      const max = this.customMax !== null ? this.customMax : 99999;
      list = list.filter(p => p.price >= min && p.price <= max);
    }

    // Deals only filter (savings > $5 or percent >= 20%)
    if (this.dealsOnly) {
      list = list.filter(p => {
        const { savings, percent } = this.getProductPricing(p);
        return savings >= 5 || percent >= 20;
      });
    }

    // Rating filter
    if (this.ratingFilter > 0) {
      list = list.filter(p => {
        const { score } = this.getProductRating(p);
        return score >= this.ratingFilter;
      });
    }

    // Stock availability
    if (this.inStockOnly) {
      list = list.filter(p => (p.stock_quantity || 0) > 0);
    }

    this.filteredProducts = list;
    this.applySorting();
    this.renderActiveFilterChips();
    this.renderProducts();
  },

  applySorting() {
    if (this.sortOrder === 'price-asc') {
      this.filteredProducts.sort((a, b) => a.price - b.price);
    } else if (this.sortOrder === 'price-desc') {
      this.filteredProducts.sort((a, b) => b.price - a.price);
    } else if (this.sortOrder === 'rating') {
      this.filteredProducts.sort((a, b) => {
        const rA = this.getProductRating(a).score;
        const rB = this.getProductRating(b).score;
        return rB - rA;
      });
    } else if (this.sortOrder === 'savings') {
      this.filteredProducts.sort((a, b) => {
        const sA = this.getProductPricing(a).savings;
        const sB = this.getProductPricing(b).savings;
        return sB - sA;
      });
    } else {
      // Default: featured / best match
      this.filteredProducts.sort((a, b) => (b.id === 'prod_obsidian_board' ? 1 : 0) - (a.id === 'prod_obsidian_board' ? 1 : 0));
    }
  },

  renderActiveFilterChips() {
    const container = document.getElementById('active-filter-chips');
    const countEl = document.getElementById('results-count-text');
    if (countEl) {
      countEl.textContent = `Showing ${Math.min(this.displayCount, this.filteredProducts.length)} of ${this.filteredProducts.length} items`;
    }

    if (!container) return;
    const chips = [];

    if (this.currentCategory !== 'All') {
      chips.push({ label: this.currentCategory, action: () => this.selectCategoryFromSidebar('All') });
    }
    if (this.searchQuery) {
      chips.push({ label: `"${this.searchQuery}"`, action: () => this.clearSearch() });
    }
    if (this.priceFilter !== 'all') {
      let pLabel = this.priceFilter;
      if (this.priceFilter === '0-25') pLabel = 'Under $25';
      else if (this.priceFilter === '25-50') pLabel = '$25–$50';
      else if (this.priceFilter === '50-100') pLabel = '$50–$100';
      else if (this.priceFilter === '100-9999') pLabel = '$100+';
      else if (this.priceFilter === 'custom') pLabel = `$${this.customMin}–$${this.customMax}`;
      chips.push({ label: pLabel, action: () => this.setPriceFilter('all') });
    }
    if (this.dealsOnly) {
      chips.push({ label: 'On Sale / Deals', action: () => this.toggleDealsOnly(false) });
    }
    if (this.ratingFilter > 0) {
      chips.push({ label: `${this.ratingFilter}★ & Up`, action: () => this.setRatingFilter(0) });
    }

    container.innerHTML = chips.map((c, i) => `
      <span class="filter-chip" onclick="NyxerisStore.removeChip(${i})">
        <span>${c.label}</span>
        <span class="filter-chip-remove">✕</span>
      </span>
    `).join('');

    this._activeChips = chips;
  },

  removeChip(index) {
    if (this._activeChips && this._activeChips[index]) {
      this._activeChips[index].action();
    }
  },

  loadMore() {
    this.displayCount += 24;
    this.renderProducts();
    const countEl = document.getElementById('results-count-text');
    if (countEl) {
      countEl.textContent = `Showing ${Math.min(this.displayCount, this.filteredProducts.length)} of ${this.filteredProducts.length} items`;
    }
  },

  renderProducts() {
    const grid = document.getElementById('products-grid');
    const loadMoreBtn = document.getElementById('btn-load-more');
    if (!grid) return;

    const itemsToShow = this.filteredProducts.slice(0, this.displayCount);

    if (itemsToShow.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 18px; margin-bottom: 8px; color: #ffffff;">No products matched your criteria.</div>
          <div style="font-size: 13px; margin-bottom: 16px;">Try adjusting filters, clearing price ranges, or searching for broader terms.</div>
          <button type="button" class="btn-solid-white" onclick="NyxerisStore.resetAllFilters()">Reset All Filters</button>
        </div>
      `;
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      return;
    }

    if (this.viewMode === 'list') {
      // Best Buy Style Horizontal List Row
      grid.innerHTML = itemsToShow.map(prod => {
        const { price, comparePrice, savings, percent } = this.getProductPricing(prod);
        const { score, count } = this.getProductRating(prod);
        const whopUrl = prod.whop_url || 'https://whop.com/nyxeris/products/';

        return `
          <article class="product-card list-view" data-id="${prod.id}">
            <div class="product-thumb-wrapper">
              <img src="${prod.image_url}" alt="${prod.title}" loading="lazy" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
              <button type="button" class="product-quickview-btn" onclick="NyxerisStore.openQuickView('${prod.id}')">
                Quick View
              </button>
            </div>
            <div class="product-details">
              <div class="product-meta-row">
                <span class="product-category">${prod.category}</span>
                <span class="product-sku">${prod.sku}</span>
              </div>
              <h3 class="product-title" onclick="NyxerisStore.openQuickView('${prod.id}')" title="${prod.title}">${prod.title}</h3>
              <div class="rating-snippet">
                <span class="rating-stars">★★★★★</span>
                <span class="rating-val">${score}</span>
                <span class="rating-count">(${count} reviews)</span>
              </div>
              <p class="product-description">${prod.description}</p>
              <div class="stock-indicator" style="position: static; display: inline-flex; width: fit-content; margin-top: 6px;">
                <span class="stock-dot"></span>
                <span>In Stock • Ready for Courier Dispatch</span>
              </div>
            </div>
            <div class="list-actions-col">
              <div>
                <div class="price-box">
                  <span class="current-price">$${price.toFixed(2)}</span>
                  <span class="compare-price">$${comparePrice.toFixed(2)}</span>
                </div>
                ${savings > 0 ? `
                  <span class="savings-badge" style="margin-top: 4px; display: inline-block;">
                    Save $${savings.toFixed(2)} (${percent}% off)
                  </span>
                ` : ''}
              </div>
              <button type="button" class="btn-buy-direct" style="justify-content: center;" onclick="NyxerisStore.quickBuy('${prod.id}')">
                <span>BUY NOW</span>
              </button>
              <button type="button" class="btn-add-cart" onclick="NyxerisStore.addToCart('${prod.id}')">
                ADD TO BAG
              </button>
              <button type="button" style="background: transparent; border: 1px solid #e8e8e8; color: #767676; font-size: 11px; font-weight: 500; padding: 6px; border-radius: 2px; cursor: pointer;" onclick="NyxerisStore.openQuickView('${prod.id}')">
                View Specifications
              </button>
            </div>
          </article>
        `;
      }).join('');
    } else {
      // Editorial v2.0 Grid Mode Cards (Matching Catalog Mockup)
      grid.innerHTML = itemsToShow.map(prod => {
        const { price, comparePrice, savings, percent } = this.getProductPricing(prod);
        const { score, count } = this.getProductRating(prod);

        return `
          <article class="product-card" data-id="${prod.id}">
            <div class="product-thumb-wrapper" style="position: relative;">
              ${percent > 0 ? `<span class="badge-discount-terracotta" style="position: absolute; top: 10px; left: 10px; z-index: 2;">${percent}% OFF</span>` : ''}
              <button type="button" class="wishlist-btn" style="position: absolute; top: 10px; right: 10px; z-index: 2; background: rgba(255,255,255,0.9); border: none; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer;" title="Save to Wishlist" onclick="event.stopPropagation(); NyxerisStore.showToast('Saved to wishlist');">
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#1f1919" stroke-width="1.8"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              </button>
              <img src="${prod.image_url}" alt="${prod.title}" loading="lazy" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
              <button type="button" class="product-quickview-btn" onclick="NyxerisStore.openQuickView('${prod.id}')">
                Quick View
              </button>
            </div>
            <div class="product-details">
              <div style="display: flex; gap: 6px; margin: 4px 0 6px 0;">
                <span class="badge-in-stock"><span class="badge-in-stock-dot"></span> In Stock</span>
                <span class="badge-fast-dispatch">Fast Dispatch</span>
              </div>
              <h3 class="product-title" onclick="NyxerisStore.openQuickView('${prod.id}')" title="${prod.title}">${prod.title}</h3>
              <div class="rating-snippet">
                <span class="rating-stars" style="color: #f59e0b;">★★★★★</span>
                <span class="rating-val">${score}</span>
                <span class="rating-count">(${count})</span>
              </div>
              <p class="product-description">${prod.description}</p>

              <div class="product-bottom-row">
                <div class="price-row-top" style="display: flex; align-items: center; justify-content: space-between;">
                  <div class="price-box">
                    <span class="current-price">$${price.toFixed(2)}</span>
                    <span class="compare-price">$${comparePrice.toFixed(2)}</span>
                  </div>
                  <span style="color: #2e6b36; font-size: 11.5px; font-weight: 600;">Free Shipping</span>
                </div>
                <button type="button" class="btn-catalog-add-bag" onclick="NyxerisStore.addToCart('${prod.id}')">
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
                  <span>Add to Bag</span>
                </button>
              </div>
            </div>
          </article>
        `;
      }).join('');
    }

    if (loadMoreBtn) {
      if (this.displayCount < this.filteredProducts.length) {
        loadMoreBtn.style.display = 'inline-block';
        loadMoreBtn.textContent = `Load More Products (${this.filteredProducts.length - this.displayCount} remaining)`;
      } else {
        loadMoreBtn.style.display = 'none';
      }
    }
  },

  openQuickView(productId) {
    const product = this.allProducts.find(p => p.id === productId);
    if (!product) return;

    const overlay = document.getElementById('quickview-modal-overlay');
    const container = document.getElementById('quickview-content');
    if (!overlay || !container) return;

    const { price, comparePrice, savings, percent } = this.getProductPricing(product);
    const { score, count } = this.getProductRating(product);
    const whopUrl = product.whop_url || 'https://whop.com/nyxeris/products/';

    container.innerHTML = `
      <div class="quickview-image-wrap">
        <img src="${product.image_url}" alt="${product.title}" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
      </div>
      <div class="quickview-info-wrap">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #767676; font-weight: 600; font-family: var(--font-nav);">
            ${product.category || 'Curated Goods'}
          </div>
          <span class="badge-in-stock"><span class="badge-in-stock-dot"></span> In Stock</span>
        </div>
        <h2 style="font-family: var(--font-serif); font-size: 22px; font-weight: 400; color: #1f1919; line-height: 1.35; margin-bottom: 8px;">
          ${product.title}
        </h2>
        <div class="rating-snippet" style="margin-bottom: 12px;">
          <span class="rating-stars" style="font-size: 14px; color: #f59e0b;">★★★★★</span>
          <span class="rating-val" style="font-size: 13px; font-weight: 600; color: #1f1919;">${score}</span>
          <span class="rating-count" style="font-size: 12.5px; color: #767676;" id="quickview-stars-count">(${count} verified reviews)</span>
        </div>

        <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px;">
          <span style="font-family: var(--font-nav); font-size: 24px; font-weight: 600; color: #1f1919;">$${price.toFixed(2)}</span>
          <span style="font-size: 15px; color: #767676; text-decoration: line-through;">$${comparePrice.toFixed(2)}</span>
          ${savings > 0 ? `<span class="badge-discount-terracotta">${percent}% OFF</span>` : ''}
        </div>
        ${savings > 0 ? `<div style="font-size: 12.5px; color: var(--accent-terracotta); font-weight: 600; margin-bottom: 12px;">You save $${savings.toFixed(2)}</div>` : ''}

        <p style="font-size: 13.5px; color: #424242; line-height: 1.6; margin-bottom: 16px;">
          ${product.description}
        </p>

        <!-- Delivery Urgency Box (PDP Mockup Specification) -->
        <div class="pdp-delivery-urgency-box">
          <div class="pdp-urgency-icon">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
          </div>
          <div class="pdp-urgency-text">
            <div>Order within <strong>${this.getDeliveryCountdown()}</strong> to get it by</div>
            <div class="pdp-urgency-date">${this.getEstimatedDeliveryRange()}</div>
          </div>
        </div>

        <div class="quickview-specs-box">
          <div class="quickview-specs-row">
            <span>Product SKU</span>
            <span style="font-family: var(--font-nav); font-size: 12px; color: #1f1919;">${product.sku}</span>
          </div>
          <div class="quickview-specs-row">
            <span>Logistics Dispatch</span>
            <span style="color: #1f1919; font-weight: 600;">Within 24 Hours (Tracked & Insured)</span>
          </div>
          <div class="quickview-specs-row">
            <span>Packaging</span>
            <span>Premium Retail Presentation Box</span>
          </div>
          <div class="quickview-specs-row">
            <span>Guarantee</span>
            <span>30-Day Transit & Quality Guarantee</span>
          </div>
        </div>

        <!-- Dual Action CTAs -->
        <div class="pdp-dual-actions-row">
          <button type="button" class="btn-pdp-add-bag" onclick="NyxerisStore.addToCart('${product.id}'); NyxerisStore.closeQuickView();">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
            <span>Add to Bag</span>
          </button>
          <button type="button" class="btn-pdp-buy-now" onclick="NyxerisStore.quickBuy('${product.id}');">
            Buy Now
          </button>
        </div>

        <!-- Payment Badges Strip -->
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 14px; font-size: 10px; color: #767676; flex-wrap: wrap;">
          <span class="payment-badge-chip">VISA</span>
          <span class="payment-badge-chip">MASTERCARD</span>
          <span class="payment-badge-chip">AMEX</span>
          <span class="payment-badge-chip">APPLE PAY</span>
          <span class="payment-badge-chip">GOOGLE PAY</span>
          <span class="payment-badge-chip">PAYPAL</span>
        </div>
      </div>

      <!-- Reviews Section -->
      <div class="quickview-reviews-section">
        <div class="reviews-section-header">
          <div class="reviews-title-group">
            <h3 class="reviews-main-title">Client Reviews & Ratings</h3>
            <span class="reviews-avg-badge" id="quickview-reviews-badge">★ ${score} (${count} reviews)</span>
          </div>
          <button type="button" class="btn-write-review" onclick="NyxerisStore.toggleReviewForm('${product.id}')">
            + Write a Review
          </button>
        </div>

        <!-- Write Review Form -->
        <div class="review-form-container" id="review-form-${product.id}">
          <div style="font-weight: 600; font-size: 14px; margin-bottom: 12px; color: #1f1919;">Share Your Hardware Experience</div>
          <div class="star-rating-selector" id="star-selector-${product.id}" data-rating="5">
            <span class="star active" onclick="NyxerisStore.setReviewRating('${product.id}', 1)">★</span>
            <span class="star active" onclick="NyxerisStore.setReviewRating('${product.id}', 2)">★</span>
            <span class="star active" onclick="NyxerisStore.setReviewRating('${product.id}', 3)">★</span>
            <span class="star active" onclick="NyxerisStore.setReviewRating('${product.id}', 4)">★</span>
            <span class="star active" onclick="NyxerisStore.setReviewRating('${product.id}', 5)">★</span>
            <span style="font-size: 12px; color: #767676; margin-left: 8px;" id="star-rating-label-${product.id}">5 of 5 Stars</span>
          </div>
          <div class="review-form-grid">
            <input type="text" id="review-name-${product.id}" class="review-input" placeholder="Your Name or Moniker" required />
            <input type="email" id="review-email-${product.id}" class="review-input" placeholder="Your Email (Verified Buyer check)" />
          </div>
          <input type="text" id="review-title-${product.id}" class="review-input" placeholder="Headline (e.g. Unrivaled CNC craftsmanship)" style="margin-bottom: 12px;" />
          <textarea id="review-comment-${product.id}" class="review-textarea" placeholder="Describe the build quality, tactile feel, and setup integration..."></textarea>
          <div id="review-alert-${product.id}" style="display: none; font-size: 12px; margin-bottom: 10px;"></div>
          <div class="review-form-actions">
            <button type="button" class="btn-outline-subtle" style="padding: 8px 14px; font-size: 12px;" onclick="NyxerisStore.toggleReviewForm('${product.id}')">Cancel</button>
            <button type="button" class="btn-solid-white" style="padding: 8px 16px; font-size: 12px;" onclick="NyxerisStore.submitProductReview('${product.id}')">Submit Review</button>
          </div>
        </div>

        <!-- Reviews List -->
        <div class="reviews-cards-list" id="quickview-reviews-list">
          <div style="font-size: 13px; color: #767676; text-align: center; padding: 20px 0;">Loading verified customer reviews...</div>
        </div>
      </div>
    `;

    overlay.classList.add('open');
    this.loadQuickViewReviews(product.id);
  },

  closeQuickView() {
    const overlay = document.getElementById('quickview-modal-overlay');
    if (overlay) overlay.classList.remove('open');
  },

  toggleReviewForm(productId) {
    const form = document.getElementById(`review-form-${productId}`);
    if (form) {
      form.style.display = (form.style.display === 'block') ? 'none' : 'block';
    }
  },

  setReviewRating(productId, rating) {
    const selector = document.getElementById(`star-selector-${productId}`);
    const label = document.getElementById(`star-rating-label-${productId}`);
    if (!selector) return;
    selector.dataset.rating = rating;
    const stars = selector.querySelectorAll('.star');
    stars.forEach((star, idx) => {
      if (idx < rating) {
        star.classList.add('active');
      } else {
        star.classList.remove('active');
      }
    });
    if (label) {
      label.textContent = `${rating} of 5 Stars`;
    }
  },

  async loadQuickViewReviews(productId) {
    const listContainer = document.getElementById('quickview-reviews-list');
    const badge = document.getElementById('quickview-reviews-badge');
    const starsCount = document.getElementById('quickview-stars-count');
    if (!listContainer) return;

    try {
      const res = await fetch(`/api/products/${productId}/reviews`);
      if (!res.ok) throw new Error('Failed to load reviews');
      const data = await res.json();

      if (badge) {
        badge.textContent = `★ ${data.average_rating} (${data.total_reviews} reviews)`;
      }
      if (starsCount) {
        starsCount.textContent = `(${data.total_reviews} verified reviews)`;
      }

      if (!data.reviews || data.reviews.length === 0) {
        listContainer.innerHTML = `<div style="font-size: 13px; color: #767676; padding: 12px 0;">No reviews yet. Be the first to review this piece!</div>`;
        return;
      }

      listContainer.innerHTML = data.reviews.map(r => {
        const starsStr = '★'.repeat(r.rating) + '☆'.repeat(Math.max(0, 5 - r.rating));
        const dateStr = r.created_at ? (r.created_at.includes('T') ? r.created_at.split('T')[0] : r.created_at) : 'Recently';
        return `
          <div class="review-card-item">
            <div class="review-card-header">
              <div class="review-card-user">
                <span class="review-card-name">${r.customer_name}</span>
                ${r.is_verified_buyer ? `<span class="review-verified-tag"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg> Verified Client</span>` : ''}
              </div>
              <span class="review-card-date">${dateStr}</span>
            </div>
            <div class="review-card-stars" style="margin-bottom: 4px;">${starsStr}</div>
            ${r.title ? `<div class="review-card-title">${r.title}</div>` : ''}
            <div class="review-card-comment">${r.comment}</div>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading reviews:', err);
      listContainer.innerHTML = `<div style="font-size: 13px; color: #767676; padding: 12px 0;">Verified review system active.</div>`;
    }
  },

  async submitProductReview(productId) {
    const selector = document.getElementById(`star-selector-${productId}`);
    const nameInput = document.getElementById(`review-name-${productId}`);
    const emailInput = document.getElementById(`review-email-${productId}`);
    const titleInput = document.getElementById(`review-title-${productId}`);
    const commentInput = document.getElementById(`review-comment-${productId}`);
    const alertBox = document.getElementById(`review-alert-${productId}`);

    if (!nameInput || !commentInput) return;
    const rating = parseInt(selector?.dataset?.rating || '5', 10);
    const name = nameInput.value.trim();
    const email = emailInput?.value?.trim() || '';
    const title = titleInput?.value?.trim() || '';
    const comment = commentInput.value.trim();

    if (!name) {
      alert('Please provide your name or moniker.');
      nameInput.focus();
      return;
    }
    if (!comment || comment.length < 3) {
      alert('Please write a brief review comment (at least 3 characters).');
      commentInput.focus();
      return;
    }

    try {
      const res = await fetch(`/api/products/${productId}/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: name,
          customer_email: email || undefined,
          rating: rating,
          title: title,
          comment: comment
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Could not submit review');
      }

      if (alertBox) {
        alertBox.style.display = 'block';
        alertBox.style.color = '#059669';
        alertBox.textContent = '✓ Review published successfully!';
      }

      commentInput.value = '';
      if (titleInput) titleInput.value = '';

      await this.loadQuickViewReviews(productId);

      setTimeout(() => {
        this.toggleReviewForm(productId);
        if (alertBox) alertBox.style.display = 'none';
      }, 1400);

    } catch (err) {
      if (alertBox) {
        alertBox.style.display = 'block';
        alertBox.style.color = '#dc2626';
        alertBox.textContent = err.message;
      } else {
        alert(err.message);
      }
    }
  },

  openPolicyModal(policyKey = 'refunds') {
    const modal = document.getElementById('pipeline-policy-modal');
    if (modal) {
      modal.style.display = 'flex';
      this.switchPolicyTab(policyKey);
    }
  },

  closePolicyModal() {
    const modal = document.getElementById('pipeline-policy-modal');
    if (modal) modal.style.display = 'none';
  },

  switchPolicyTab(policyKey) {
    const tabs = ['refunds', 'shipping', 'privacy', 'terms'];
    tabs.forEach(t => {
      const btn = document.getElementById(`policy-tab-${t}`);
      if (btn) {
        if (t === policyKey) btn.classList.add('active');
        else btn.classList.remove('active');
      }
    });

    const titleEl = document.getElementById('policy-modal-title');
    const contentEl = document.getElementById('policy-modal-content');
    if (!contentEl) return;

    const policies = {
      refunds: {
        title: '30-Day Transit & Quality Guarantee',
        html: `
          <h2>1. 30-Day Unconditional Quality Guarantee</h2>
          <p>Every piece engineered and dispatched by Nyxeris is backed by our strict 30-day satisfaction commitment. If you are not entirely satisfied with the craftsmanship, material density, or ergonomic performance of your gear, you may initiate a return or exchange within 30 calendar days of confirmed carrier delivery.</p>
          <div style="background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 16px; margin: 16px 0;">
            <p style="margin: 0; color: #e0f2fe;"><strong>Instant Courier Protection:</strong> In the unlikely event that your parcel sustains transit damage or gets stalled, our Concierge team immediately dispatches a replacement without requiring you to wait for long carrier investigations.</p>
          </div>
          <h2>2. Direct Concierge Resolution</h2>
          <p>Contact <strong>concierge@nyxeris.com</strong> with your Nyxeris Order ID (e.g. <code>NYX-1A2B3C4D5E6F</code>) or lookup your order in the Client Privileges account modal for instant 12-hour resolution.</p>
        `
      },
      shipping: {
        title: 'Shipping & Insured Logistics Policy',
        html: `
          <h2>1. Global Express Logistics</h2>
          <p>Nyxeris dispatches via tier-one express logistics networks (USPS Priority, DHL Express, FedEx Air, and Royal Mail) with full transit insurance.</p>
          <ul>
            <li><strong>Continental US:</strong> $14.99 Priority Courier (Free on orders $120+). 4 to 8 business days.</li>
            <li><strong>UK & Europe:</strong> $16.99 Tracked Air Courier (VAT prepaid). 6 to 10 business days.</li>
            <li><strong>Worldwide:</strong> $19.99 Worldwide Insured Express. 7 to 12 business days.</li>
          </ul>
          <h2>2. Premium Bespoke Unboxing ($2.99)</h2>
          <p>Customers may opt for the Nyxeris Signature Packaging Box at checkout, featuring dual-density foam shock dampening and a serialized metallic authenticity certificate card.</p>
        `
      },
      privacy: {
        title: 'Privacy & Data Protection Policy',
        html: `
          <h2>1. Privacy-First Architecture</h2>
          <p>Nyxeris does not sell, rent, or monetize your personal information or purchase history with third-party advertising brokers under any circumstances.</p>
          <h2>2. Level 1 PCI-DSS Payment Tokenization</h2>
          <p>All transactions are tokenized via Whop Payments and Stripe with AES-256 bank-level encryption. Nyxeris never stores raw credit card numbers on our servers.</p>
          <h2>3. GDPR & CCPA Compliance</h2>
          <p>You maintain full ownership of your data and can request complete account profile export or permanent erasure by emailing <strong>privacy@nyxeris.com</strong>.</p>
        `
      },
      terms: {
        title: 'Terms of Service & Purchase Agreement',
        html: `
          <h2>1. Commercial Purchase Agreement</h2>
          <p>By placing an order on Nyxeris, you enter into a verified purchase agreement backed by our official serialized tax receipts and automated carrier dispatch notifications.</p>
          <h2>2. Precision Machining & Material Tolerances</h2>
          <p>All specifications are laboratory-calibrated. Microscopic variations in CNC anodization tone, natural vegan leather texture, or Hall Effect switch magnetic thresholds reflect the artisanal nature of our hardware.</p>
          <h2>3. Governing Jurisdiction</h2>
          <p>Commercial transactions are governed by standard international electronic commerce consumer protection conventions.</p>
        `
      }
    };

    const pol = policies[policyKey] || policies.refunds;
    if (titleEl) titleEl.textContent = pol.title;
    contentEl.innerHTML = pol.html;
  },

  selectVariant(productId, variantName, btnElement) {
    const container = document.getElementById(`variants-${productId}`);
    if (!container) return;
    container.querySelectorAll('.variant-chip').forEach(el => el.classList.remove('selected'));
    btnElement.classList.add('selected');
  },

  getSelectedVariant(productId) {
    const container = document.getElementById(`variants-${productId}`);
    if (!container) return null;
    const selectedBtn = container.querySelector('.variant-chip.selected');
    return selectedBtn ? selectedBtn.textContent.trim() : null;
  },

  quickBuy(productId) {
    const product = this.allProducts.find(p => p.id === productId) || this.products.find(p => p.id === productId);
    if (!product) return;

    const variant = this.getSelectedVariant(productId);
    const existingIndex = this.cart.findIndex(item => item.product_id === productId && item.variant_title === variant);

    if (existingIndex > -1) {
      this.cart[existingIndex].quantity += 1;
    } else {
      this.cart.push({
        product_id: product.id,
        title: product.title,
        price: product.price,
        image_url: product.image_url,
        sku: product.sku,
        variant_title: variant || '',
        quantity: 1
      });
    }

    this.saveCartToStorage();
    this.closeQuickView();
    this.openCheckoutModal();
  },

  addToCart(productId) {
    const product = (this.allProducts && this.allProducts.find(p => p.id === productId)) || (this.products && this.products.find(p => p.id === productId));
    if (!product) return;

    const variant = this.getSelectedVariant(productId);
    const existingIndex = this.cart.findIndex(item => item.product_id === productId && item.variant_title === variant);

    if (existingIndex > -1) {
      this.cart[existingIndex].quantity += 1;
    } else {
      this.cart.push({
        product_id: product.id,
        title: product.title,
        price: product.price,
        image_url: product.image_url,
        sku: product.sku,
        variant_title: variant || '',
        quantity: 1
      });
    }

    this.saveCartToStorage();
    this.openCart();
    this.showToast(`Added ${product.title} to bag`);
  },

  addBundleToCart(bundleType) {
    if (bundleType === 'creator') {
      // Add Apex keyboard + Lumina Pad
      const kb = this.products.find(p => p.id === 'prod_obsidian_board');
      const pad = this.products.find(p => p.id === 'prod_lumina_pad');
      if (kb) {
        this.cart.push({
          product_id: kb.id,
          title: "Creator Bundle: Apex-65 HE Keyboard + Lumina Mat",
          price: 219.00,
          image_url: kb.image_url,
          sku: "NYX-BDL-CRTR01",
          variant_title: "Creator Studio Edition",
          quantity: 1
        });
      }
    } else if (bundleType === 'master') {
      const kb = this.products.find(p => p.id === 'prod_obsidian_board');
      if (kb) {
        this.cart.push({
          product_id: kb.id,
          title: "Master Workspace: Keyboard + ScreenBar + Mat + MagSafe",
          price: 349.00,
          image_url: kb.image_url,
          sku: "NYX-BDL-MSTR01",
          variant_title: "Full Studio Architecture",
          quantity: 1
        });
      }
    }

    this.saveCartToStorage();
    this.openCart();
    this.showToast(`Selected curated bundle added to bag`);
  },

  switchInteractiveMode(modeKey, btn) {
    document.querySelectorAll('.mode-pill').forEach(el => el.classList.remove('active'));
    btn.classList.add('active');

    const data = this.modesData[modeKey];
    if (!data) return;

    document.getElementById('mode-tag').textContent = data.tag;
    document.getElementById('mode-title').textContent = data.title;
    document.getElementById('mode-description').textContent = data.desc;
    document.getElementById('mode-spec-actuation').textContent = data.actuation;
    document.getElementById('mode-spec-reset').textContent = data.reset;
    document.getElementById('mode-spec-force').textContent = data.force;
    document.getElementById('mode-image').src = data.image;
  },

  updateQuantity(index, delta) {
    if (!this.cart[index]) return;
    this.cart[index].quantity += delta;
    if (this.cart[index].quantity <= 0) {
      this.cart.splice(index, 1);
    }
    this.saveCartToStorage();
  },

  removeFromCart(index) {
    this.cart.splice(index, 1);
    this.saveCartToStorage();
  },

  getShippingFee(country, subtotal) {
    if (subtotal >= this.freeShippingThreshold || subtotal === 0) return 0.00;
    const c = (country || this.selectedCountry || 'United States').toLowerCase();
    if (c.includes('united states') || c.includes('usa') || c.includes('canada')) return 14.99;
    if (c.includes('united kingdom') || c.includes('uk') || c.includes('germany') || c.includes('france') || c.includes('europe') || c.includes('spain') || c.includes('italy')) return 16.99;
    return 19.99;
  },

  setPackaging(tier) {
    this.selectedPackaging = tier === 'premium' ? 'premium' : 'standard';

    // Update cart drawer cards
    const cartStdCard = document.getElementById('cart-pkg-standard-card');
    const cartPremCard = document.getElementById('cart-pkg-premium-card');
    if (cartStdCard && cartPremCard) {
      if (this.selectedPackaging === 'premium') {
        cartStdCard.classList.remove('active');
        cartPremCard.classList.add('active');
      } else {
        cartPremCard.classList.remove('active');
        cartStdCard.classList.add('active');
      }
    }

    // Update checkout modal cards
    const modalStdCard = document.getElementById('modal-pkg-standard-card');
    const modalPremCard = document.getElementById('modal-pkg-premium-card');
    if (modalStdCard && modalPremCard) {
      if (this.selectedPackaging === 'premium') {
        modalStdCard.classList.remove('active');
        modalPremCard.classList.add('active');
      } else {
        modalPremCard.classList.remove('active');
        modalStdCard.classList.add('active');
      }
    }

    this.updateCheckoutBreakdown();
    this.updateCartUI();
  },

  calculateTotals(country = null) {
    const subtotal = this.cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
    const shipping = this.getShippingFee(country || this.selectedCountry, subtotal);
    const packagingFee = (this.selectedPackaging === 'premium' && this.cart.length > 0) ? this.premiumPackagingFee : 0.0;
    const tax = Math.round(subtotal * this.taxRate * 100) / 100;
    const grandTotal = Math.round((subtotal + shipping + packagingFee + tax) * 100) / 100;
    return { subtotal, shipping, packagingFee, tax, grandTotal };
  },

  updateCartUI() {
    const countBadge = document.getElementById('header-cart-count');
    const drawerContainer = document.getElementById('cart-items-list');
    const subtotalEl = document.getElementById('cart-subtotal-val');
    const shippingEl = document.getElementById('cart-shipping-val');
    const taxEl = document.getElementById('cart-tax-val');
    const grandTotalEl = document.getElementById('cart-total-val');
    const progressFill = document.getElementById('shipping-progress-bar');
    const progressText = document.getElementById('shipping-progress-desc');

    const totalQty = this.cart.reduce((acc, it) => acc + it.quantity, 0);
    if (countBadge) countBadge.textContent = `(${totalQty})`;

    const { subtotal, shipping, tax, grandTotal } = this.calculateTotals();
    const headerCartTotal = document.getElementById('header-cart-total');
    if (headerCartTotal) headerCartTotal.textContent = `$${subtotal.toFixed(2)}`;

    if (progressFill && progressText) {
      const leftBadge = document.getElementById('shipping-progress-left-badge');
      if (subtotal >= this.freeShippingThreshold) {
        progressFill.style.width = '100%';
        progressText.innerHTML = `<span>✓ Unlocked Free Insured Courier Delivery!</span>`;
        if (leftBadge) leftBadge.textContent = 'FREE SHIPPING';
      } else {
        const remaining = (this.freeShippingThreshold - subtotal).toFixed(2);
        const percent = Math.min(100, Math.round((subtotal / this.freeShippingThreshold) * 100));
        progressFill.style.width = `${percent}%`;
        progressText.innerHTML = `<span>🚚 You're <strong>$${remaining}</strong> away from Free Shipping!</span>`;
        if (leftBadge) leftBadge.textContent = `$${remaining} left`;
      }
    }

    if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    if (shippingEl) shippingEl.textContent = shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`;
    if (taxEl) taxEl.textContent = `$${tax.toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.textContent = `$${grandTotal.toFixed(2)}`;

    if (drawerContainer) {
      if (this.cart.length === 0) {
        drawerContainer.innerHTML = `
          <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
            <p>Your shopping bag is empty.</p>
          </div>
        `;
        const checkoutBtn = document.getElementById('btn-open-checkout');
        if (checkoutBtn) checkoutBtn.disabled = true;
      } else {
        const checkoutBtn = document.getElementById('btn-open-checkout');
        if (checkoutBtn) checkoutBtn.disabled = false;

        drawerContainer.innerHTML = this.cart.map((item, idx) => `
          <div class="cart-item-row">
            <img src="${item.image_url}" alt="${item.title}" class="cart-item-thumb" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
            <div class="cart-item-info">
              <h4 class="cart-item-title">${item.title}</h4>
              ${item.variant_title ? `<span class="cart-item-variant">${item.variant_title}</span>` : ''}
              <div class="cart-item-price">$${(item.price * item.quantity).toFixed(2)}</div>
              <div class="cart-item-controls">
                <div class="qty-stepper">
                  <button type="button" class="qty-btn" onclick="NyxerisStore.updateQuantity(${idx}, -1)">−</button>
                  <span class="qty-val">${item.quantity}</span>
                  <button type="button" class="qty-btn" onclick="NyxerisStore.updateQuantity(${idx}, 1)">+</button>
                </div>
                <button type="button" class="btn-remove-item" onclick="NyxerisStore.removeFromCart(${idx})">Remove</button>
              </div>
            </div>
          </div>
        `).join('');
      }
    }
  },

  openCart() {
    const overlay = document.getElementById('cart-drawer-overlay');
    if (overlay) overlay.classList.add('open');
  },

  closeCart() {
    const overlay = document.getElementById('cart-drawer-overlay');
    if (overlay) overlay.classList.remove('open');
  },

  openMobileNav() {
    const drawer = document.getElementById('pipeline-mobile-drawer');
    const overlay = document.getElementById('pipeline-mobile-overlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  },

  closeMobileNav() {
    const drawer = document.getElementById('pipeline-mobile-drawer');
    const overlay = document.getElementById('pipeline-mobile-overlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  },

  toggleMobileFilters() {
    const sidebar = document.getElementById('catalog-sidebar-filters');
    const btn = document.getElementById('mobile-filter-toggle-btn');
    if (sidebar) {
      sidebar.classList.toggle('mobile-open');
      if (btn) btn.classList.toggle('active');
    }
  },

  openCheckoutModal() {
    if (this.cart.length === 0) return;
    this.closeCart();
    const overlay = document.getElementById('checkout-modal-overlay');
    if (overlay) overlay.classList.add('open');
    this.updateCheckoutBreakdown();

    // Pre-fill customer address and contact if logged in
    if (this.currentUser) {
      const form = document.getElementById('checkout-shipping-form');
      if (form) {
        if (this.currentUser.full_name && form.elements['full_name']) form.elements['full_name'].value = this.currentUser.full_name;
        if (this.currentUser.email && form.elements['email']) form.elements['email'].value = this.currentUser.email;
        if (this.currentUser.phone && form.elements['phone']) form.elements['phone'].value = this.currentUser.phone;
        if (this.currentUser.address_line1 && form.elements['address_line1']) form.elements['address_line1'].value = this.currentUser.address_line1;
        if (this.currentUser.address_line2 && form.elements['address_line2']) form.elements['address_line2'].value = this.currentUser.address_line2;
        if (this.currentUser.city && form.elements['city']) form.elements['city'].value = this.currentUser.city;
        if (this.currentUser.state && form.elements['state']) form.elements['state'].value = this.currentUser.state;
        if (this.currentUser.postal_code && form.elements['postal_code']) form.elements['postal_code'].value = this.currentUser.postal_code;
        if (this.currentUser.country && form.elements['country']) {
          form.elements['country'].value = this.currentUser.country;
          this.handleCountryChange(this.currentUser.country);
        }
      }
    }
  },

  handleCountryChange(country) {
    this.selectedCountry = country;
    this.updateCheckoutBreakdown();
    this.updateCartUI();
  },

  updateCheckoutBreakdown() {
    const countrySelect = document.getElementById('checkout-country-select');
    const country = countrySelect ? countrySelect.value : this.selectedCountry;
    const { subtotal, shipping, packagingFee, tax, grandTotal } = this.calculateTotals(country);

    const subtotalEl = document.getElementById('modal-subtotal-val');
    const shippingEl = document.getElementById('modal-shipping-val');
    const packagingEl = document.getElementById('modal-packaging-val');
    const taxEl = document.getElementById('modal-tax-val');
    const sumTotalEl = document.getElementById('modal-grand-total');

    if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    if (shippingEl) shippingEl.textContent = shipping === 0 ? 'FREE (Orders Over $150)' : `$${shipping.toFixed(2)}`;
    if (packagingEl) packagingEl.textContent = this.selectedPackaging === 'premium' ? '+$2.99 (Nyxeris Signature)' : 'Standard (Free)';
    if (taxEl) taxEl.textContent = `$${tax.toFixed(2)}`;
    if (sumTotalEl) sumTotalEl.textContent = `$${grandTotal.toFixed(2)}`;
  },

  closeCheckoutModal() {
    const overlay = document.getElementById('checkout-modal-overlay');
    if (overlay) overlay.classList.remove('open');
  },

  async submitCheckout(event) {
    event.preventDefault();
    const form = document.getElementById('checkout-shipping-form');
    const submitBtn = document.getElementById('btn-submit-order');
    if (!form || !submitBtn) return;

    const formData = new FormData(form);
    const shipping = {
      full_name: formData.get('full_name'),
      email: formData.get('email'),
      phone: formData.get('phone') || '',
      address_line1: formData.get('address_line1'),
      address_line2: formData.get('address_line2') || '',
      city: formData.get('city'),
      state: formData.get('state'),
      postal_code: formData.get('postal_code'),
      country: formData.get('country') || 'United States',
      shipping_method: formData.get('shipping_method') || 'Nyxeris Priority Insured Courier'
    };

    const payload = {
      items: this.cart.map(i => ({
        product_id: i.product_id,
        variant_title: i.variant_title,
        quantity: i.quantity
      })),
      shipping: shipping,
      packaging_tier: this.selectedPackaging
    };

    try {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Securing Session...';

      const res = await fetch('/api/orders/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Checkout failed');
      }

      const orderResult = await res.json();
      localStorage.removeItem('nyxeris_cart');
      let checkoutUrl = orderResult.checkout_url;
      if (checkoutUrl.startsWith('http://localhost') || checkoutUrl.startsWith('https://localhost')) {
        checkoutUrl = checkoutUrl.replace(/^https?:\/\/[^\/]+/, '');
      }
      window.location.href = checkoutUrl;
    } catch (err) {
      alert(`Error: ${err.message}`);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Continue to Payment';
    }
  },

  // -------------------------------------------------------------------------
  // Customer Authentication & Client Portal Management
  // -------------------------------------------------------------------------
  async initAuth() {
    try {
      const res = await fetch('/api/auth/me');
      if (res.ok) {
        const data = await res.json();
        if (data.authenticated && data.customer) {
          this.currentUser = data.customer;
        } else {
          this.currentUser = null;
        }
      }
    } catch (e) {
      console.warn('Auth check error:', e);
      this.currentUser = null;
    }
    this.updateAuthUI();
  },

  updateAuthUI() {
    const accountLabel = document.getElementById('pipeline-account-label');
    const cartAuthStrip = document.getElementById('cart-auth-strip');

    if (this.currentUser) {
      const firstName = (this.currentUser.full_name || 'Client').split(' ')[0];
      if (accountLabel) {
        accountLabel.textContent = `Hi, ${firstName}`;
      }
      if (cartAuthStrip) {
        cartAuthStrip.className = 'cart-auth-strip logged-in';
        cartAuthStrip.style.display = 'flex';
        cartAuthStrip.innerHTML = `
          <span>✓ Signed in as <strong>${firstName}</strong></span>
          <a href="javascript:void(0)" onclick="NyxerisStore.openAccountModal()">View Orders</a>
        `;
      }
    } else {
      if (accountLabel) {
        accountLabel.textContent = 'My Account';
      }
      if (cartAuthStrip) {
        cartAuthStrip.className = 'cart-auth-strip guest';
        cartAuthStrip.style.display = 'flex';
        cartAuthStrip.innerHTML = `
          <span>Returning client?</span>
          <a href="javascript:void(0)" onclick="NyxerisStore.openAccountModal('signin')">Sign in for 1-click checkout</a>
        `;
      }
    }
  },

  openAccountModal(initialTab = 'signin') {
    const modal = document.getElementById('pipeline-account-modal');
    if (!modal) return;
    modal.style.display = 'flex';

    if (this.currentUser) {
      const guestView = document.getElementById('account-guest-view');
      const memberView = document.getElementById('account-member-view');
      if (guestView) guestView.style.display = 'none';
      if (memberView) memberView.style.display = 'block';
      this.renderMemberProfile();
      this.loadMemberOrders();
      this.switchMemberTab('orders');
    } else {
      const guestView = document.getElementById('account-guest-view');
      const memberView = document.getElementById('account-member-view');
      if (guestView) guestView.style.display = 'block';
      if (memberView) memberView.style.display = 'none';
      this.switchAccountTab(initialTab);
    }
  },

  closeAccountModal() {
    const modal = document.getElementById('pipeline-account-modal');
    if (modal) modal.style.display = 'none';
    const alertBox = document.getElementById('account-auth-alert');
    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.textContent = '';
    }
  },

  switchAccountTab(tabName) {
    const tabs = ['signin', 'register', 'lookup'];
    tabs.forEach(t => {
      const btn = document.getElementById(`tab-btn-${t}`);
      const pane = document.getElementById(`account-pane-${t}`);
      if (btn) btn.classList.toggle('active', t === tabName);
      if (pane) pane.style.display = t === tabName ? 'flex' : 'none';
    });
    const alertBox = document.getElementById('account-auth-alert');
    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.textContent = '';
    }
  },

  switchMemberTab(tabName) {
    const tabs = ['orders', 'address'];
    tabs.forEach(t => {
      const btn = document.getElementById(`member-tab-${t}`);
      const pane = document.getElementById(`member-pane-${t}`);
      if (btn) btn.classList.toggle('active', t === tabName);
      if (pane) pane.style.display = t === tabName ? 'block' : 'none';
    });
  },

  showAuthAlert(msg, type = 'error') {
    const alertBox = document.getElementById('account-auth-alert');
    if (alertBox) {
      alertBox.className = `account-alert ${type}`;
      alertBox.textContent = msg;
      alertBox.style.display = 'block';
    }
  },

  async handleSignIn(e) {
    e.preventDefault();
    const email = document.getElementById('signin-email').value.trim();
    const password = document.getElementById('signin-password').value;
    const btn = document.getElementById('signin-submit-btn');

    try {
      btn.disabled = true;
      btn.textContent = 'Signing in...';
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Sign in failed');

      this.currentUser = data.customer;
      this.updateAuthUI();
      this.showToast(`Welcome back, ${data.customer.full_name}!`);
      this.openAccountModal(); // Switches to member view
    } catch (err) {
      this.showAuthAlert(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sign In to Nyxeris';
    }
  },

  async handleRegister(e) {
    e.preventDefault();
    const full_name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const phone = document.getElementById('register-phone').value.trim();
    const btn = document.getElementById('register-submit-btn');

    try {
      btn.disabled = true;
      btn.textContent = 'Creating account...';
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name, email, password, phone })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Registration failed');

      this.currentUser = data.customer;
      this.updateAuthUI();
      this.showToast(`Account created! Welcome to Nyxeris, ${data.customer.full_name}`);
      this.openAccountModal();
    } catch (err) {
      this.showAuthAlert(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Create Nyxeris Account';
    }
  },

  async handleLogout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    this.currentUser = null;
    this.updateAuthUI();
    this.closeAccountModal();
    this.showToast('Signed out successfully.');
  },

  renderMemberProfile() {
    if (!this.currentUser) return;
    const initials = (this.currentUser.full_name || 'NY').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'NY';
    const avatarInitials = document.getElementById('member-avatar-initials');
    const displayName = document.getElementById('member-display-name');
    const displayEmail = document.getElementById('member-display-email');
    if (avatarInitials) avatarInitials.textContent = initials;
    if (displayName) displayName.textContent = this.currentUser.full_name;
    if (displayEmail) displayEmail.textContent = this.currentUser.email;

    // Pre-fill profile form fields
    const profName = document.getElementById('prof-name');
    const profPhone = document.getElementById('prof-phone');
    const profAdd1 = document.getElementById('prof-address1');
    const profAdd2 = document.getElementById('prof-address2');
    const profCity = document.getElementById('prof-city');
    const profState = document.getElementById('prof-state');
    const profZip = document.getElementById('prof-zip');
    const profCountry = document.getElementById('prof-country');

    if (profName) profName.value = this.currentUser.full_name || '';
    if (profPhone) profPhone.value = this.currentUser.phone || '';
    if (profAdd1) profAdd1.value = this.currentUser.address_line1 || '';
    if (profAdd2) profAdd2.value = this.currentUser.address_line2 || '';
    if (profCity) profCity.value = this.currentUser.city || '';
    if (profState) profState.value = this.currentUser.state || '';
    if (profZip) profZip.value = this.currentUser.postal_code || '';
    if (profCountry) profCountry.value = this.currentUser.country || 'United States';
  },

  async loadMemberOrders() {
    const listContainer = document.getElementById('member-orders-list');
    const countSpan = document.getElementById('member-orders-count');
    if (!listContainer) return;

    listContainer.innerHTML = '<div style="text-align: center; padding: 24px; color: #888;">Loading your order history...</div>';

    try {
      const res = await fetch('/api/auth/orders');
      if (!res.ok) throw new Error('Could not load orders');
      const data = await res.json();
      const orders = data.orders || [];

      if (countSpan) countSpan.textContent = orders.length;

      if (orders.length === 0) {
        listContainer.innerHTML = `
          <div style="text-align: center; padding: 36px 16px; color: #767676;">
            <p style="margin-bottom: 8px; font-weight: 500;">No orders found under this account.</p>
            <p style="font-size: 12px; color: #999;">Any physical orders you place will be recorded here with real-time tracking.</p>
          </div>
        `;
        return;
      }

      listContainer.innerHTML = orders.map(ord => {
        const itemsSummary = (ord.items || []).map(it => `${it.quantity}x ${it.product_title}`).join(', ') || 'Physical Products';
        const isPaid = ord.payment_status === 'paid';
        const isShipped = ord.fulfillment_status === 'shipped';
        const trackingBadge = ord.tracking_number
          ? `<a href="${ord.tracking_url || 'https://cjpacket.com'}" target="_blank" class="btn-order-action track">CJ Tracking: ${ord.tracking_number} ↗</a>`
          : `<span class="status-badge ${isShipped ? 'shipped' : 'unfulfilled'}">${isShipped ? 'In Transit' : 'Processing'}</span>`;

        return `
          <div class="member-order-card">
            <div class="order-card-header">
              <div>
                <span class="order-card-id">${ord.order_id}</span>
                <span class="order-card-date"> • ${new Date(ord.created_at).toLocaleDateString()}</span>
              </div>
              <div class="order-status-badges">
                <span class="status-badge ${isPaid ? 'paid' : 'pending'}">${ord.payment_status}</span>
              </div>
            </div>
            <div class="order-items-preview">${itemsSummary}</div>
            <div class="order-card-footer">
              <span class="order-card-total">$${parseFloat(ord.total_amount).toFixed(2)}</span>
              <div class="order-card-actions">
                ${ord.tracking_number ? trackingBadge : ''}
                <a href="/order-confirmation/${ord.order_id}" class="btn-order-action receipt">Order & Receipt ↗</a>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      listContainer.innerHTML = `<div style="color: #cf1322; padding: 16px;">Failed to load orders: ${err.message}</div>`;
    }
  },

  async handleSaveProfile(e) {
    e.preventDefault();
    const btn = document.getElementById('save-address-btn');
    const updates = {
      full_name: document.getElementById('prof-name').value.trim(),
      phone: document.getElementById('prof-phone').value.trim(),
      address_line1: document.getElementById('prof-address1').value.trim(),
      address_line2: document.getElementById('prof-address2').value.trim(),
      city: document.getElementById('prof-city').value.trim(),
      state: document.getElementById('prof-state').value.trim(),
      postal_code: document.getElementById('prof-zip').value.trim(),
      country: document.getElementById('prof-country').value.trim()
    };

    try {
      btn.disabled = true;
      btn.textContent = 'Saving...';
      const res = await fetch('/api/auth/update-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Save failed');

      this.currentUser = data.customer;
      this.updateAuthUI();
      this.showToast('Shipping address saved to your client profile!');
    } catch (err) {
      alert(`Error saving address: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Save Shipping Address';
    }
  },

  async handleOrderLookup(e) {
    e.preventDefault();
    const orderId = document.getElementById('lookup-order-id').value.trim();
    const email = document.getElementById('lookup-order-email').value.trim();
    const resultBox = document.getElementById('lookup-result-container');
    const btn = document.getElementById('lookup-submit-btn');

    try {
      btn.disabled = true;
      btn.textContent = 'Searching...';
      const q = new URLSearchParams({ order_id: orderId });
      if (email) q.append('email', email);

      const res = await fetch(`/api/auth/lookup-order?${q.toString()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Order not found');

      const ord = data.order;
      const itemsList = (ord.items || []).map(i => `${i.quantity}x ${i.product_title}`).join(', ');

      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <strong>Order ${ord.order_id}</strong>
          <span class="status-badge ${ord.payment_status === 'paid' ? 'paid' : 'pending'}">${ord.payment_status}</span>
        </div>
        <div style="font-size: 12px; color: #555; margin-bottom: 8px;">Items: ${itemsList}</div>
        <div style="font-size: 12px; color: #555; margin-bottom: 12px;">Total: <strong>$${parseFloat(ord.total_amount).toFixed(2)}</strong> (${ord.currency})</div>
        <div style="display: flex; gap: 8px;">
          ${ord.tracking_number ? `<a href="${ord.tracking_url || 'https://cjpacket.com'}" target="_blank" class="btn-order-action track">Track Courier: ${ord.tracking_number} ↗</a>` : ''}
          <a href="/order-confirmation/${ord.order_id}" class="btn-order-action receipt">View Full Receipt ↗</a>
        </div>
      `;
    } catch (err) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `<div style="color: #cf1322; font-size: 12.5px;">${err.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Track Order';
    }
  },

  promptTrackOrder() {
    this.openAccountModal('lookup');
  },

  showToast(message) {
    let toast = document.getElementById('nyxeris-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'nyxeris-toast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #1c1c20;
        border: 1px solid rgba(255,255,255,0.2);
        color: #ffffff;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        z-index: 2000;
        opacity: 0;
        transform: translateY(10px);
        transition: all 200ms ease;
      `;
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, 2500);
  },

  /* ==========================================================================
     SHOPIFY MOTION REACTIVE INTERACTION ENGINE
     ========================================================================== */
  motionState: {
    heroVideoPlaying: true,
    ambientSoundActive: false,
    acousticAudioPlaying: false,
    acousticAudioObj: null,
    isPoronDamped: true,
    visAnimationFrame: null
  },

  flowData: {
    rapid: {
      title: "Dual-Axis Laser Spec Profiling",
      desc: "Continuous scanning verifies ±0.02mm tolerances on every CNC chamfer. Electromagnetic flux calibration guarantees instantaneous rapid reset.",
      video: "/static/videos/hardware_macro_flow.webm",
      badge: "Precision Stream",
      specs: ["0.125ms MCU Polling", "IP65 Water Resistance", "Full N-Key Rollover"]
    },
    unibody: {
      title: "6063 Solid Billet CNC Machining",
      desc: "Sculpted from a single aircraft-grade aluminum block. Hand-sandblasted with 150-grit micro-beads and matte charcoal anodized.",
      video: "/static/videos/ambient_mesh_flow.webm",
      badge: "Thermal Stress Sim",
      specs: ["1,150g Table Stability", "Zero Chassis Flex", "Anodized 25µm Oxide"]
    },
    power: {
      title: "15W Qi2 MagSafe Alignment Array",
      desc: "Industrial neodymium N52 ring automatically snaps mobile devices into peak inductive flux alignment with zero thermal throttling.",
      video: "/static/videos/hardware_macro_flow.webm",
      badge: "Inductive Flux Scan",
      specs: ["Qi2 Certified 15W", "Dual GaN Regulators", "Sub-40°C Cooling"]
    }
  },

  initMotionEngine() {
    this.initActuationVisualizer();
    this.initAcousticCanvas();
    this.initCard3DTilt();
    this.initMagneticButtons();
  },

  toggleHeroVideo() {
    const video = document.getElementById('hero-ambient-video');
    const icon = document.getElementById('video-ctrl-icon');
    const label = document.getElementById('video-ctrl-text');
    if (!video) return;

    if (video.paused) {
      video.play();
      this.motionState.heroVideoPlaying = true;
      if (icon) icon.textContent = '⏸';
      if (label) label.textContent = 'Motion';
    } else {
      video.pause();
      this.motionState.heroVideoPlaying = false;
      if (icon) icon.textContent = '▶';
      if (label) label.textContent = 'Paused';
    }
  },

  toggleAmbientSound() {
    const video = document.getElementById('hero-ambient-video');
    const icon = document.getElementById('sound-ctrl-icon');
    const label = document.getElementById('sound-ctrl-text');
    if (!video) return;

    video.muted = !video.muted;
    this.motionState.ambientSoundActive = !video.muted;
    if (icon) icon.textContent = video.muted ? '🔇' : '🔊';
    if (label) label.textContent = video.muted ? 'Muted' : 'Sound ON';
    this.showToast(video.muted ? 'Ambient sound muted' : 'Ambient sound active');
  },

  selectHotspot(key) {
    const hint = document.getElementById('active-hotspot-hint');
    const tooltips = {
      switch: "Inspecting: Dual-Rail Hall Effect Sensor (0.1mm micro-millimeter fidelity, zero physical contacts).",
      chassis: "Inspecting: 6063 Solid Billet Aluminum Unibody (1,150g weight eliminates keyboard drift).",
      gasket: "Inspecting: Quad-Layer Poron Gasket Damping (Acoustic absorption of high-frequency resonance)."
    };
    if (hint && tooltips[key]) {
      hint.textContent = tooltips[key];
    }
  },

  switchVideoFlow(flowKey, btn) {
    const data = this.flowData[flowKey];
    if (!data) return;

    // Set active tab
    document.querySelectorAll('.flow-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // Update video
    const video = document.getElementById('flow-detail-video');
    const badge = document.getElementById('flow-video-badge');
    const title = document.getElementById('flow-title');
    const desc = document.getElementById('flow-desc');
    const specContainer = document.querySelector('.flow-spec-pills');

    if (video) {
      video.style.opacity = '0.3';
      setTimeout(() => {
        video.src = data.video;
        video.play();
        video.style.opacity = '1';
      }, 150);
    }
    if (badge) badge.textContent = data.badge;
    if (title) title.textContent = data.title;
    if (desc) desc.textContent = data.desc;
    if (specContainer) {
      specContainer.innerHTML = data.specs.map(s => `<span class="spec-tag">${s}</span>`).join('');
    }
  },

  initActuationVisualizer() {
    this.handleActuationSlider(0.10);
  },

  handleActuationSlider(val) {
    const num = parseFloat(val);
    const display = document.getElementById('actuation-display-val');
    const latency = document.getElementById('gauge-latency');
    const flux = document.getElementById('gauge-flux');
    const reset = document.getElementById('gauge-reset');
    const stem = document.getElementById('switch-stem-graphic');
    const sensorGlow = document.getElementById('sensor-glow');

    if (display) display.textContent = num.toFixed(2) + ' mm';
    
    // Physics calculations
    const msLatency = (0.125 + (num - 0.10) * 0.22).toFixed(3);
    const gauss = Math.max(420, Math.round(1840 - (num - 0.10) * 350));
    const resetDist = num <= 1.0 ? '0.05 mm' : (0.05 + (num - 1.0) * 0.08).toFixed(2) + ' mm';

    if (latency) latency.textContent = msLatency + ' ms';
    if (flux) flux.textContent = gauss.toLocaleString() + ' Gauss';
    if (reset) reset.textContent = resetDist;

    // Stem motion: 0.1mm -> 0px, 4.0mm -> 32px
    if (stem) {
      const translateY = (num - 0.10) * 8.2;
      stem.style.transform = `translateY(${translateY}px)`;
    }
    if (sensorGlow) {
      const glowAlpha = Math.min(1.0, 0.35 + (4.0 - num) * 0.16);
      sensorGlow.style.background = `radial-gradient(ellipse at bottom, rgba(0, 240, 255, ${glowAlpha}) 0%, transparent 80%)`;
    }
  },

  setActuationPreset(val, btn) {
    const slider = document.getElementById('actuation-slider');
    if (slider) slider.value = val;
    this.handleActuationSlider(val);

    document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
  },

  initAcousticCanvas() {
    const canvas = document.getElementById('acoustic-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    this.drawEqualizerBars(ctx, canvas, false);
  },

  drawEqualizerBars(ctx, canvas, isPlaying) {
    const barCount = 48;
    const barWidth = canvas.width / barCount - 3;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < barCount; i++) {
      let height;
      if (isPlaying) {
        // Dynamic wave oscillation
        const t = Date.now() / 150;
        const wave1 = Math.sin(t + i * 0.4);
        const wave2 = Math.cos(t * 0.8 + i * 0.2);
        const factor = (wave1 + wave2 + 2) / 4;
        height = 10 + factor * (canvas.height - 20) * (this.motionState.isPoronDamped ? 0.75 : 1.0);
      } else {
        // Idle gentle waveform
        height = 8 + Math.sin(i * 0.3) * 6;
      }

      const x = i * (barWidth + 3);
      const y = canvas.height - height;

      const grad = ctx.createLinearGradient(0, y, 0, canvas.height);
      if (this.motionState.isPoronDamped) {
        grad.addColorStop(0, '#1f1919');
        grad.addColorStop(1, '#666666');
      } else {
        grad.addColorStop(0, '#424242');
        grad.addColorStop(1, '#999999');
      }

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, height, [3, 3, 0, 0]);
      ctx.fill();
    }

    if (isPlaying) {
      this.motionState.visAnimationFrame = requestAnimationFrame(() => {
        this.drawEqualizerBars(ctx, canvas, true);
      });
    }
  },

  toggleAcousticAudio() {
    const canvas = document.getElementById('acoustic-canvas');
    const icon = document.getElementById('acoustic-play-icon');
    const label = document.getElementById('acoustic-play-text');
    const statusLabel = document.getElementById('vis-label');

    if (!this.motionState.acousticAudioObj) {
      this.motionState.acousticAudioObj = new Audio('/static/audio/typing_sound_profile.wav');
      this.motionState.acousticAudioObj.addEventListener('ended', () => {
        this.motionState.acousticAudioPlaying = false;
        if (icon) icon.textContent = '▶';
        if (label) label.textContent = 'Play Typing Test (4.0s)';
        if (statusLabel) statusLabel.textContent = 'Finished • Press play to replay';
        if (this.motionState.visAnimationFrame) {
          cancelAnimationFrame(this.motionState.visAnimationFrame);
        }
        if (canvas) {
          const ctx = canvas.getContext('2d');
          this.drawEqualizerBars(ctx, canvas, false);
        }
      });
    }

    const audio = this.motionState.acousticAudioObj;

    if (this.motionState.acousticAudioPlaying) {
      audio.pause();
      audio.currentTime = 0;
      this.motionState.acousticAudioPlaying = false;
      if (icon) icon.textContent = '▶';
      if (label) label.textContent = 'Play Typing Test (4.0s)';
      if (statusLabel) statusLabel.textContent = 'Paused • Ready';
      if (this.motionState.visAnimationFrame) {
        cancelAnimationFrame(this.motionState.visAnimationFrame);
      }
      if (canvas) {
        const ctx = canvas.getContext('2d');
        this.drawEqualizerBars(ctx, canvas, false);
      }
    } else {
      audio.play().then(() => {
        this.motionState.acousticAudioPlaying = true;
        if (icon) icon.textContent = '⏹';
        if (label) label.textContent = 'Stop Audio';
        if (statusLabel) statusLabel.textContent = this.motionState.isPoronDamped 
          ? 'Live Stream: Quad-Poron Dampening Active (240Hz Thock)'
          : 'Live Stream: Bare Metal Acoustic Ping (High Resonance)';
        if (canvas) {
          const ctx = canvas.getContext('2d');
          this.drawEqualizerBars(ctx, canvas, true);
        }
      }).catch(err => {
        console.warn('Audio play notice:', err);
      });
    }
  },

  switchAcousticDamping(isPoron, btn) {
    this.motionState.isPoronDamped = isPoron;
    document.querySelectorAll('.btn-sound-mode').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    const statusLabel = document.getElementById('vis-label');
    if (statusLabel) {
      statusLabel.textContent = isPoron 
        ? 'Acoustic profile: Quad-Poron Foam (Muffled Low-Resonance)' 
        : 'Acoustic profile: Bare Aluminum Ingot (Bright Ping)';
    }

    const canvas = document.getElementById('acoustic-canvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      this.drawEqualizerBars(ctx, canvas, this.motionState.acousticAudioPlaying);
    }
  },

  initCard3DTilt() {
    const cards = document.querySelectorAll('[data-tilt]');
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = ((y - centerY) / centerY) * -9;
        const rotateY = ((x - centerX) / centerX) * 9;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
      });
    });
  },

  initMagneticButtons() {
    const magBtns = document.querySelectorAll('.magnetic-btn');
    magBtns.forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.25}px, ${y * 0.25}px) scale(1.02)`;
      });

      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'translate(0px, 0px) scale(1)';
      });
    });
  },

  bindEvents() {
    const cartOverlay = document.getElementById('cart-drawer-overlay');
    if (cartOverlay) {
      cartOverlay.addEventListener('click', (e) => {
        if (e.target === cartOverlay) this.closeCart();
      });
    }

    const checkoutOverlay = document.getElementById('checkout-modal-overlay');
    if (checkoutOverlay) {
      checkoutOverlay.addEventListener('click', (e) => {
        if (e.target === checkoutOverlay) this.closeCheckoutModal();
      });
    }

    const quickViewOverlay = document.getElementById('quickview-modal-overlay');
    if (quickViewOverlay) {
      quickViewOverlay.addEventListener('click', (e) => {
        if (e.target === quickViewOverlay) this.closeQuickView();
      });
    }

    // Close live search & dropdowns on outside click
    document.addEventListener('click', (e) => {
      const searchBox = document.querySelector('.header-omni-search');
      if (searchBox && !searchBox.contains(e.target)) {
        this.hideLiveSearchResults();
      }
      if (!e.target.closest('.pipeline-dropdown-wrap')) {
        this.closeAllDropdowns();
      }
      const searchOverlay = document.getElementById('pipeline-search-modal');
      if (e.target === searchOverlay) {
        this.closeSearchModal();
      }
    });

    // Escape key handler
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeQuickView();
        this.closeCart();
        this.closeCheckoutModal();
        this.hideLiveSearchResults();
        this.closeSearchModal();
        this.closeAllDropdowns();
      }
    });
  },

  // ==========================================
  // Pipeline Editorial Theme Engine
  // ==========================================
  pipelineCurrentTab: 'edc',
  pipelineSlideIndex: 0,
  pipelineHotspotIndex: 0,

  initPipelineEngine() {
    this.renderSignatureCarousel(this.pipelineCurrentTab);
    this.renderBestsellers();
    this.selectHotspot(0);
  },

  renderPipelineSections() {
    this.renderSignatureCarousel(this.pipelineCurrentTab);
    this.renderBestsellers();
    this.selectHotspot(this.pipelineHotspotIndex || 0);
  },

  switchPipelineTab(tabKey, btnEl) {
    this.pipelineCurrentTab = tabKey;
    this.pipelineSlideIndex = 0;
    const allPills = document.querySelectorAll('.pipeline-tab-pill');
    allPills.forEach(p => p.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    this.renderSignatureCarousel(tabKey);
  },

  getCategoryProducts(tabKey) {
    if (!this.allProducts || !this.allProducts.length) return [];
    const isExcluded = (title) => /playground|toy|luggage|baby|kid|pet|costume|clothes|dress|plush/i.test(title);
    
    if (tabKey === 'edc') {
      const topId = 'prod_edc_tool';
      const topProd = this.allProducts.find(p => p.id === topId);
      const matched = this.allProducts.filter(p => 
        p.id !== topId && !isExcluded(p.title) &&
        ((p.category && p.category.includes('EDC')) || 
        /titanium|bolt action|pen|screwdriver|pry|knife|carabiner|unibody|edc/i.test(p.title))
      );
      return topProd ? [topProd, ...matched] : matched;
    } else if (tabKey === 'power') {
      const topId = 'prod_pulse_dock';
      const topProd = this.allProducts.find(p => p.id === topId);
      const matched = this.allProducts.filter(p => 
        p.id !== topId && !isExcluded(p.title) &&
        ((p.category && p.category.includes('Power')) || 
        /gan|charger|magsafe|dock|power bank|cable|usb-c|hub|charging/i.test(p.title))
      );
      return topProd ? [topProd, ...matched] : matched;
    } else if (tabKey === 'audio') {
      const topIds = ['prod_obsidian_board', 'prod_apex_audio', 'prod_horizon_light'];
      const topProds = topIds.map(id => this.allProducts.find(p => p.id === id)).filter(Boolean);
      const matched = this.allProducts.filter(p => 
        !topIds.includes(p.id) && !isExcluded(p.title) &&
        ((p.category && (p.category.includes('Audio') || p.category.includes('Mechanical') || p.category.includes('Workspace'))) || 
        /audio|speaker|keyboard|dac|switch|keycap|screenbar|desk/i.test(p.title))
      );
      return [...topProds, ...matched];
    }
    return this.allProducts.filter(p => !isExcluded(p.title)).slice(0, 8);
  },

  renderSignatureCarousel(tabKey) {
    const track = document.getElementById('pipeline-carousel-track');
    const counter = document.getElementById('pipeline-tab-counter');
    if (!track) return;

    const items = this.getCategoryProducts(tabKey);
    if (!items.length) return;

    const pageSize = 4;
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    if (this.pipelineSlideIndex >= totalPages) this.pipelineSlideIndex = 0;
    if (this.pipelineSlideIndex < 0) this.pipelineSlideIndex = totalPages - 1;

    if (counter) {
      counter.textContent = `${this.pipelineSlideIndex + 1} / ${totalPages}`;
    }

    const start = this.pipelineSlideIndex * pageSize;
    const visibleItems = items.slice(start, start + pageSize);

    track.innerHTML = visibleItems.map(p => this.createPipelineProductCard(p)).join('');
  },

  slidePipelineCarousel(dir) {
    const items = this.getCategoryProducts(this.pipelineCurrentTab);
    const pageSize = 4;
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));

    if (dir === 'next') {
      this.pipelineSlideIndex = (this.pipelineSlideIndex + 1) % totalPages;
    } else {
      this.pipelineSlideIndex = (this.pipelineSlideIndex - 1 + totalPages) % totalPages;
    }
    this.renderSignatureCarousel(this.pipelineCurrentTab);
  },

  createPipelineProductCard(prod) {
    const { price, comparePrice } = this.getProductPricing(prod);
    return `
      <div class="pipeline-product-card" data-product-id="${prod.id}">
        <div class="pipeline-card-thumb">
          <img src="${prod.image_url}" alt="${prod.title}" class="pipeline-card-img" loading="lazy" onclick="NyxerisStore.openQuickView('${prod.id}')" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
          <span class="pipeline-card-badge">${prod.stock_count > 0 ? 'IN STOCK' : 'LIMITED BATCH'}</span>
          <button type="button" class="pipeline-quick-hover-btn" onclick="NyxerisStore.quickAdd('${prod.id}')">+ QUICK ADD</button>
        </div>
        <div class="pipeline-card-info">
          <div class="pipeline-card-variant">${prod.category || 'Curated Goods'}</div>
          <h3 class="pipeline-card-title" onclick="NyxerisStore.openQuickView('${prod.id}')" title="${prod.title}">${prod.title}</h3>
          <div class="pipeline-card-price-row">
            <span class="pipeline-card-price">$${price.toFixed(2)}</span>
            ${comparePrice > price ? `<span class="pipeline-card-compare">$${comparePrice.toFixed(2)}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  },

  renderBestsellers() {
    const container = document.getElementById('pipeline-bestsellers-grid');
    if (!container) return;

    if (!this.allProducts || !this.allProducts.length) return;

    const priorityIds = ['prod_obsidian_board', 'prod_horizon_light', 'prod_edc_tool', 'prod_pulse_dock'];
    let bestsellers = [];
    priorityIds.forEach(id => {
      const p = this.allProducts.find(item => item.id === id);
      if (p) bestsellers.push(p);
    });

    if (bestsellers.length < 4) {
      const remainder = this.allProducts.filter(p => !bestsellers.some(b => b.id === p.id)).slice(0, 4 - bestsellers.length);
      bestsellers = bestsellers.concat(remainder);
    }

    container.innerHTML = bestsellers.map(p => this.createPipelineProductCard(p)).join('');
  },

  hotspotProducts: [
    {
      id: 'prod_horizon_light',
      title: 'Horizon Pro Screenbar Asymmetric Light',
      kicker: 'WORKSPACE LIGHTING',
      price: 69.00,
      comparePrice: 99.00,
      desc: 'Zero screen reflection, 3000K–6500K dynamic stepless color temperature, weighted aluminum CNC unibody housing with wireless magnetic control dial.',
      image: 'https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=800&auto=format&fit=crop&q=80'
    },
    {
      id: 'prod_obsidian_board',
      title: 'Apex-65 Magnetic HE Rapid-Trigger Keyboard',
      kicker: 'HALL-EFFECT INPUT',
      price: 179.00,
      comparePrice: 229.00,
      desc: '0.1mm–4.0mm adjustable rapid trigger, 8000Hz polling rate, CNC anodized aluminum unibody chassis with custom sound-dampening brass acoustic weight.',
      image: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80'
    },
    {
      id: 'prod_edc_tool',
      title: 'Vektor Grade-5 Titanium Precision Tool',
      kicker: 'PRECISION EDC',
      price: 55.00,
      comparePrice: 79.00,
      desc: 'Aerospace-grade Ti-6Al-4V unibody construct. Integrated ceramic ball-bearing glass breaker, box opener, metric rule, and 1/4" hex bit driver.',
      image: 'https://images.unsplash.com/photo-1585336261026-77564d212974?w=800&auto=format&fit=crop&q=80'
    },
    {
      id: 'prod_lumina_pad',
      title: 'Lumina Anti-Static Vegan-Leather Desk Mat',
      kicker: 'STUDIO SURFACE',
      price: 39.00,
      comparePrice: 59.00,
      desc: 'Dual-textured micro-texture water-resistant surface. High-density natural rubber base eliminates electrostatic discharge and ensures zero slip.',
      image: 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800&auto=format&fit=crop&q=80'
    }
  ],

  selectHotspot(idx) {
    this.pipelineHotspotIndex = idx;
    const pins = document.querySelectorAll('.pipeline-hotspot-pin');
    pins.forEach((pin, i) => {
      if (i === idx) pin.classList.add('active');
      else pin.classList.remove('active');
    });

    const card = document.getElementById('pipeline-hotspot-card');
    if (!card) return;

    const data = this.hotspotProducts[idx] || this.hotspotProducts[0];
    const liveProd = this.allProducts ? this.allProducts.find(p => p.id === data.id) : null;
    const currentPrice = liveProd ? Number(liveProd.price) : data.price;
    const currentCompare = liveProd && liveProd.compare_at_price ? Number(liveProd.compare_at_price) : data.comparePrice;
    const currentImg = liveProd ? liveProd.image_url : data.image;
    const currentTitle = liveProd ? liveProd.title : data.title;

    card.innerHTML = `
      <div style="font-family: var(--font-nav); font-size: 11px; font-weight: 600; color: #767676; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 8px;">CURATED PIECE [${idx + 1}/4]</div>
      <img src="${currentImg}" alt="${currentTitle}" style="width: 100%; aspect-ratio: 16/10; object-fit: cover; border-radius: 2px; margin: 10px 0 14px; border: 1px solid #e8e8e8;" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
      <div style="font-family: var(--font-nav); font-size: 10.5px; font-weight: 600; color: #767676; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">${data.kicker}</div>
      <h3 style="font-family: var(--font-serif); font-size: 18px; font-weight: 400; color: #1f1919; margin-bottom: 6px; line-height: 1.35;">${currentTitle}</h3>
      <div style="font-family: var(--font-nav); font-size: 15px; font-weight: 600; color: #1f1919; margin-bottom: 12px;">
        $${currentPrice.toFixed(2)}
        ${currentCompare > currentPrice ? `<span style="color: #767676; font-size: 13px; text-decoration: line-through; margin-left: 8px;">$${currentCompare.toFixed(2)}</span>` : ''}
      </div>
      <p style="font-size: 12.5px; color: #424242; line-height: 1.55; margin-bottom: 18px; font-family: var(--font-sans);">${data.desc}</p>
      <button type="button" class="btn-solid-white" style="width: 100%; justify-content: center; padding: 11px; font-size: 11px; letter-spacing: 0.12em;" onclick="NyxerisStore.quickAdd('${data.id}')">
        ADD TO BAG
      </button>
    `;
  },

  quickAdd(productId) {
    this.addToCart(productId);
  },

  toggleDropdown(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const wasOpen = el.classList.contains('open');
    this.closeAllDropdowns();
    if (!wasOpen) el.classList.add('open');
  },

  closeAllDropdowns() {
    document.querySelectorAll('.pipeline-dropdown-menu').forEach(menu => {
      menu.classList.remove('open');
    });
  },

  setCurrency(code, sym) {
    const label = document.getElementById('active-currency-label');
    if (label) {
      if (code === 'USD') label.textContent = 'UNITED STATES (US $)';
      else if (code === 'CAD') label.textContent = 'CANADA (CA $)';
      else if (code === 'GBP') label.textContent = 'UNITED KINGDOM (GB £)';
      else if (code === 'EUR') label.textContent = 'EUROPEAN UNION (€)';
      else label.textContent = `${code} (${sym})`;
    }
    this.closeAllDropdowns();
    this.showToast(`Currency set to ${code}`);
  },

  setLanguage(lang) {
    const label = document.getElementById('active-lang-label');
    if (label) label.textContent = lang.toUpperCase();
    this.closeAllDropdowns();
    this.showToast(`Language set to ${lang}`);
  },

  openSearchModal() {
    const modal = document.getElementById('pipeline-search-modal');
    const input = document.getElementById('pipeline-modal-search-input');
    if (!modal) return;
    modal.style.display = 'flex';
    if (input) {
      input.value = '';
      input.focus();
    }
    this.handleModalSearch('');
  },

  closeSearchModal() {
    const modal = document.getElementById('pipeline-search-modal');
    if (modal) modal.style.display = 'none';
  },

  clearModalSearch() {
    const input = document.getElementById('pipeline-modal-search-input');
    const clearBtn = document.getElementById('btn-clear-modal-search');
    if (input) {
      input.value = '';
      input.focus();
    }
    if (clearBtn) clearBtn.style.display = 'none';
    this.handleModalSearch('');
  },

  handleModalSearch(query) {
    const q = (query || '').trim().toLowerCase();
    const resultsContainer = document.getElementById('pipeline-modal-search-results');
    const clearBtn = document.getElementById('btn-clear-modal-search');
    if (clearBtn) clearBtn.style.display = q.length ? 'block' : 'none';

    if (!resultsContainer) return;

    if (!this.allProducts || !this.allProducts.length) {
      resultsContainer.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading catalog...</div>`;
      return;
    }

    let matches = [];
    if (!q) {
      matches = this.allProducts.slice(0, 5);
    } else {
      matches = this.allProducts.filter(p => 
        (p.title && p.title.toLowerCase().includes(q)) ||
        (p.category && p.category.toLowerCase().includes(q)) ||
        (p.sku && p.sku.toLowerCase().includes(q)) ||
        (p.description && p.description.toLowerCase().includes(q))
      ).slice(0, 8);
    }

    if (!matches.length) {
      resultsContainer.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #767676; font-family: var(--font-sans);">
          No products found matching "<strong>${query}</strong>". Try searching "lighting", "titanium", "desk", or "audio".
        </div>
      `;
      return;
    }

    resultsContainer.innerHTML = `
      ${!q ? `<div style="font-size: 11px; font-family: var(--font-nav); font-weight: 600; color: #767676; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 12px;">SUGGESTED PRODUCTS</div>` : ''}
      ${matches.map(p => `
        <div class="search-result-row" onclick="NyxerisStore.openQuickView('${p.id}'); NyxerisStore.closeSearchModal();" style="display: flex; align-items: center; gap: 16px; padding: 12px; border-radius: 2px; cursor: pointer; transition: background 0.15s ease; border-bottom: 1px solid #e8e8e8;">
          <img src="${p.image_url}" alt="${p.title}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 2px; border: 1px solid #e8e8e8;" onerror="this.src='/static/images/products/nyxeris-lumina-desk-mat.jpg'" />
          <div style="flex: 1; min-width: 0;">
            <div style="font-size: 10px; color: #767676; font-family: var(--font-nav); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 2px;">${p.category || 'Curated Goods'}</div>
            <div style="font-size: 13.5px; font-weight: 500; color: #1f1919; font-family: var(--font-sans); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.title}</div>
          </div>
          <div style="font-family: var(--font-nav); font-size: 13px; font-weight: 600; color: #1f1919;">$${Number(p.price).toFixed(2)}</div>
        </div>
      `).join('')}
    `;
  },

  handleNewsletterSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('newsletter-email-input');
    const msg = document.getElementById('newsletter-feedback-msg');
    if (msg) {
      msg.style.display = 'block';
    }
    if (input) {
      input.value = '';
    }
    this.showToast('Subscribed to Nyxeris Private Register');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  NyxerisStore.init();
});
