# 🧪 Testing Guide - RMLCanteen Database Integration

## ✅ **Database Connection Status: COMPLETE**

Your RMLCanteen application is now **fully connected** to NeonDB PostgreSQL!

---

## 🎯 **What's Been Connected:**

### ✅ **Authentication (100% Database)**
- ✅ Login - Uses `/login` API endpoint
- ✅ Register - Uses `/register` API endpoint
- ✅ User data stored in PostgreSQL `users` table

### ✅ **Orders (100% Database)**
- ✅ Place Order - Uses `/orders` POST endpoint
- ✅ View Orders - Uses `/orders` GET endpoint
- ✅ Update Status - Uses `/orders/{id}` PUT endpoint
- ✅ All order data stored in PostgreSQL `orders` table

### ⚠️ **Menu Management (Still LocalStorage)**
- ℹ️ Menu items (hardcoded in frontend)
- ℹ️ Sold-out status (localStorage - can be moved to DB later)

---

## 🧪 **How to Test:**

### **Step 1: Start the Server**

```bash
# Option 1: Double-click START_SERVER.bat

# Option 2: Manual
python -m uvicorn server:app --reload
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

---

### **Step 2: Test User Registration**

1. **Open**: http://localhost:8000/register.html
2. **Register a new user**:
   - Name: `Test Customer`
   - Email: `customer@test.com`
   - Password: `test123`
3. **Click Register**
4. **Expected Result**: ✅ "Account created successfully!"
5. **Verify**: Check NeonDB - user should be in `users` table

---

### **Step 3: Test Login**

1. **Open**: http://localhost:8000/index.html
2. **Login with**:
   - Email: `customer@test.com`
   - Password: `test123`
3. **Expected Result**: Redirects to `order.html`

---

### **Step 4: Test Order Placement**

1. **From order.html** (logged in as customer)
2. **Add items to cart**:
   - Click on any menu item
   - Set quantity
   - Click "Add"
3. **Fill delivery details**:
   - Full Name: `Juan Dela Cruz`
   - Contact: `09123456789`
   - Address: `123 Main St, Manila`
4. **Click "Confirm Order"**
5. **Expected Result**: ✅ "Order placed successfully!"
6. **Verify**: Check NeonDB - order should be in `orders` table

---

### **Step 5: Test Admin Dashboard**

1. **Logout** (if logged in as customer)
2. **Login as Admin**:
   - Email: `admin@canteen`
   - Password: `admin123`
3. **Expected Result**: Redirects to `admin.html`
4. **Verify Dashboard Shows**:
   - ✅ Statistics (Total Orders, Pending, etc.)
   - ✅ Your test order appears
   - ✅ Order details are correct

---

### **Step 6: Test Order Status Update**

1. **From admin.html**
2. **Find your test order**
3. **Change status dropdown** to "Preparing"
4. **Expected Result**: ✅ "Order status updated!"
5. **Verify**: 
   - Check NeonDB - status should be updated
   - Customer should see new status in `orders.html`

---

### **Step 7: Test Customer Order View**

1. **Logout from admin**
2. **Login as customer** (`customer@test.com` / `test123`)
3. **Go to**: http://localhost:8000/orders.html
4. **Expected Result**: 
   - ✅ See your order
   - ✅ Status shows "Preparing"
   - ✅ All order details correct

---

## 🔍 **Verify in NeonDB:**

### **Check Users Table:**
```sql
SELECT * FROM users;
```
Expected: Your new user `customer@test.com` appears

### **Check Orders Table:**
```sql
SELECT * FROM orders ORDER BY id DESC LIMIT 5;
```
Expected: Your test order appears with all details

### **Check Order Items (JSONB):**
```sql
SELECT id, fullname, items, status FROM orders;
```
Expected: Items are stored as JSON

---

## ⚡ **Quick Test Checklist:**

- [ ] Server starts without errors
- [ ] Can register new user
- [ ] User saved to database
- [ ] Can login with new user
- [ ] Can place order
- [ ] Order saved to database
- [ ] Admin can see all orders
- [ ] Admin can update order status
- [ ] Status updates in database
- [ ] Customer sees updated status
- [ ] Print order works
- [ ] Search/filter orders works

---

## 🐛 **Common Issues & Solutions:**

### **Issue 1: "Failed to load orders"**
**Solution**: Check if server is running on port 8000

### **Issue 2: "Registration failed"**
**Solution**: Check NeonDB connection string in `server.py`

### **Issue 3: "CORS error"**
**Solution**: Already handled - CORS is enabled in `server.py`

### **Issue 4: Database connection error**
**Solution**: 
1. Check internet connection
2. Verify NeonDB connection string
3. Ensure NeonDB database is active

---

## 📊 **Database Tables Used:**

### `users`
- Stores: User accounts (customers & admin)
- Used for: Login, Registration

### `orders`
- Stores: All customer orders
- Used for: Order placement, tracking, admin management

### `soldout_items`
- Available but not currently used
- Can be integrated later for sold-out tracking

---

## 🎉 **Success Indicators:**

You'll know everything is working when:

1. ✅ New users can register and login
2. ✅ Customers can place orders
3. ✅ Orders appear in admin dashboard
4. ✅ Admin can update order status
5. ✅ Status updates show in real-time
6. ✅ Data persists after closing browser
7. ✅ Data accessible from different devices

---

## 📝 **Next Steps (Optional Enhancements):**

1. **Move sold-out items to database**
2. **Add DELETE order endpoint**
3. **Add user profile update endpoint**
4. **Add order cancellation**
5. **Add email notifications**
6. **Add payment integration**

---

**Your system is now production-ready with persistent database storage hahahahha!** 🚀

