/* ===== RMLCanteen — API-Connected Version =====
   - Uses FastAPI backend with NeonDB PostgreSQL
   - Admin account: admin@canteen / admin123
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

/* ---------- Menu Data (Frontend - same as before) ---------- */
const DEFAULT_MENU = {
  budget: [
    { id: 's1', name: 'Budget Meal A (Fried Chicken + Rice)', price: 50 },
    { id: 's2', name: 'Budget Meal B (Pork Adobo + Rice)', price: 50 },
    { id: 's3', name: 'Budget Meal C (Burger Steak + Rice)', price: 50 },
    { id: 's4', name: 'Budget Meal D (Hotdog + Egg + Rice)', price: 45 }
  ],
  foods: [
    { id: 'f1', name: 'Sisig', price: 70 },
    { id: 'f2', name: 'Dinakdakan', price: 75 },
    { id: 'f3', name: 'Pork Adobo', price: 65 },
    { id: 'f4', name: 'Beef Caldereta', price: 80 },
    { id: 'f5', name: 'Carbonara', price: 70 },
    { id: 'f6', name: 'Spaghetti', price: 60 },
    { id: 'f7', name: 'Palabok', price: 60 },
    { id: 'f8', name: 'Fried Rice', price: 20 }
  ],
  drinks: [
    { id: 'd1', name: 'Coke', price: 25 },
    { id: 'd2', name: 'Sprite', price: 25 },
    { id: 'd3', name: 'Royal', price: 25 },
    { id: 'd4', name: 'Bottled Water', price: 15 },
    { id: 'd5', name: 'C2 Green Tea', price: 20 },
    { id: 'd6', name: 'Iced Coffee', price: 35 }
  ]
};

/* ---------- Sold Out Management (localStorage for now, can be moved to API) ---------- */
function getSoldOutItems() {
  return readLocal(KEY_SOLDOUT, []);
}
function saveSoldOutItems(list) {
  writeLocal(KEY_SOLDOUT, list);
}
function toggleSoldOut(itemId) {
  let soldOut = getSoldOutItems();
  if (soldOut.includes(itemId)) {
    soldOut = soldOut.filter(id => id !== itemId);
  } else {
    soldOut.push(itemId);
  }
  saveSoldOutItems(soldOut);
  renderAdminMenuList();
  if(typeof loadMenuToPage === 'function') loadMenuToPage();
  alert('✅ Item availability updated.');
}

/* ---------- Cart Functions (localStorage) ---------- */
function getCart(){ return readLocal(KEY_CART, []); }
function saveCart(c){ writeLocal(KEY_CART, c); }
function clearCart(){ saveCart([]); renderCart(); }

function addToCartById(id, qty = 1){
  const menu = {...DEFAULT_MENU};
  const all = [...menu.budget, ...menu.foods, ...menu.drinks];
  const item = all.find(x => x.id === id);
  const soldOut = getSoldOutItems();
  
  if(!item) return alert('Item not found.');
  if(soldOut.includes(id)) return alert('Sorry — this item is sold out.');
  
  const cart = getCart();
  const row = cart.find(r => r.id === id);
  if(row) row.qty += qty;
  else cart.push({ id: item.id, name: item.name, price: item.price, qty });
  
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
function loadMenuToPage(){
  const budget = document.getElementById('budgetContainer');
  const foods = document.getElementById('foodsContainer');
  const drinks = document.getElementById('drinksContainer');
  if(budget) budget.innerHTML = DEFAULT_MENU.budget.map(i => itemCardHtml(i)).join('');
  if(foods) foods.innerHTML = DEFAULT_MENU.foods.map(i => itemCardHtml(i)).join('');
  if(drinks) drinks.innerHTML = DEFAULT_MENU.drinks.map(i => itemCardHtml(i)).join('');
}

function itemCardHtml(i){
  const soldOut = getSoldOutItems();
  const isSold = soldOut.includes(i.id);
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
            <button class="btn small" onclick="addToCartWithQty('${i.id}')">Add</button>
          </div>
        `}
      </div>
    </div>
  `;
}

function addToCartWithQty(id){
  const qEl = document.getElementById('q_' + id);
  const qty = qEl ? Number(qEl.value) || 1 : 1;
  addToCartById(id, qty);
}

/* ---------- Order Placement (API) ---------- */
async function placeOrder(name, contact, address){
  const cur = getCurrent();
  if(!cur) { 
    alert('Please login'); 
    location.href='index.html'; 
    return; 
  }
  
  const cart = getCart();
  if(cart.length === 0) return alert('Cart is empty');

  const soldOut = getSoldOutItems();
  const blocked = cart.filter(it => soldOut.includes(it.id));
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
        total: total
      })
    });

    if(response.ok) {
      saveCart([]); // Clear cart
      alert('✅ Order placed successfully!');
      location.href = 'orders.html';
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
    const response = await fetch(`${API_BASE}/orders`);
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

/* ---------- Admin Menu Editor ---------- */
function renderAdminMenuList(){
  const cur = getCurrent();
  if(!cur || cur.role !== 'admin') return;
  const menuArea = document.getElementById('adminMenuList');
  if(!menuArea) return;

  const soldOut = getSoldOutItems();
  const sections = Object.keys(DEFAULT_MENU);

  menuArea.innerHTML = sections.map(sec => {
    const itemsHtml = DEFAULT_MENU[sec].map(i => {
      const isSold = soldOut.includes(i.id);
      return `
        <div class="item-row">
          <span>${i.name}</span>
          <div class="price">₱${Number(i.price).toFixed(2)}</div>
          <button class="btn small ${isSold ? 'ghost' : ''}" onclick="toggleSoldOut('${i.id}')">
            ${isSold ? 'Mark Available' : 'Mark Sold Out'}
          </button>
        </div>
      `;
    }).join('');
    return `
      <div class="card" style="margin-bottom:12px;">
        <h4 style="margin:0 0 8px 0;">${sec.charAt(0).toUpperCase() + sec.slice(1)}</h4>
        ${itemsHtml}
      </div>
    `;
  }).join('');
}

/* ---------- Profile Functions ---------- */
function loadProfilePage(){
  const cur = getCurrent();
  if(!cur) { location.href='index.html'; return; }
  document.getElementById('profileName').value = cur.name || '';
  document.getElementById('profileEmail').value = cur.email || '';
}

async function saveProfile(){
  const cur = getCurrent();
  if(!cur) return;
  
  const name = (document.getElementById('profileName')?.value || '').trim();
  const pass = (document.getElementById('profilePass')?.value || '').trim();
  
  if(!name && !pass) {
    return alert('Nothing to update');
  }

  // Note: You'll need to add a PUT /users/{id} endpoint in server.py for this
  alert('Profile update coming soon!');
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
