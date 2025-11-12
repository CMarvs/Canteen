/* ===== RMLCanteen — API-Connected Version =====
   - Uses FastAPI backend with NeonDB PostgreSQL
   - Admin account: admin@canteen / admin123
   - Version: 2.0 - Profile update enabled
*/

// API Base URL
const API_BASE = '';  // Same origin

// Storage keys (still using localStorage for cart and current user session)
const KEY_CURRENT = 'canteen_current_v2';
const KEY_CART = 'canteen_cart_v2';
const KEY_SOLDOUT = 'canteen_soldout_v1';
const DELIVERY_FEE = 10;

/* ---------- Local Storage Helpers (for session only) ---------- */
function readLocal(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch(e){ return fallback; }
}
function writeLocal(key, val) { localStorage.setItem(key, JSON.stringify(val)); }

/* ---------- Current User Session ---------- */
function getCurrent(){ return readLocal(KEY_CURRENT, null); }
function saveCurrent(u){ writeLocal(KEY_CURRENT, u); }
function clearCurrent(){ localStorage.removeItem(KEY_CURRENT); }

/* ---------- Auth: Register ---------- */
async function registerUser(){
  const name = (document.getElementById('regName')?.value || '').trim();
  const email = (document.getElementById('regEmail')?.value || '').trim().toLowerCase();
  const pass = (document.getElementById('regPass')?.value || '').trim();
  const confirmPass = (document.getElementById('regConfirmPass')?.value || '').trim();

  if(!name || !email || !pass) {
    return alert('Please fill all fields.');
  }

  if(pass.length < 4) {
    return alert('Password must be at least 4 characters.');
  }

  if(pass !== confirmPass) {
    return alert('❌ Passwords do not match! Please try again.');
  }

  try {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password: pass })
    });

    const data = await response.json();
    
    if(response.ok) {
      alert('✅ Account created successfully! You can now login.');
      location.href = 'index.html';
    } else {
      alert(data.detail || 'Registration failed');
    }
  } catch(error) {
    console.error('Registration error:', error);
    alert('Registration failed. Please try again.');
  }
}

/* ---------- Auth: Login ---------- */
async function loginUser(){
  const email = (document.getElementById('loginEmail')?.value || '').trim().toLowerCase();
  const pass = (document.getElementById('loginPass')?.value || '').trim();
  
  if(!email || !pass) return alert('Enter email and password.');

  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: pass })
    });

    const data = await response.json();
    
    if(response.ok) {
      // Save user session locally
      saveCurrent({ 
        id: data.id, 
        name: data.name, 
        email: data.email, 
        role: data.role 
      });
      
      // Redirect based on role
      if(data.role === 'admin') {
        location.href = 'admin.html';
      } else {
        location.href = 'order.html';
      }
    } else {
      alert(data.detail || 'Invalid credentials');
    }
  } catch(error) {
    console.error('Login error:', error);
    alert('Login failed. Please try again.');
  }
}

/* ---------- Auth: Logout ---------- */
function logoutUser(){
  clearCurrent();
  localStorage.removeItem(KEY_CART); // Clear cart on logout
  location.href = 'index.html';
}

/* ---------- Menu Data (Fetched from API) ---------- */
let MENU_CACHE = null; // Cache menu items to avoid repeated API calls

/* ---------- Menu Functions ---------- */
async function fetchMenuItems() {
  try {
    const response = await fetch(`${API_BASE}/menu`);
    if (!response.ok) {
      console.error('Failed to fetch menu items');
      return [];
    }
    const items = await response.json();
    MENU_CACHE = items;
    return items;
  } catch(error) {
    console.error('Error fetching menu items:', error);
    return [];
  }
}

function getMenuById(id) {
  if (!MENU_CACHE) return null;
  return MENU_CACHE.find(item => item.id === id || item.id.toString() === id.toString());
}

/* ---------- Cart Functions (localStorage) ---------- */
function getCart(){ return readLocal(KEY_CART, []); }
function saveCart(c){ writeLocal(KEY_CART, c); }
function clearCart(){ saveCart([]); renderCart(); }

async function addToCartById(id, qty = 1){
  // Ensure menu is loaded
  if (!MENU_CACHE) {
    await fetchMenuItems();
  }
  
  const item = getMenuById(id);
  if(!item) {
    return alert('Item not found. Please refresh the page.');
  }
  
  // Check if item is available
  if(item.is_available === false) {
    return alert('Sorry — this item is sold out.');
  }
  
  const cart = getCart();
  const row = cart.find(r => r.id === id || r.id.toString() === id.toString());
  if(row) {
    row.qty += qty;
  } else {
    cart.push({ 
      id: item.id, 
      name: item.name, 
      price: item.price, 
      qty 
    });
  }
  
  saveCart(cart);
  renderCart();
}

function updateCartQty(id, newQty){
  let cart = getCart();
  if(newQty <= 0) cart = cart.filter(x => x.id !== id);
  else cart = cart.map(x => x.id === id ? {...x, qty: Number(newQty)} : x);
  saveCart(cart);
  renderCart();
}

function removeCartItem(id){
  if(!confirm('Remove item from cart?')) return;
  const cart = getCart().filter(x => x.id !== id);
  saveCart(cart);
  renderCart();
}

function calcSubtotal(){
  const cart = getCart();
  return cart.reduce((s, it) => s + (Number(it.price) * Number(it.qty || 1)), 0);
}

/* ---------- Render Cart UI ---------- */
function renderCart(){
  const listEl = document.getElementById('cartList');
  if(!listEl) return;
  const cart = getCart();
  
  if(cart.length === 0){
    listEl.innerHTML = '<div class="muted">Cart is empty</div>';
  } else {
    listEl.innerHTML = cart.map(it => `
      <div class="cart-item">
        <div>
          <strong>${it.name}</strong><br>
          <span class="muted">₱${Number(it.price).toFixed(2)} × ${it.qty}</span>
        </div>
        <div>
          <button class="btn small" onclick="promptEditQty('${it.id}', ${it.qty})">Edit</button>
          <button class="btn small ghost" onclick="removeCartItem('${it.id}')">Delete</button>
        </div>
      </div>
    `).join('');
  }
  
  const subtotal = calcSubtotal();
  const grand = subtotal + DELIVERY_FEE;
  const sEl = document.getElementById('subtotal');
  const gEl = document.getElementById('grandTotal') || document.getElementById('total') || null;
  if(sEl) sEl.innerText = subtotal.toFixed(2);
  if(gEl) gEl.innerText = grand.toFixed(2);
}

function promptEditQty(id, currentQty){
  const val = prompt('Enter new quantity:', currentQty);
  if(val === null) return;
  const n = Number(val);
  if(isNaN(n) || n <= 0) return alert('Invalid quantity');
  updateCartQty(id, n);
}

/* ---------- Menu Rendering ---------- */
async function loadMenuToPage(){
  const budget = document.getElementById('budgetContainer');
  const foods = document.getElementById('foodsContainer');
  const drinks = document.getElementById('drinksContainer');
  
  // Show loading state
  if(budget) budget.innerHTML = '<div class="muted">Loading...</div>';
  if(foods) foods.innerHTML = '<div class="muted">Loading...</div>';
  if(drinks) drinks.innerHTML = '<div class="muted">Loading...</div>';
  
  // Fetch menu items from API
  const menuItems = await fetchMenuItems();
  
  if(menuItems.length === 0) {
    const emptyMsg = '<div class="muted">No menu items available. Please contact admin.</div>';
    if(budget) budget.innerHTML = emptyMsg;
    if(foods) foods.innerHTML = emptyMsg;
    if(drinks) drinks.innerHTML = emptyMsg;
    return;
  }
  
  // Group by category
  const grouped = {
    budget: menuItems.filter(i => i.category === 'budget'),
    foods: menuItems.filter(i => i.category === 'foods'),
    drinks: menuItems.filter(i => i.category === 'drinks')
  };
  
  if(budget) budget.innerHTML = grouped.budget.map(i => itemCardHtml(i)).join('');
  if(foods) foods.innerHTML = grouped.foods.map(i => itemCardHtml(i)).join('');
  if(drinks) drinks.innerHTML = grouped.drinks.map(i => itemCardHtml(i)).join('');
}

function itemCardHtml(i){
  const isSold = i.is_available === false;
  return `
    <div class="item card ${isSold ? 'sold' : ''}">
      <div>
        <h4 style="margin:0 0 6px 0;">${i.name}</h4>
        <div class="muted">₱${Number(i.price).toFixed(2)}</div>
      </div>
      <div style="margin-top:8px;">
        ${isSold ? `<div class="sold-label">SOLD OUT</div>` : `
          <div style="display:flex;gap:8px;align-items:center;justify-content:center;">
            <input class="qty" type="number" id="q_${i.id}" value="1" min="1">
            <button class="btn small" onclick="addToCartWithQty(${i.id})">Add</button>
          </div>
        `}
      </div>
    </div>
  `;
}

async function addToCartWithQty(id){
  const qEl = document.getElementById('q_' + id);
  const qty = qEl ? Number(qEl.value) || 1 : 1;
  await addToCartById(id, qty);
}

/* ---------- Order Placement (API) ---------- */
async function placeOrder(name, contact, address, idProofBase64 = null){
  const cur = getCurrent();
  if(!cur) { 
    alert('Please login'); 
    location.href='index.html'; 
    return; 
  }
  
  const cart = getCart();
  if(cart.length === 0) return alert('Cart is empty');

  // Check if any items in cart are sold out (validate against current menu)
  if (!MENU_CACHE) {
    await fetchMenuItems();
  }
  const blocked = cart.filter(cartItem => {
    const menuItem = getMenuById(cartItem.id);
    return !menuItem || menuItem.is_available === false;
  });
  if(blocked.length > 0) {
    alert('Some items in your cart are sold out. Please remove them first.');
    return;
  }

  const subtotal = calcSubtotal();
  const total = subtotal + DELIVERY_FEE;

  try {
    const response = await fetch(`${API_BASE}/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: cur.id,
        fullname: name,
        contact: contact,
        location: address,
        items: cart,
        total: total,
        id_proof: idProofBase64
      })
    });

    if(response.ok) {
      // Clear cart
      saveCart([]);
      
      // Clear form fields on order page if still there
      const delName = document.getElementById('delName');
      const delContact = document.getElementById('delContact');
      const delAddress = document.getElementById('delAddress');
      const idProofFile = document.getElementById('idProofFile');
      if(delName) delName.value = '';
      if(delContact) delContact.value = '';
      if(delAddress) delAddress.value = '';
      if(idProofFile) {
        idProofFile.value = '';
        // Clear ID proof preview if exists
        const preview = document.getElementById('idProofPreview');
        const capture = document.getElementById('idProofCapture');
        if(preview) preview.style.display = 'none';
        if(capture) capture.style.display = 'block';
      }
      
      // Re-render cart to show it's empty
      if(typeof renderCart === 'function') {
        renderCart();
      }
      
      alert('✅ Order placed successfully!');
      
      // Small delay to ensure order is committed, then redirect
      setTimeout(() => {
        location.href = 'orders.html?t=' + Date.now(); // Add timestamp to prevent cache
      }, 300);
    } else {
      const data = await response.json();
      alert(data.detail || 'Order placement failed');
    }
  } catch(error) {
    console.error('Order placement error:', error);
    alert('Failed to place order. Please try again.');
  }
}

/* ---------- User Orders (API) ---------- */
async function renderUserOrders(){
  const cur = getCurrent();
  if(!cur){ location.href='index.html'; return; }
  
  const list = document.getElementById('ordersList');
  const no = document.getElementById('noOrders');
  if(!list) return;

  try {
    // Add cache-busting timestamp to ensure fresh data
    const response = await fetch(`${API_BASE}/orders?t=${Date.now()}`, {
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    const allOrders = await response.json();
    
    // Filter orders for current user
    const mine = allOrders
      .filter(o => o.user_id === cur.id)
      .reverse();

    if(mine.length === 0){
      list.innerHTML = '';
      if(no) no.style.display = 'block';
      return;
    }
    
    if(no) no.style.display = 'none';
    list.innerHTML = mine.map(o => orderCardHtmlForUser(o)).join('');
  } catch(error) {
    console.error('Error loading orders:', error);
    list.innerHTML = '<p class="muted">Failed to load orders</p>';
  }
}

function orderCardHtmlForUser(o){
  const statusBadge = statusBadgeHtml(o.status);
  const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
  const itemsText = items.map(i => `${i.name} ×${i.qty}`).join('<br>');
  const canCancel = o.status === 'Pending';
  
  return `
    <div class="order-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div><strong>Order #${o.id}</strong><div class="muted small">${new Date(o.created_at).toLocaleString()}</div></div>
        <div>${statusBadge}</div>
      </div>
      <div style="margin-top:8px">${itemsText}</div>
      <div class="muted small" style="margin-top:8px">Delivery: ${o.fullname} • ${o.contact} • ${o.location}</div>
      <div style="margin-top:8px;display:flex;gap:8px;align-items:center;">
        <div><strong>Total:</strong> ₱${Number(o.total).toFixed(2)}</div>
      </div>
    </div>
  `;
}

function statusBadgeHtml(status){
  const map = {
    'Pending': `<span class="order-status status-Pending">Pending</span>`,
    'Preparing': `<span class="order-status status-Preparing">Preparing</span>`,
    'Out for Delivery': `<span class="order-status status-Out">Out for Delivery</span>`,
    'Delivered': `<span class="order-status status-Delivered">Delivered</span>`
  };
  return map[status] || `<span class="order-status">${status}</span>`;
}

/* ---------- Old Admin Menu Editor (removed - now handled in admin.html) ---------- */

/* ---------- Profile Functions ---------- */
function loadProfilePage(){
  const cur = getCurrent();
  if(!cur) { location.href='index.html'; return; }
  document.getElementById('profileName').value = cur.name || '';
  document.getElementById('profileEmail').value = cur.email || '';
}

async function saveProfile(){
  const cur = getCurrent();
  if(!cur) {
    alert('Please login first');
    location.href = 'index.html';
    return;
  }
  
  const nameInput = document.getElementById('profileName');
  const passInput = document.getElementById('profilePass');
  
  if(!nameInput || !passInput) {
    console.error('Profile form elements not found');
    return;
  }
  
  const name = (nameInput.value || '').trim();
  const pass = (passInput.value || '').trim();
  
  // Get current name from session if name field is empty
  const currentName = cur.name || '';
  const nameToUpdate = name || currentName;
  
  // Check if there's anything to update
  const nameChanged = name && name !== currentName;
  const passwordProvided = pass && pass.length > 0;
  
  if(!nameChanged && !passwordProvided) {
    return alert('Nothing to update. Please enter a new name or new password.');
  }

  if(pass && pass.length < 4) {
    return alert('Password must be at least 4 characters.');
  }

  try {
    const updateData = {};
    
    // Always include name (either new or current)
    if(nameToUpdate) {
      updateData.name = nameToUpdate;
    }
    
    // Only include password if provided
    if(passwordProvided) {
      updateData.password = pass;
    }

    console.log('Updating profile:', { userId: cur.id, updateData });

    const response = await fetch(`${API_BASE}/users/${cur.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
    });

    if (!response.ok) {
      let errorMessage = 'Failed to update profile';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch(e) {
        errorMessage = `Server returned ${response.status}: ${response.statusText}`;
      }
      alert(`❌ ${errorMessage}`);
      return;
    }

    const data = await response.json();
    console.log('Profile update response:', data);
    
    // Update local session with updated user data
    if(data.user) {
      saveCurrent({
        id: cur.id,
        name: data.user.name || nameToUpdate,
        email: cur.email,
        role: cur.role
      });
    }

    alert('✅ Profile updated successfully!');
    
    // Clear password field
    passInput.value = '';
    
    // Reload profile page to show updated information
    loadProfilePage();
  } catch(error) {
    console.error('Profile update error:', error);
    alert('Failed to update profile. Please check your connection and try again.');
  }
}

/* ---------- Page Helpers ---------- */
function ensureLoggedIn(requiredRole){
  const cur = getCurrent();
  if(!cur) { 
    location.href = 'index.html'; 
    return; 
  }
  if(requiredRole && cur.role !== requiredRole) {
    alert('Access denied.');
    location.href = cur.role === 'admin' ? 'admin.html' : 'order.html';
  }
}

/* ---------- Page Init ---------- */
window.addEventListener('DOMContentLoaded', () => {
  renderCart();
});
