# 💳 Payment Integration Guide

## ✅ Payment System Implemented

Your canteen application now supports **Card** and **GCash** payment methods!

---

## 🎯 Features Added

### 1. **Payment Method Selection**
- ✅ Credit/Debit Card option
- ✅ GCash mobile wallet option
- ✅ Dynamic form fields based on selection
- ✅ Input validation for payment details

### 2. **Payment Processing**
- ✅ Payment processing endpoint (`/payment/process`)
- ✅ Payment status tracking (pending, paid, failed)
- ✅ Automatic database column creation
- ✅ Order creation with payment information

### 3. **Payment Status Display**
- ✅ Payment method shown in admin dashboard
- ✅ Payment status badges (Paid, Pending, Failed)
- ✅ Payment information in user order history
- ✅ Visual indicators for payment status

---

## 📋 How It Works

### **User Flow:**
1. User adds items to cart
2. Fills delivery details
3. **Selects payment method** (Card or GCash)
4. **Enters payment details**:
   - Card: Card number, expiry, CVV, cardholder name
   - GCash: Mobile number
5. Clicks "Proceed to Payment"
6. Payment is processed
7. Order is created with payment status
8. User sees payment confirmation

### **Payment Processing:**
1. Order is created first (with `payment_status: 'pending'`)
2. Payment is processed via `/payment/process` endpoint
3. Payment status is updated to `'paid'` or `'failed'`
4. User receives confirmation

---

## 🔧 Database Schema

The system automatically adds these columns to the `orders` table:

```sql
payment_method TEXT DEFAULT 'cash'  -- 'card', 'gcash', or 'cash'
payment_status TEXT DEFAULT 'pending'  -- 'pending', 'paid', or 'failed'
```

---

## 🔌 Integrating Real Payment Gateways

### **For Card Payments (Stripe Example):**

1. **Install Stripe:**
   ```bash
   pip install stripe
   ```

2. **Update `server.py` payment processing:**
   ```python
   import stripe
   stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
   
   # In process_payment function:
   if payment_method == "card":
       try:
           # Create payment intent
           intent = stripe.PaymentIntent.create(
               amount=int(amount * 100),  # Convert to cents
               currency='php',
               payment_method_data={
                   'type': 'card',
                   'card': {
                       'number': card_number,
                       'exp_month': card_expiry.split('/')[0],
                       'exp_year': '20' + card_expiry.split('/')[1],
                       'cvc': card_cvv,
                   }
               },
               confirm=True
           )
           payment_success = intent.status == 'succeeded'
       except stripe.error.CardError as e:
           payment_success = False
           payment_message = str(e)
   ```

3. **Add Stripe keys to environment:**
   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

### **For GCash Payments:**

GCash offers several integration options:

1. **GCash API** (requires business account)
2. **Payment Gateway** (like PayMongo, DragonPay)
3. **QR Code Payment** (generate QR, user scans)

**Example with PayMongo (Philippines payment gateway):**
```python
import requests

# In process_payment function:
if payment_method == "gcash":
    response = requests.post('https://api.paymongo.com/v1/payment_intents', 
        headers={'Authorization': f'Basic {PAYMONGO_SECRET}'},
        json={
            'amount': int(amount * 100),
            'currency': 'PHP',
            'payment_method_allowed': ['gcash'],
            'payment_method_options': {
                'gcash': {
                    'mobile_number': gcash_number
                }
            }
        }
    )
    payment_success = response.json()['data']['attributes']['status'] == 'succeeded'
```

---

## 🧪 Testing Payment System

### **Current Implementation (Demo Mode):**
- ✅ Accepts any valid format card number (13+ digits)
- ✅ Accepts any valid expiry (MM/YY format)
- ✅ Accepts any valid CVV (3+ digits)
- ✅ Accepts any valid GCash number (11 digits)
- ✅ Simulates successful payment

### **Test Cards (for Stripe integration):**
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Requires 3D Secure: `4000 0025 0000 3155`

---

## 📝 Payment Status Values

- **`pending`**: Payment not yet processed
- **`paid`**: Payment successful
- **`failed`**: Payment failed or declined

---

## 🔐 Security Notes

### **Current Implementation:**
- ⚠️ Payment details are sent to server (for demo)
- ⚠️ No encryption of card details
- ⚠️ Card details stored in request only (not saved)

### **For Production:**
1. **Use Payment Gateway SDKs** (Stripe Elements, PayPal SDK)
2. **Never store card details** on your server
3. **Use tokenization** - gateway returns tokens
4. **Implement webhooks** for payment confirmations
5. **Add SSL/HTTPS** (Render provides this automatically)
6. **Validate payments server-side** before marking as paid

---

## 🚀 Next Steps

1. **Choose a payment gateway:**
   - Stripe (supports Philippines)
   - PayPal
   - PayMongo (Philippines)
   - GCash Business API

2. **Get API keys:**
   - Sign up for payment gateway account
   - Get test/live API keys
   - Add to Render environment variables

3. **Update payment processing:**
   - Replace mock payment logic in `server.py`
   - Add real API calls
   - Handle webhooks for payment confirmations

4. **Test thoroughly:**
   - Test successful payments
   - Test failed payments
   - Test refunds (if needed)
   - Test webhook handling

---

## 📊 Payment Gateway Comparison

| Gateway | Card Support | GCash | Setup Difficulty | Fees |
|---------|-------------|-------|------------------|------|
| **Stripe** | ✅ | ❌ | Easy | ~3.4% + ₱15 |
| **PayMongo** | ✅ | ✅ | Medium | ~3.5% + ₱15 |
| **GCash API** | ❌ | ✅ | Hard | Contact GCash |
| **PayPal** | ✅ | ❌ | Easy | ~4.4% + fixed |

**Recommendation:** PayMongo for Philippines (supports both Card and GCash)

---

## ✅ Current Status

- ✅ Payment UI implemented
- ✅ Payment method selection working
- ✅ Payment processing endpoint created
- ✅ Database schema updated automatically
- ✅ Payment status displayed in admin/user views
- ⏳ **Ready for real gateway integration**

---

## 🎉 You're All Set!

The payment system is fully functional in demo mode. To go live:

1. Choose a payment gateway
2. Get API keys
3. Update the `process_payment` function in `server.py`
4. Test with real payments
5. Deploy!

**The foundation is ready - just plug in your payment gateway!** 🚀

