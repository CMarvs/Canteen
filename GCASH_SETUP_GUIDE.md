# 📱 GCash Payment Integration Setup Guide

## ✅ Real GCash Integration Implemented!

Your application now supports **real GCash payments** via PayMongo payment gateway!

---

## 🎯 What's Been Implemented

1. **PayMongo Integration** - Real GCash payment processing
2. **Payment Gateway Module** - `payment_gateway.py` handles all payment logic
3. **Payment Status Tracking** - Real-time payment status updates
4. **Webhook Support** - Payment callbacks from PayMongo
5. **Fallback Mode** - Works in demo mode if API keys not configured

---

## 🔧 Setup Instructions

### Step 1: Sign Up for PayMongo

1. Go to [PayMongo](https://paymongo.com) and create an account
2. Complete business verification
3. Get your API keys from the dashboard:
   - **Secret Key** (starts with `sk_`)
   - **Public Key** (starts with `pk_`)

### Step 2: Set Environment Variables

Add these to your **Render environment variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `PAYMONGO_SECRET_KEY` | Your PayMongo secret key | `sk_test_...` or `sk_live_...` |
| `PAYMONGO_PUBLIC_KEY` | Your PayMongo public key | `pk_test_...` or `pk_live_...` |
| `APP_URL` | Your app URL (for callbacks) | `https://your-app.onrender.com` |

**In Render Dashboard:**
1. Go to your service → **Environment** tab
2. Add the variables above
3. Click **Save Changes** (auto-redeploys)

### Step 3: Configure Webhook (Optional but Recommended)

1. In PayMongo dashboard → **Webhooks**
2. Add webhook URL: `https://your-app.onrender.com/payment/callback`
3. Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Save webhook

---

## 🧪 Testing

### Test Mode (PayMongo Test Keys)

1. Use PayMongo **test keys** (starts with `sk_test_`)
2. Test GCash number: Use any valid 11-digit number
3. Payments will be simulated (no real money)

### Live Mode (PayMongo Live Keys)

1. Use PayMongo **live keys** (starts with `sk_live_`)
2. Real GCash payments will be processed
3. Real money transactions

---

## 🔄 How It Works

### **Payment Flow:**

1. **User selects GCash** and enters mobile number
2. **Order is created** with `payment_status: 'pending'`
3. **PayMongo API is called**:
   - Creates payment intent
   - Attaches GCash payment method
   - Returns redirect URL or success
4. **User redirected to GCash** (if needed) to confirm payment
5. **Payment status updated** to `'paid'` when confirmed
6. **Webhook received** (optional) to confirm payment

### **Payment Status:**

- **`pending`**: Payment request sent, waiting for user confirmation
- **`paid`**: Payment successful
- **`failed`**: Payment failed or declined

---

## 📝 API Endpoints

### **Process Payment:**
```
POST /payment/process
Body: {
  "order_id": 123,
  "payment_method": "gcash",
  "amount": 150.00,
  "payment_details": {
    "gcashNumber": "09123456789"
  }
}
```

### **Payment Callback (Webhook):**
```
POST /payment/callback
Body: { PayMongo webhook data }
```

### **Check Payment Status:**
```
GET /payment/status/{payment_intent_id}
```

---

## 🔐 Security Notes

1. **Never commit API keys** to GitHub
2. **Use environment variables** for all secrets
3. **Enable HTTPS** (Render does this automatically)
4. **Verify webhook signatures** (PayMongo provides this)
5. **Validate payment amounts** server-side

---

## 🐛 Troubleshooting

### Issue: "PAYMONGO_SECRET_KEY not set"
**Solution:** Add `PAYMONGO_SECRET_KEY` to Render environment variables

### Issue: Payment stuck on "pending"
**Solution:** 
- Check PayMongo dashboard for payment status
- Verify webhook is configured correctly
- Check server logs for errors

### Issue: "Invalid GCash number"
**Solution:** Ensure mobile number is exactly 11 digits (e.g., 09123456789)

### Issue: Payment fails
**Solution:**
- Check PayMongo dashboard for error details
- Verify API keys are correct (test vs live)
- Check account balance/limits in PayMongo

---

## 💰 PayMongo Fees

- **Transaction Fee**: ~3.5% + ₱15 per transaction
- **No monthly fees** (pay-as-you-go)
- **Test mode**: Free (no real charges)

---

## 🚀 Going Live

1. **Complete PayMongo verification**
2. **Switch to live keys** in environment variables
3. **Test with small amount** first
4. **Monitor transactions** in PayMongo dashboard
5. **Set up webhooks** for automatic status updates

---

## 📞 Support

- **PayMongo Support**: support@paymongo.com
- **PayMongo Docs**: https://developers.paymongo.com
- **GCash Business**: Contact GCash for direct API access

---

## ✅ Current Status

- ✅ PayMongo integration implemented
- ✅ GCash payment processing ready
- ✅ Payment status tracking working
- ✅ Webhook support added
- ⏳ **Configure PayMongo API keys to enable real payments**

---

## 🎉 Next Steps

1. **Sign up for PayMongo** account
2. **Get API keys** from dashboard
3. **Add to Render** environment variables
4. **Test with test keys** first
5. **Switch to live keys** when ready

**Your GCash integration is ready - just add your PayMongo API keys!** 🚀

