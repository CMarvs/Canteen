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

  // ID proof is handled in register.html script
  // This function is overridden there to include ID proof
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

    // Check if response is ok before parsing JSON
    let data;
    try {
      data = await response.json();
    } catch(jsonError) {
      console.error('Failed to parse response:', jsonError);
      alert('❌ Server error. Please try again or contact support.');
      return;
    }
    
    if(response.ok) {
      // Check if user is approved (admins are always approved)
      if(data.role !== 'admin' && (data.is_approved === false || data.is_approved === 0)) {
        alert('⏳ Your account is pending admin approval. Please wait for approval before logging in.');
        return;
      }
      
      // Validate required fields
      if(!data.id || !data.email || !data.role) {
        console.error('Invalid user data received:', data);
        alert('❌ Invalid user data. Please try again.');
        return;
      }
      
      // Save user session locally
      saveCurrent({ 
        id: data.id, 
        name: data.name || data.email, 
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
      // Handle error response
      const errorMsg = data.detail || data.message || 'Invalid credentials';
      alert(`❌ ${errorMsg}`);
    }
  } catch(error) {
    console.error('Login error:', error);
    alert('❌ Login failed. Please check your connection and try again.');
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
  
  // Check stock quantity
  const quantity = item.quantity || 0;
  if(quantity === 0) {
    return alert('Sorry — this item is out of stock.');
  }
  
  const cart = getCart();
  const row = cart.find(r => r.id === id || r.id.toString() === id.toString());
  const currentCartQty = row ? row.qty : 0;
  const newTotalQty = currentCartQty + qty;
  
  // Check if adding this quantity would exceed available stock
  if(newTotalQty > quantity) {
    return alert(`Sorry — only ${quantity} item(s) available in stock. You already have ${currentCartQty} in your cart.`);
  }
  
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

async function updateCartQty(id, newQty){
  // Ensure menu is loaded to check stock
  if (!MENU_CACHE) {
    await fetchMenuItems();
  }
  
  const item = getMenuById(id);
  if(item) {
    const quantity = item.quantity || 0;
    if(newQty > quantity) {
      return alert(`Sorry — only ${quantity} item(s) available in stock.`);
    }
  }
  
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
  try {
    const listEl = document.getElementById('cartList');
    if(!listEl) return;
    
    const cart = getCart();
    if (!Array.isArray(cart)) {
      saveCart([]);
      listEl.innerHTML = '<div class="muted">Cart is empty</div>';
      return;
    }
    
    // Validate and filter cart items
    const validCart = cart.filter(item => {
      if (!item || !item.id) return false;
      const menuItem = getMenuById(item.id);
      return menuItem && menuItem.is_available !== false;
    });
    
    // Update cart if items were filtered
    if (validCart.length !== cart.length) {
      saveCart(validCart);
    }
    
    if(validCart.length === 0){
      listEl.innerHTML = '<div class="muted">Cart is empty</div>';
    } else {
      listEl.innerHTML = validCart.map(it => {
        try {
          const price = Number(it.price) || 0;
          const qty = Number(it.qty) || 1;
          return `
            <div class="cart-item" style="animation: fadeIn 0.3s ease-out;">
              <div>
                <strong>${it.name || 'Unknown Item'}</strong><br>
                <span class="muted">₱${price.toFixed(2)} × ${qty}</span>
              </div>
              <div>
                <button class="btn small" onclick="promptEditQty('${it.id}', ${qty})" style="transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">Edit</button>
                <button class="btn small ghost" onclick="removeCartItem('${it.id}')" style="transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">Delete</button>
              </div>
            </div>
          `;
        } catch(err) {
          console.error('Error rendering cart item:', err, it);
          return '';
        }
      }).filter(html => html).join('');
    }
    
    const subtotal = calcSubtotal();
    const grand = subtotal + DELIVERY_FEE;
    const sEl = document.getElementById('subtotal');
    const gEl = document.getElementById('grandTotal') || document.getElementById('total') || null;
    if(sEl) sEl.innerText = subtotal.toFixed(2);
    if(gEl) gEl.innerText = grand.toFixed(2);
  } catch(error) {
    console.error('Error rendering cart:', error);
    const listEl = document.getElementById('cartList');
    if(listEl) {
      listEl.innerHTML = '<div class="muted" style="color: #e74c3c;">Error loading cart. Please refresh the page.</div>';
    }
  }
}

async function promptEditQty(id, currentQty){
  try {
    const val = prompt('Enter new quantity:', currentQty);
    if(val === null || val.trim() === '') return;
    
    const n = Number(val);
    if(isNaN(n) || n <= 0) {
      alert('⚠️ Please enter a valid quantity (greater than 0)');
      return;
    }
    
    // Check stock availability
    const item = getMenuById(id);
    if (item) {
      const quantity = item.quantity || 0;
      if (quantity > 0 && n > quantity) {
        alert(`⚠️ Only ${quantity} available in stock.`);
        return;
      }
    }
    
    await updateCartQty(id, n);
  } catch(error) {
    console.error('Error editing quantity:', error);
    alert('❌ Failed to update quantity. Please try again.');
  }
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
  const quantity = i.quantity || 0;
  const stockText = quantity > 0 ? `📦 ${quantity} available` : '⚠️ Out of Stock';
  const stockColor = quantity > 0 ? (quantity < 10 ? '#ff9800' : '#4caf50') : '#f44336';
  const isOutOfStock = quantity === 0 || isSold;
  const stockBadgeStyle = `display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; background: ${stockColor}15; color: ${stockColor}; border: 1px solid ${stockColor}40; margin-top: 6px;`;
  
  return `
    <div class="item card ${isOutOfStock ? 'sold' : ''}">
      <div>
        <h4 style="margin:0 0 6px 0;">${i.name}</h4>
        <div class="muted" style="font-size: 1rem; margin-bottom: 6px;">₱${Number(i.price).toFixed(2)}</div>
        <div style="${stockBadgeStyle}">${stockText}</div>
      </div>
      <div style="margin-top:12px;">
        ${isOutOfStock ? `<div class="sold-label">SOLD OUT</div>` : `
          <div style="display:flex;gap:8px;align-items:center;justify-content:center;">
            <input class="qty" type="number" id="q_${i.id}" value="1" min="1" max="${quantity}" style="width: 60px; text-align: center;">
            <button class="btn small" onclick="addToCartWithQty(${i.id})">Add to Cart</button>
          </div>
        `}
      </div>
    </div>
  `;
}

async function addToCartWithQty(id){
  try {
  const qEl = document.getElementById('q_' + id);
  const qty = qEl ? Number(qEl.value) || 1 : 1;
  await addToCartById(id, qty);
}

/* ---------- Order Placement (API) ---------- */
async function placeOrder(name, contact, address, paymentMethod){
  const cur = getCurrent();
  if(!cur) { 
    alert('Please login'); 
    location.href='index.html'; 
    return; 
  }
  
  const cart = getCart();
  if(cart.length === 0) {
    alert('Cart is empty');
    return;
  }

  // Validate full name: must have at least 3 words (First, Middle, Last)
  const nameWords = name.trim().split(/\s+/).filter(word => word.length > 0);
  if(nameWords.length < 3) {
    alert('Please enter your full name: First Name, Middle Name, and Last Name (at least 3 words).');
    return;
  }

  // Validate contact number: must be exactly 11 digits
  const contactDigits = contact.replace(/\D/g, ''); // Remove non-digits
  if(contactDigits.length !== 11) {
    alert('Contact number must be exactly 11 digits (e.g., 09123456789).');
    return;
  }

  // Check if any items in cart are sold out (validate against current menu)
  if (!MENU_CACHE) {
    await fetchMenuItems();
  }
  const blocked = cart.filter(cartItem => {
    const menuItem = getMenuById(cartItem.id);
    return !menuItem || menuItem.is_available === false;
  });
  if(blocked.length > 0) {
    alert('Some items in your cart are sold out or out of stock. Please remove them or adjust quantities first.');
    return;
  }

  const subtotal = calcSubtotal();
  const total = subtotal + DELIVERY_FEE;

  // Get payment details
  let paymentDetails = {};
  if (paymentMethod === 'cod') {
    // COD doesn't need payment details
    paymentDetails = {};
  } else if (paymentMethod === 'gcash') {
    paymentDetails = {
      gcashNumber: document.getElementById('gcashNumber').value.replace(/\D/g, '')
    };
  }

  try {
    // First, create the order
    const orderResponse = await fetch(`${API_BASE}/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: cur.id,
        fullname: name.trim(),
        contact: contactDigits,
        location: address.trim(),
        items: cart,
        total: total,
        payment_method: paymentMethod,
        payment_status: 'pending'
      })
    });

    if(!orderResponse.ok) {
      const errorData = await orderResponse.json();
      alert(errorData.detail || 'Order placement failed');
      return;
    }

    const orderData = await orderResponse.json();
    const orderId = orderData.order?.id || orderData.id;

    // For COD, skip payment processing (payment is done on delivery)
    if (paymentMethod === 'cod') {
      // COD orders are automatically marked as paid
      // Clear cart and show success
      saveCart([]);
      
      // Clear form fields
      const delName = document.getElementById('delName');
      const delContact = document.getElementById('delContact');
      const delAddress = document.getElementById('delAddress');
      if(delName) delName.value = '';
      if(delContact) delContact.value = '';
      if(delAddress) delAddress.value = '';
      
      // Re-render cart
      if(typeof renderCart === 'function') {
        renderCart();
      }
      
      alert(`✅ Order placed successfully!\n\nPayment: Cash on Delivery (COD)\n\nPlease prepare cash payment when your order is delivered.`);
      
      // Redirect to orders page
      setTimeout(() => {
        location.href = 'orders.html?t=' + Date.now();
      }, 300);
      return;
    }

    // Process payment for GCash
    let paymentResponse;
    let paymentData;
    
    try {
      paymentResponse = await fetch(`${API_BASE}/payment/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          payment_method: paymentMethod,
          amount: total,
          payment_details: paymentDetails
        })
      });
      
      if (!paymentResponse.ok) {
        const errorData = await paymentResponse.json().catch(() => ({ detail: 'Payment processing failed' }));
        throw new Error(errorData.detail || `Payment failed: ${paymentResponse.status}`);
      }
      
      paymentData = await paymentResponse.json();
    } catch (paymentError) {
      console.error('Payment processing error:', paymentError);
      alert(`⚠️ Payment Error: ${paymentError.message || 'Failed to process payment. Please try again.'}\n\nYour order has been created. You can complete the payment later.`);
      
      // Still redirect to orders page
      setTimeout(() => {
        location.href = 'orders.html?t=' + Date.now();
      }, 1000);
      return;
    }

    // Handle direct GCash transfer (show payment instructions)
    if(paymentResponse.ok && paymentData.payment_type === 'direct_gcash') {
      // Show payment modal with QR code and instructions
      showGCashPaymentModal(paymentData);
      return;
    }

    // Handle payment that requires action (GCash redirect)
    if(paymentResponse.ok && paymentData.requires_action && paymentData.redirect_url) {
      // Show message and redirect to GCash payment page
      if(confirm(`📱 Redirecting to GCash payment...\n\nYou will be redirected to complete your payment. After payment, you'll be redirected back.\n\nClick OK to proceed.`)) {
        window.location.href = paymentData.redirect_url;
      }
      return;
    }

    if(paymentResponse.ok && paymentData.success) {
      // Clear cart
      saveCart([]);
      
      // Clear form fields
      const delName = document.getElementById('delName');
      const delContact = document.getElementById('delContact');
      const delAddress = document.getElementById('delAddress');
      if(delName) delName.value = '';
      if(delContact) delContact.value = '';
      if(delAddress) delAddress.value = '';
      
      // Clear payment fields
      if (paymentMethod === 'gcash') {
        document.getElementById('gcashNumber').value = '';
      }
      
      // Re-render cart
      if(typeof renderCart === 'function') {
        renderCart();
      }
      
      // Show success message
      const paymentMethodName = 'GCash';
      const statusMessage = paymentData.status === 'pending' ? 
        'Payment request sent. Please confirm in your GCash app.' : 
        'Payment successful!';
      
      alert(`✅ ${statusMessage}\n\nOrder placed successfully!`);
      
      // Redirect to orders page
      setTimeout(() => {
        location.href = 'orders.html?t=' + Date.now();
      }, 300);
    } else {
      // Payment failed - order is created but payment pending
      const errorMsg = paymentData.message || paymentData.detail || 'Payment processing failed';
      alert(`⚠️ Payment Issue: ${errorMsg}\n\nYour order has been placed but payment is pending. Please complete the payment or contact support.`);
      
      // Still redirect to orders page
      setTimeout(() => {
        location.href = 'orders.html?t=' + Date.now();
      }, 500);
    }
  } catch(error) {
    console.error('Order placement error:', error);
    alert('Failed to place order. Please try again.');
  }
}

// Show GCash payment modal with beautiful UI and QR code support
function showGCashPaymentModal(paymentData) {
  // Create modal with smooth animation
  const modal = document.createElement('div');
  modal.id = 'gcashPaymentModal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.85);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    animation: fadeIn 0.3s ease-out;
  `;
  
  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: white;
    padding: 0;
    border-radius: 20px;
    max-width: 450px;
    width: 90%;
    max-height: 95vh;
    overflow-y: auto;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    animation: slideUp 0.4s ease-out;
  `;
  
  const adminNumber = paymentData.admin_gcash_number || '09947784922';
  const amount = paymentData.amount || 0;
  const reference = paymentData.reference || paymentData.payment_intent_id || '';
  
  // GCash QR code image URL (use provided URL or default)
  const qrCodeUrl = paymentData.qr_code_url || '/static/gcash-qr.png';
  
  modalContent.innerHTML = `
    <style>
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes slideUp {
        from { transform: translateY(30px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
      @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
      }
    </style>
    
    <!-- GCash Header -->
    <div style="background: linear-gradient(135deg, #0066cc 0%, #004499 100%); padding: 25px 30px; border-radius: 20px 20px 0 0; color: white; position: relative; overflow: hidden;">
      <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
      <div style="position: absolute; bottom: -30px; left: -30px; width: 150px; height: 150px; background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
      <div style="position: relative; z-index: 1;">
        <div style="font-size: 2.5rem; margin-bottom: 10px;">📱</div>
        <h2 style="margin: 0; font-size: 1.8rem; font-weight: bold;">GCash Payment</h2>
        <div style="font-size: 0.9rem; opacity: 0.95; margin-top: 5px;">Secure & Fast Payment</div>
      </div>
    </div>
    
    <div style="padding: 30px;">
      <!-- Payment Amount -->
      <div style="margin-bottom: 25px;">
        <div style="font-size: 0.85rem; color: #666; margin-bottom: 5px;">Amount to Pay</div>
        <div style="font-size: 2.5rem; font-weight: bold; color: #0066cc; letter-spacing: -1px;">₱${amount.toFixed(2)}</div>
      </div>
      
      <!-- GCash QR Code Section -->
      <div style="background: #f8f9fa; padding: 25px; border-radius: 16px; margin-bottom: 25px; border: 2px solid #e9ecef;">
        <div style="font-weight: bold; color: #333; margin-bottom: 15px; font-size: 1rem;">Scan QR Code to Pay</div>
        <div style="background: white; padding: 20px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
          <img id="gcashQRCode" src="${qrCodeUrl}" 
               onerror="this.style.display='none'; document.getElementById('qrFallback').style.display='block';"
               style="max-width: 250px; width: 100%; height: auto; border-radius: 8px;" 
               alt="GCash QR Code">
          <div id="qrFallback" style="display: none; padding: 40px; text-align: center; color: #999;">
            <div style="font-size: 2rem; margin-bottom: 10px;">📱</div>
            <div>QR Code will be displayed here</div>
            <div style="font-size: 0.85rem; margin-top: 5px; color: #666;">Use manual payment method below</div>
          </div>
        </div>
        <div style="font-size: 0.75rem; color: #999; margin-top: 12px;">Transfer fees may apply</div>
      </div>
      
      <!-- Admin GCash Number -->
      <div style="background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%); padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 2px solid #0066cc;">
        <div style="font-size: 0.85rem; color: #666; margin-bottom: 8px;">Send Payment To</div>
        <div style="font-size: 1.6rem; font-weight: bold; color: #0066cc; letter-spacing: 1px; margin-bottom: 5px; font-family: monospace;">${adminNumber}</div>
        <div style="font-size: 0.8rem; color: #666;">Or scan QR code above</div>
      </div>
    
      <!-- Reference Number -->
      <div style="background: #fff8e1; padding: 18px; border-radius: 12px; margin-bottom: 20px; border: 2px solid #ffc107;">
        <div style="font-weight: bold; color: #856404; margin-bottom: 10px; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; gap: 6px;">
          <span>🔑</span> Reference Number
        </div>
        <div style="font-size: 1.1em; color: #0066cc; font-weight: bold; font-family: 'Courier New', monospace; letter-spacing: 1px; padding: 12px; background: white; border-radius: 8px; border: 1px solid #e0e0e0; word-break: break-all;">${reference}</div>
        <button id="copyReferenceBtn" style="
          margin-top: 12px;
          background: #ffc107;
          color: #333;
          border: none;
          padding: 10px 24px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.9em;
          font-weight: bold;
          transition: all 0.3s;
          box-shadow: 0 2px 8px rgba(255,193,7,0.3);
        " onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 12px rgba(255,193,7,0.4)';" 
           onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 8px rgba(255,193,7,0.3)';">
          📋 Copy Reference
        </button>
      </div>
      
      <!-- Payment Instructions (Collapsible) -->
      <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: left;">
        <div style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 15px;" 
             onclick="const inst = document.getElementById('paymentInstructions'); inst.style.display = inst.style.display === 'none' ? 'block' : 'none';">
          <h3 style="margin: 0; color: #333; display: flex; align-items: center; gap: 8px; font-size: 1rem;">
            <span>📝</span> Payment Instructions
          </h3>
          <span id="instructionsToggle" style="font-size: 1.2rem; color: #0066cc;">▼</span>
        </div>
        <div id="paymentInstructions" style="display: block;">
          <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 12px;">
            <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
              <div style="background: #0066cc; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">1</div>
              <div style="flex: 1;">
                <strong>Scan QR Code</strong> or open <strong>GCash app</strong>
              </div>
            </div>
            <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
              <div style="background: #0066cc; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">2</div>
              <div style="flex: 1;">
                Tap <strong>"Send Money"</strong> or <strong>"Scan QR"</strong>
              </div>
            </div>
            <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
              <div style="background: #0066cc; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">3</div>
              <div style="flex: 1;">
                Enter amount: <strong style="color: #0066cc;">₱${amount.toFixed(2)}</strong>
              </div>
            </div>
            <div style="display: flex; align-items: start; gap: 12px;">
              <div style="background: #0066cc; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">4</div>
              <div style="flex: 1;">
                Add reference: <strong style="color: #0066cc; font-family: monospace;">${reference}</strong> in message
              </div>
            </div>
          </div>
          <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
            <div style="font-weight: bold; color: #856404; margin-bottom: 8px;">⚠️ Important:</div>
            <div style="font-size: 0.9rem; color: #856404; line-height: 1.6;">
              • Always include the reference number in your payment message<br>
              • This helps us verify your payment quickly<br>
              • Keep your payment receipt for reference
            </div>
          </div>
        </div>
      </div>
    
      <!-- Action Buttons -->
      <div style="margin-bottom: 15px;">
        <button id="openGCashBtn" style="
          background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
          color: white;
          border: none;
          padding: 16px 32px;
          border-radius: 12px;
          cursor: pointer;
          font-size: 1.1em;
          font-weight: bold;
          width: 100%;
          box-shadow: 0 4px 16px rgba(0,102,204,0.4);
          transition: all 0.3s;
          position: relative;
          overflow: hidden;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(0,102,204,0.5)';" 
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 16px rgba(0,102,204,0.4)';"
           onmousedown="this.style.transform='translateY(0)';"
           onmouseup="this.style.transform='translateY(-2px)';">
          <span style="position: relative; z-index: 1;">📱 Open GCash App</span>
        </button>
        <div style="font-size: 0.8rem; color: #999; margin-top: 8px; text-align: center;">
          Tap to open GCash app directly
        </div>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px;">
        <button id="copyNumberBtn" style="
          background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
          color: white;
          border: none;
          padding: 14px 20px;
          border-radius: 10px;
          cursor: pointer;
          font-size: 0.95em;
          font-weight: bold;
          box-shadow: 0 3px 12px rgba(40,167,69,0.3);
          transition: all 0.3s;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 16px rgba(40,167,69,0.4)';" 
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 3px 12px rgba(40,167,69,0.3)';">
          📋 Copy Number
        </button>
        <button id="confirmPaymentBtn" style="
          background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
          color: white;
          border: none;
          padding: 14px 20px;
          border-radius: 10px;
          cursor: pointer;
          font-size: 0.95em;
          font-weight: bold;
          box-shadow: 0 3px 12px rgba(0,102,204,0.3);
          transition: all 0.3s;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 16px rgba(0,102,204,0.4)';" 
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 3px 12px rgba(0,102,204,0.3)';">
          ✅ Payment Sent
        </button>
      </div>
      
      <button id="cancelPaymentBtn" style="
        background: transparent;
        color: #666;
        border: 2px solid #ddd;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.9em;
        width: 100%;
        transition: all 0.3s;
      " onmouseover="this.style.borderColor='#999'; this.style.color='#333';" 
         onmouseout="this.style.borderColor='#ddd'; this.style.color='#666';">
        Cancel
      </button>
    </div>
  `;
  
  modal.appendChild(modalContent);
  document.body.appendChild(modal);
  
  // Function to open GCash app - improved version
  function openGCashApp() {
    const adminNumber = paymentData.admin_gcash_number || '09947784922';
    const amount = paymentData.amount || 0;
    const reference = paymentData.reference || paymentData.payment_intent_id || '';
    
    // Detect device type
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    
    // Show loading state
    const btn = document.getElementById('openGCashBtn');
    if (btn) {
      const originalText = btn.textContent;
      btn.textContent = '⏳ Opening GCash...';
      btn.style.opacity = '0.7';
      btn.disabled = true;
    }
    
    if (isMobile) {
      // Mobile device - try to open GCash app directly
      let opened = false;
      
      // Method 1: Try Android Intent URL (for Android)
      if (isAndroid) {
        try {
          // Android Intent format - opens GCash app
          const intentUrl = `intent://#Intent;scheme=gcash;package=com.globe.gcash.android;end`;
          window.location.href = intentUrl;
          opened = true;
        } catch(e) {
          console.log('Intent URL failed, trying direct link');
        }
      }
      
      // Method 2: Try direct GCash deep link (works for both iOS and Android)
      if (!opened) {
        try {
          // Try opening GCash app directly
          window.location.href = 'gcash://';
          opened = true;
        } catch(e) {
          console.log('GCash deep link failed');
        }
      }
      
      // Method 3: Fallback - Open Play Store/App Store
      if (!opened) {
        setTimeout(() => {
          if (isAndroid) {
            window.open('https://play.google.com/store/apps/details?id=com.globe.gcash.android', '_blank');
          } else if (isIOS) {
            window.open('https://apps.apple.com/app/gcash/id1322865881', '_blank');
          }
        }, 2000);
      }
      
      // Show instructions after opening app
      setTimeout(() => {
        // Create instruction overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.85);
          z-index: 10001;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 20px;
        `;
        
        overlay.innerHTML = `
          <div style="background: white; padding: 25px; border-radius: 12px; max-width: 400px; width: 100%; text-align: center;">
            <h3 style="margin-top: 0; color: #0066cc;">📱 GCash Payment Steps</h3>
            <div style="text-align: left; margin: 20px 0; line-height: 1.8;">
              <div style="margin-bottom: 12px;"><strong>1.</strong> Tap <strong>"Send Money"</strong> in GCash</div>
              <div style="margin-bottom: 12px;"><strong>2.</strong> Enter number: <strong style="color: #0066cc;">${adminNumber}</strong></div>
              <div style="margin-bottom: 12px;"><strong>3.</strong> Enter amount: <strong style="color: #0066cc;">₱${amount.toFixed(2)}</strong></div>
              <div style="margin-bottom: 12px;"><strong>4.</strong> Add reference: <strong style="color: #0066cc; font-family: monospace;">${reference}</strong></div>
              <div><strong>5.</strong> Complete the payment</div>
            </div>
            <button onclick="this.closest('div[style*=\"position: fixed\"]').remove(); document.getElementById('openGCashBtn').textContent='${originalText}'; document.getElementById('openGCashBtn').style.opacity='1';" 
                    style="background: #0066cc; color: white; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 10px;">
              Got it!
            </button>
          </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Auto-close after 30 seconds
        setTimeout(() => {
          if (overlay.parentElement) {
            overlay.remove();
            btn.textContent = originalText;
            btn.style.opacity = '1';
          }
        }, 30000);
      }, 500);
      
    } else {
      // Desktop - show instructions
      btn.textContent = originalText;
      btn.style.opacity = '1';
      alert(`📱 Please open GCash app on your phone\n\nSend Payment:\n• Number: ${adminNumber}\n• Amount: ₱${amount.toFixed(2)}\n• Reference: ${reference}`);
    }
  }
  
  // Make openGCashApp function available globally and attach to button
  window.openGCashAppFunc = openGCashApp;
  
  // Attach event listener to button
  const openGCashBtn = document.getElementById('openGCashBtn');
  if (openGCashBtn) {
    openGCashBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      openGCashApp();
      return false;
    };
  }
  
  // Copy GCash number
  document.getElementById('copyNumberBtn').onclick = () => {
    navigator.clipboard.writeText(adminNumber).then(() => {
      const btn = document.getElementById('copyNumberBtn');
      const originalText = btn.textContent;
      btn.textContent = '✅ Copied!';
      btn.style.background = '#28a745';
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '#28a745';
      }, 2000);
    }).catch(() => {
      alert(`GCash Number: ${adminNumber}\n\nPlease copy this number manually.`);
    });
  };
  
  // Copy reference number
  document.getElementById('copyReferenceBtn').onclick = () => {
    navigator.clipboard.writeText(reference).then(() => {
      const btn = document.getElementById('copyReferenceBtn');
      const originalText = btn.textContent;
      btn.textContent = '✅ Copied!';
      setTimeout(() => {
        btn.textContent = originalText;
      }, 2000);
    }).catch(() => {
      alert(`Reference: ${reference}\n\nPlease copy this reference manually.`);
    });
  };
  
  // Handle confirm payment
  document.getElementById('confirmPaymentBtn').onclick = () => {
    // Clear cart
    saveCart([]);
    
    // Clear form fields
    const delName = document.getElementById('delName');
    const delContact = document.getElementById('delContact');
    const delAddress = document.getElementById('delAddress');
    if(delName) delName.value = '';
    if(delContact) delContact.value = '';
    if(delAddress) delAddress.value = '';
    if(document.getElementById('gcashNumber')) {
      document.getElementById('gcashNumber').value = '';
    }
    
    // Re-render cart
    if(typeof renderCart === 'function') {
      renderCart();
    }
    
    // Remove modal
    document.body.removeChild(modal);
    
    alert(`✅ Payment instructions received!\n\nYour order has been placed. Please send ₱${amount.toFixed(2)} to ${adminNumber} with reference ${reference}.\n\nAdmin will verify your payment and update your order status.`);
    
    // Redirect to orders page
    setTimeout(() => {
      location.href = 'orders.html?t=' + Date.now();
    }, 300);
  };
  
  // Handle cancel
  document.getElementById('cancelPaymentBtn').onclick = () => {
    document.body.removeChild(modal);
  };
  
  // Close on outside click
  modal.onclick = (e) => {
    if(e.target === modal) {
      document.body.removeChild(modal);
    }
  };
}

/* ---------- User Orders (API) ---------- */
// Store user orders globally for sequential numbering
let userAllOrders = [];

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
    
    // Filter orders for current user and update global
    const mine = allOrders
      .filter(o => o.user_id === cur.id)
      .reverse();
    
    // Update global orders list
    userAllOrders = mine;

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

// Calculate sequential order numbers for user (only active orders)
function getUserOrderNumberMap() {
  // Get all active orders (not delivered), sorted by creation time (oldest first)
  const activeOrders = userAllOrders
    .filter(o => o.status !== 'Delivered')
    .sort((a, b) => {
      const dateA = new Date(a.created_at || 0);
      const dateB = new Date(b.created_at || 0);
      return dateA - dateB; // Oldest first
    });
  
  // Create a map: orderId -> sequential number
  const orderNumberMap = {};
  activeOrders.forEach((order, index) => {
    orderNumberMap[order.id] = index + 1; // Start from 1
  });
  
  return orderNumberMap;
}

function orderCardHtmlForUser(o){
  // Get sequential order number (only for active orders)
  const orderNumberMap = getUserOrderNumberMap();
  const sequentialNumber = orderNumberMap[o.id];
  const displayOrderNumber = sequentialNumber ? sequentialNumber : o.id;
  const orderNumberLabel = sequentialNumber ? `Order #${sequentialNumber}` : `Order #${o.id} (Completed)`;
  
  // Get payment information
  const paymentMethod = o.payment_method || 'cash';
  const paymentStatus = o.payment_status || 'pending';
  const paymentMethodIcon = paymentMethod === 'cod' ? '💵' : paymentMethod === 'gcash' ? '📱' : '💵';
  const paymentMethodName = paymentMethod === 'cod' ? 'Cash on Delivery' : paymentMethod === 'gcash' ? 'GCash' : 'Cash';
  const paymentStatusBadge = paymentStatus === 'paid' ? 
    '<span style="background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px;">✅ Paid</span>' :
    paymentStatus === 'failed' ?
    '<span style="background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px;">❌ Failed</span>' :
    '<span style="background: #d7a24e; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px;">⏳ Pending</span>';
  
  const statusBadge = statusBadgeHtml(o.status);
  const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
  const itemsText = items.map(i => `${i.name} ×${i.qty}`).join('<br>');
  const canCancel = o.status === 'Pending';
  
  return `
    <div class="order-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <strong>${orderNumberLabel}</strong>
          <div class="muted small">${new Date(o.created_at).toLocaleString()}</div>
          <div style="margin-top: 4px; font-size: 0.85rem; color: #666;">
            ${paymentMethodIcon} ${paymentMethodName} ${paymentStatusBadge}
          </div>
        </div>
        <div>${statusBadge}</div>
      </div>
      <div style="margin-top:8px">${itemsText}</div>
      <div class="muted small" style="margin-top:8px">Delivery: ${o.fullname} • ${o.contact} • ${o.location}</div>
      <div style="margin-top:12px;display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;">
        <div><strong>Total:</strong> ₱${Number(o.total).toFixed(2)}</div>
        ${canCancel ? `
        <div style="display:flex;gap:8px;align-items:center;">
          <button class="btn small" onclick="editUserOrder(${o.id})" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500;">✏️ Edit</button>
          <button class="btn delete small" onclick="cancelUserOrder(${o.id})" style="padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500;">❌ Cancel</button>
        </div>
        ` : ''}
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

/* ---------- Edit User Order ---------- */
async function editUserOrder(orderId) {
  const cur = getCurrent();
  if (!cur) {
    alert('Please login first');
    location.href = 'index.html';
    return;
  }

  // Fetch all orders to find this one
  try {
    const response = await fetch(`/orders?t=${Date.now()}`);
    const allOrders = await response.json();
    const order = allOrders.find(o => o.id === orderId && o.user_id === cur.id);
    
    if (!order) {
      alert('Order not found or you do not have permission to edit this order.');
      return;
    }

    if (order.status !== 'Pending') {
      alert('Only orders with "Pending" status can be edited.');
      return;
    }

    // Parse items if it's a string
    const items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
    
    // Create edit modal
    const modal = document.createElement('div');
    modal.id = 'editUserOrderModal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.7);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      overflow-y: auto;
    `;
    
    modal.innerHTML = `
      <div style="background: white; border-radius: 12px; padding: 24px; max-width: 600px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative;">
        <button onclick="document.getElementById('editUserOrderModal').remove()" 
                style="position: absolute; top: 12px; right: 12px; background: #f44336; color: white; border: none; border-radius: 50%; width: 32px; height: 32px; cursor: pointer; font-size: 18px; font-weight: bold;">×</button>
        
        <h2 style="margin: 0 0 20px 0; color: #8b4513;">✏️ Edit Order #${orderId}</h2>
        
        <form id="editUserOrderForm" onsubmit="saveUserOrderEdit(event, ${orderId})">
          <div style="margin-bottom: 16px;">
            <label class="input-label">Full Name (First Middle Last)</label>
            <input type="text" id="editUserFullname" value="${(order.fullname || order.name || '').replace(/"/g, '&quot;')}" 
                   placeholder="First Name Middle Name Last Name"
                   required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
          </div>
          
          <div style="margin-bottom: 16px;">
            <label class="input-label">Contact Number (11 digits)</label>
            <input type="tel" id="editUserContact" value="${(order.contact || order.number || '').replace(/"/g, '&quot;')}" 
                   placeholder="09XXXXXXXXX" maxlength="11" pattern="[0-9]{11}"
                   oninput="this.value = this.value.replace(/\D/g, '').slice(0, 11)"
                   required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
          </div>
          
          <div style="margin-bottom: 16px;">
            <label class="input-label">Address / Location</label>
            <textarea id="editUserLocation" required 
                      style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-height: 80px;">${(order.location || order.address || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
          </div>
          
          <div style="margin-bottom: 16px;">
            <label class="input-label">Order Items</label>
            <div id="editUserItemsList" style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #f9f9f9;">
              ${items.map((item, idx) => {
                const safeName = (item.name || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                return `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 8px; background: white; border-radius: 6px;">
                  <div style="flex: 1;">
                    <strong>${safeName}</strong><br>
                    <span style="color: var(--muted); font-size: 0.9rem;">₱${Number(item.price).toFixed(2)} × 
                    <input type="number" id="editUserQty_${idx}" value="${item.qty}" min="1" 
                           style="width: 60px; padding: 4px; border: 1px solid #ddd; border-radius: 4px; text-align: center;"
                           onchange="updateUserEditTotal()">
                    </span>
                  </div>
                  <button type="button" class="btn delete small" onclick="removeUserEditItem(${idx})">Remove</button>
                </div>
              `;
              }).join('')}
            </div>
            <div style="margin-top: 12px;">
              <button type="button" class="btn small ghost" onclick="addUserEditItem()">+ Add Item</button>
            </div>
          </div>
          
          <div style="margin-bottom: 20px; padding: 12px; background: #fff8f1; border-radius: 8px; border: 1px solid #8b4513;">
            <strong>💰 Total: ₱<span id="editUserTotal">${Number(order.total).toFixed(2)}</span></strong>
          </div>
          
          <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button type="button" class="btn ghost" onclick="document.getElementById('editUserOrderModal').remove()">Cancel</button>
            <button type="submit" class="btn">💾 Save Changes</button>
          </div>
        </form>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Store original items for calculations
    window.editUserOrderData = {
      items: items.map(item => ({...item})),
      orderId: orderId
    };
    
    // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  } catch(error) {
    console.error('Error loading order:', error);
    alert('Failed to load order. Please try again.');
  }
}

async function saveUserOrderEdit(event, orderId) {
  event.preventDefault();
  
  const cur = getCurrent();
  if (!cur) {
    alert('Please login first');
    return;
  }
  
  const fullname = document.getElementById('editUserFullname').value.trim();
  const contact = document.getElementById('editUserContact').value.trim();
  const location = document.getElementById('editUserLocation').value.trim();
  
  if (!fullname || !contact || !location) {
    alert('Please fill in all required fields.');
    return;
  }
  
  // Validate full name: must have at least 3 words (First, Middle, Last)
  const nameWords = fullname.split(/\s+/).filter(word => word.length > 0);
  if(nameWords.length < 3) {
    alert('Please enter full name: First Name, Middle Name, and Last Name (at least 3 words).');
    document.getElementById('editUserFullname').focus();
    return;
  }
  
  // Validate contact number: must be exactly 11 digits
  const contactDigits = contact.replace(/\D/g, ''); // Remove non-digits
  if(contactDigits.length !== 11) {
    alert('Contact number must be exactly 11 digits (e.g., 09123456789).');
    document.getElementById('editUserContact').focus();
    return;
  }
  
  // Collect items with quantities
  const items = [];
  let total = 0;
  const DELIVERY_FEE = 10;
  
  for (let i = 0; i < window.editUserOrderData.items.length; i++) {
    const qtyInput = document.getElementById(`editUserQty_${i}`);
    if (qtyInput && qtyInput.parentElement.parentElement.parentElement) {
      const qty = parseInt(qtyInput.value) || 0;
      if (qty > 0) {
        const item = window.editUserOrderData.items[i];
        items.push({
          id: item.id,
          name: item.name,
          price: Number(item.price),
          qty: qty
        });
        total += Number(item.price) * qty;
      }
    }
  }
  
  if (items.length === 0) {
    alert('Order must have at least one item.');
    return;
  }
  
  total += DELIVERY_FEE;
  
  try {
    const response = await fetch(`/orders/${orderId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: cur.id,
        fullname: fullname.trim(),
        contact: contactDigits, // Use validated digits-only contact
        location: location.trim(),
        items: items,
        total: total
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      alert(`Failed to update order: ${errorData.detail || 'Unknown error'}`);
      return;
    }
    
    alert('✅ Order updated successfully!');
    document.getElementById('editUserOrderModal').remove();
    await renderUserOrders();
  } catch(error) {
    console.error('Error updating order:', error);
    alert('Failed to update order. Please try again.');
  }
}

function updateUserEditTotal() {
  const DELIVERY_FEE = 10;
  let total = 0;
  
  for (let i = 0; i < window.editUserOrderData.items.length; i++) {
    const qtyInput = document.getElementById(`editUserQty_${i}`);
    if (qtyInput && qtyInput.parentElement.parentElement.parentElement) {
      const qty = parseInt(qtyInput.value) || 0;
      const item = window.editUserOrderData.items[i];
      total += Number(item.price) * qty;
    }
  }
  
  total += DELIVERY_FEE;
  document.getElementById('editUserTotal').textContent = total.toFixed(2);
}

function removeUserEditItem(idx) {
  window.editUserOrderData.items.splice(idx, 1);
  document.getElementById('editUserOrderModal').remove();
  editUserOrder(window.editUserOrderData.orderId);
}

async function addUserEditItem() {
  // Fetch menu items
  try {
    const response = await fetch('/menu');
    const menuItems = await response.json();
    
    if (menuItems.length === 0) {
      alert('No menu items available.');
      return;
    }
    
    // Create a simple selection dialog
    const itemNames = menuItems.map(item => item.name).join('\n');
    const selectedName = prompt(`Enter item name to add:\n\nAvailable items:\n${itemNames}`);
    if (!selectedName) return;
    
    const selectedItem = menuItems.find(item => 
      item.name.toLowerCase() === selectedName.toLowerCase()
    );
    
    if (!selectedItem) {
      alert('Item not found. Please enter the exact item name.');
      return;
    }
    
    if (selectedItem.is_available === false || (selectedItem.quantity || 0) === 0) {
      alert('This item is currently out of stock.');
      return;
    }
    
    const qty = parseInt(prompt(`Enter quantity for ${selectedItem.name}:`, '1')) || 1;
    if (qty <= 0) {
      alert('Quantity must be greater than 0.');
      return;
    }
    
    // Check stock availability
    if (qty > (selectedItem.quantity || 0)) {
      alert(`Only ${selectedItem.quantity} item(s) available in stock.`);
      return;
    }
    
    window.editUserOrderData.items.push({
      id: selectedItem.id,
      name: selectedItem.name,
      price: selectedItem.price,
      qty: qty
    });
    
    // Refresh the modal
    document.getElementById('editUserOrderModal').remove();
    editUserOrder(window.editUserOrderData.orderId);
  } catch(error) {
    console.error('Error adding item:', error);
    alert('Failed to load menu items.');
  }
}

/* ---------- Cancel User Order ---------- */
async function cancelUserOrder(orderId) {
  const cur = getCurrent();
  if (!cur) {
    alert('Please login first');
    location.href = 'index.html';
    return;
  }

  if (!confirm(`⚠️ Are you sure you want to cancel Order #${orderId}?\n\nThis action cannot be undone and your items will be restocked.`)) {
    return;
  }

  try {
    const response = await fetch(`/orders/${orderId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: cur.id })
    });

    // Read response
    let responseData = null;
    try {
      const responseText = await response.text();
      if (responseText) {
        responseData = JSON.parse(responseText);
      }
    } catch(parseError) {
      console.log('Response parse note:', parseError);
    }

    if (!response.ok) {
      // Handle error response
      const errorMessage = responseData?.detail || `Server returned ${response.status}: ${response.statusText}`;
      alert(`Failed to cancel order: ${errorMessage}`);
      return;
    }

    // Success - show message and refresh
    alert('✅ Order cancelled successfully! Stock has been restored.');
    
    // Refresh orders list
    try {
      await renderUserOrders();
    } catch(refreshError) {
      console.error('Error refreshing orders after cancel:', refreshError);
    }
  } catch(error) {
    console.error('Error cancelling order:', error);
    alert('Failed to cancel order. Please check your connection and try again.');
  }
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

