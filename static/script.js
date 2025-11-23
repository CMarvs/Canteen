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

    const data = await response.json();
    
    if(response.ok) {
      // Check if user is approved
      if(data.is_approved === false || data.is_approved === 0) {
        alert('⏳ Your account is pending admin approval. Please wait for approval before logging in.');
        return;
      }
      
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

async function promptEditQty(id, currentQty){
  const val = prompt('Enter new quantity:', currentQty);
  if(val === null) return;
  const n = Number(val);
  if(isNaN(n) || n <= 0) return alert('Invalid quantity');
  await updateCartQty(id, n);
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
  if (paymentMethod === 'card') {
    paymentDetails = {
      cardNumber: document.getElementById('cardNumber').value.replace(/\s/g, ''),
      cardExpiry: document.getElementById('cardExpiry').value,
      cardCVV: document.getElementById('cardCVV').value,
      cardName: document.getElementById('cardName').value.trim()
    };
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

    // Process payment
    const paymentResponse = await fetch(`${API_BASE}/payment/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: orderId,
        payment_method: paymentMethod,
        amount: total,
        payment_details: paymentDetails
      })
    });

    const paymentData = await paymentResponse.json();

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
      if (paymentMethod === 'card') {
        document.getElementById('cardNumber').value = '';
        document.getElementById('cardExpiry').value = '';
        document.getElementById('cardCVV').value = '';
        document.getElementById('cardName').value = '';
      } else {
        document.getElementById('gcashNumber').value = '';
      }
      
      // Re-render cart
      if(typeof renderCart === 'function') {
        renderCart();
      }
      
      // Show success message
      const paymentMethodName = paymentMethod === 'card' ? 'Card' : 'GCash';
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

// Show GCash payment modal with instructions (no QR code - GCash doesn't support generic QR)
function showGCashPaymentModal(paymentData) {
  // Create modal
  const modal = document.createElement('div');
  modal.id = 'gcashPaymentModal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;
  
  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: white;
    padding: 30px;
    border-radius: 12px;
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    text-align: center;
  `;
  
  const adminNumber = paymentData.admin_gcash_number || '09947784922';
  const amount = paymentData.amount || 0;
  const reference = paymentData.reference || paymentData.payment_intent_id || '';
  
  modalContent.innerHTML = `
    <h2 style="margin-top: 0; color: #0066cc;">📱 GCash Payment</h2>
    
    <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #0066cc 0%, #004499 100%); border-radius: 12px; color: white;">
      <div style="font-size: 0.9em; margin-bottom: 8px; opacity: 0.9;">Send Payment To</div>
      <div style="font-size: 1.8em; font-weight: bold; margin-bottom: 8px; letter-spacing: 2px;">${adminNumber}</div>
      <div style="font-size: 0.9em; opacity: 0.9;">Amount: <strong style="font-size: 1.2em;">₱${amount.toFixed(2)}</strong></div>
    </div>
    
    <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 2px dashed #0066cc;">
      <div style="font-weight: bold; color: #333; margin-bottom: 10px;">Reference Number:</div>
      <div style="font-size: 1.1em; color: #0066cc; font-weight: bold; font-family: monospace; letter-spacing: 1px; padding: 10px; background: white; border-radius: 6px;">${reference}</div>
      <button id="copyReferenceBtn" style="
        margin-top: 10px;
        background: #0066cc;
        color: white;
        border: none;
        padding: 8px 20px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9em;
      ">📋 Copy Reference</button>
    </div>
    
    <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
      <h3 style="margin-top: 0; color: #333; display: flex; align-items: center; gap: 8px;">
        <span>📝</span> Payment Instructions:
      </h3>
      <ol style="line-height: 2; color: #555; padding-left: 20px;">
        <li>Open your <strong>GCash app</strong> on your phone</li>
        <li>Tap <strong>"Send Money"</strong></li>
        <li>Enter or paste GCash number: <strong style="color: #0066cc;">${adminNumber}</strong></li>
        <li>Enter amount: <strong style="color: #0066cc;">₱${amount.toFixed(2)}</strong></li>
        <li>In the message/notes field, add: <strong style="color: #0066cc;">${reference}</strong></li>
        <li>Review and confirm the payment</li>
      </ol>
      <div style="background: #fff3cd; padding: 15px; border-radius: 6px; margin-top: 15px; border-left: 4px solid #ffc107;">
        <strong>⚠️ Important:</strong><br>
        • Include the reference number <strong>${reference}</strong> in your payment message<br>
        • This helps us verify your payment quickly<br>
        • Keep your payment receipt for reference
      </div>
    </div>
    
    <div style="margin: 20px 0;">
      <button id="openGCashBtn" style="
        background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
        color: white;
        border: none;
        padding: 16px 32px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 1.1em;
        font-weight: bold;
        width: 100%;
        box-shadow: 0 4px 12px rgba(0,102,204,0.3);
        transition: transform 0.2s, box-shadow 0.2s;
      " onmouseover="this.style.transform='scale(1.02)'; this.style.boxShadow='0 6px 16px rgba(0,102,204,0.4)';" 
         onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,102,204,0.3)';">
        📱 Open GCash App
      </button>
      <div style="font-size: 0.85em; color: #666; margin-top: 8px; text-align: center;">
        Tap to open GCash app directly
      </div>
    </div>
    
    <div style="display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap;">
      <button id="copyNumberBtn" style="
        background: #28a745;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.95em;
        font-weight: bold;
        flex: 1;
        min-width: 150px;
      ">📋 Copy Number</button>
      <button id="confirmPaymentBtn" style="
        background: #0066cc;
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 1em;
        font-weight: bold;
        flex: 1;
        min-width: 150px;
      ">✅ I've Sent the Payment</button>
    </div>
    <div style="margin-top: 10px;">
      <button id="cancelPaymentBtn" style="
        background: #6c757d;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9em;
      ">Cancel</button>
    </div>
  `;
  
  modal.appendChild(modalContent);
  document.body.appendChild(modal);
  
  // Function to open GCash app
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
    const originalText = btn.textContent;
    btn.textContent = '⏳ Opening GCash...';
    btn.style.opacity = '0.7';
    
    if (isMobile) {
      // Mobile device - try to open GCash app
      
      // Method 1: Try Android Intent URL (for Android)
      if (isAndroid) {
        try {
          // Android Intent format - opens GCash app
          const intentUrl = `intent://#Intent;scheme=gcash;package=com.globe.gcash.android;end`;
          window.location.href = intentUrl;
        } catch(e) {
          // Fallback to direct link
          window.location.href = 'gcash://';
        }
      } else if (isIOS) {
        // iOS: Try GCash URL scheme
        try {
          window.location.href = 'gcash://';
        } catch(e) {
          // Fallback to App Store
          window.open('https://apps.apple.com/app/gcash/id1322865881', '_blank');
        }
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
  
  // Open GCash app button
  document.getElementById('openGCashBtn').onclick = openGCashApp;
  
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
  // Get payment information
  const paymentMethod = o.payment_method || 'cash';
  const paymentStatus = o.payment_status || 'pending';
  const paymentMethodIcon = paymentMethod === 'card' ? '💳' : paymentMethod === 'gcash' ? '📱' : '💵';
  const paymentMethodName = paymentMethod === 'card' ? 'Card' : paymentMethod === 'gcash' ? 'GCash' : 'Cash';
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
          <strong>Order #${o.id}</strong>
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

