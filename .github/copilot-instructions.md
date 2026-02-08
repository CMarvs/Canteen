# Copilot Instructions - Online Canteen

## Project Overview
Online Canteen is a full-stack food ordering system built with FastAPI (Python backend) and vanilla JavaScript frontend. It uses NeonDB PostgreSQL for data storage and integrates GCash payment processing via PayMongo.

**Key Stack**: FastAPI 0.115.0 | Uvicorn | PostgreSQL (NeonDB) | Vanilla JS | psycopg2

---

## Architecture & Component Boundaries

### Backend (server.py - 3379 lines)
- **FastAPI app** with CORS middleware, GZip compression, and security headers
- **Database**: PostgreSQL with auto-migration on startup (creates tables if missing)
- **Core endpoints**: `/orders`, `/menu`, `/login`, `/register`, `/payment/*`, `/ratings`, `/messages`
- **Key pattern**: Defensive table initialization - all tables created with `ensure_*_table_exists()` on startup

### Database Schema
Five main tables with automatic column additions:
- `users`: id, name, email, password, role (admin/user), id_proof, selfie_proof, is_approved, created_at
- `orders`: id, user_id, fullname, contact, location, items (JSON), total, payment_method, payment_status, payment_proof, refund_status, created_at
- `menu_items`: id, name, price, category, quantity, is_available, image_url, created_at
- `chat_messages`: id, order_id, user_id, sender_role, sender_name, message, image, is_read, read_at, created_at
- `service_ratings`: id, user_id, rating (1-5), comment, created_at, UNIQUE(user_id)

**Critical pattern**: Items stored as JSON string in `orders.items`. Each item object includes: `id`, `name`, `qty`, `price`, `image_url`.

### Frontend Architecture
- **Static files** serve HTML templates from `/templates` directory
- **Three user views**: home.html (landing), order.html (menu/cart), orders.html (user orders), admin.html (admin dashboard), profile.html
- **State management**: localStorage (`canteen_current_v2` for user, cart, soldout_items)
- **API calls**: All use `${API_BASE}` variable pointing to `/` (same-origin)

---

## Critical Developer Workflows

### 1. Starting the Server (Windows)
```bash
# Option A: Use startup script (simplest)
python start_server.py
# or double-click START_SERVER.bat

# Option B: Manual
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```
Server runs on `http://localhost:8000` with auto-reload enabled for development.

### 2. Database Setup (First Run)
```bash
# Ensure DATABASE_URL environment variable is set to your NeonDB connection string
# Then run:
python setup_database.py
```
This creates all tables and inserts default accounts (admin@canteen/admin123, user@demo/user123).

### 3. Testing Payment Flow
- **GCash**: Uses PayMongo API - requires `PAYMONGO_SECRET_KEY` and `PAYMONGO_PUBLIC_KEY` env vars
- **Cash/COD**: Auto-marked as "paid" in database
- Payment proof uploads stored as image URLs in `orders.payment_proof`

### 4. Real-time Polling
- **Orders page**: Polls `/orders` every 8 seconds for status updates
- **Chat messages**: Polls `/orders/{order_id}/messages` every 5 seconds
- **Unread badges**: Tracked via `lastKnownUserMessageIds` Set to detect new messages

---

## Project-Specific Conventions & Patterns

### 1. Item Images
- **Storage**: Images uploaded to `/static/images/menu_items/` directory
- **Database field**: `image_url` in `menu_items` and stored in order items JSON
- **Display**: Use `imageUrl ? `/${item.image_url}` : '/static/images/menu_items/default.jpg'` fallback
- **In orders**: Items now display with 70×70px thumbnails between price and quantity/total

### 2. Order Status Flow
Possible statuses: `Pending` → `Preparing` → `Out for Delivery` → `Delivered`
- Admin updates via PUT `/orders/{oid}` with `{status: "new_status"}`
- Users see "Edit" button only on Pending orders
- Completed orders show "Rate Service" button

### 3. Cart to Order Pipeline
1. User adds items to localStorage cart via `addToCartById(id, qty)` - **now includes `image_url`**
2. Cart rendered with images via `renderCart()` - shows thumbnail + price calculation
3. User places order: cart items serialized as JSON string in `orders.items`
4. Admin receives with full item details including images

### 4. User Approval Workflow
- New users start as `is_approved = FALSE`
- Admin can approve via PUT `/users/{user_id}/approve`
- User sees approval status in profile.html

### 5. Chat System
- Each order can have multiple messages via `/orders/{order_id}/messages`
- Messages linked to users; admin can reply
- Read status tracked with `is_read` and `read_at` fields
- Notifications only show for unread admin messages

### 6. Error Handling - Database Connection
- **Defensive pattern**: All table creation is non-blocking
- If DB unavailable at startup: server continues, tables created on first request
- Each endpoint checks for missing columns and adds them dynamically
- *Never* crashes on DB schema issues

### 7. Session Management
- User stored in localStorage: `canteen_current_v2` (JSON object with id, name, email, role)
- `ensureLoggedIn(requiredRole)` validates on page load - redirects to index.html if not authenticated
- Role-based access: 'admin' or 'user'

### 8. Payment Methods
- **Values**: `'cash'` (default), `'cod'` (cash on delivery), `'gcash'`
- **GCash logic**: Requires payment_proof screenshot upload; marked "pending" until admin verifies
- **Refunds**: Tracked via `refund_status` field ('pending', 'refunded')

---

## Integration Points & External Dependencies

### PayMongo (GCash)
- **Endpoint**: `/payment/process` accepts `{order_id, amount, gcash_number, order_details}`
- **Response**: Returns `payment_intent_id` for tracking
- **Callback**: POST `/payment/callback` updates payment status
- **Config**: `payment_gateway.py` handles all PayMongo logic

### Image Upload
- Form enctype must be `multipart/form-data`
- Images stored in filesystem at `/static/images/menu_items/`
- Database stores path as relative: `static/images/menu_items/filename.jpg`

### Environment Variables (Required for Production)
```
DATABASE_URL=postgresql://...
PAYMONGO_SECRET_KEY=...
PAYMONGO_PUBLIC_KEY=...
ADMIN_GCASH_NUMBER=09947784922
```

---

## Debugging Tips

### Order Items Not Showing Images?
1. Check `orders.items` column contains valid JSON with `image_url` field
2. Verify images exist at `/static/images/menu_items/` directory
3. Use fallback: `item.image_url || 'default.jpg'`

### Cart Items Lost?
- localStorage key is `canteen_current_v2` - check browser dev tools
- `saveCart()` serializes to JSON; `getCart()` parses it back

### Admin Orders Display Issues?
- Run `/orders/fix-corrupted` endpoint to validate/clean item JSON
- Items > 5000 chars total get reset to empty array

### Chat Notifications Not Working?
- Verify `is_read = FALSE` in database
- Check polling interval (5 sec in code) - may need refresh
- Ensure `sender_role = 'admin'` for user notifications

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [server.py](server.py) | FastAPI backend - all endpoints & database logic |
| [payment_gateway.py](payment_gateway.py) | PayMongo GCash integration |
| [static/script.js](static/script.js) | Frontend logic - cart, orders, chat, ratings |
| [templates/order.html](templates/order.html) | Menu & cart UI |
| [templates/orders.html](templates/orders.html) | User orders history (with real-time polling) |
| [templates/admin.html](templates/admin.html) | Admin dashboard (orders + menu management) |
| [templates/profile.html](templates/profile.html) | User profile & approval status |
| [setup_database.py](setup_database.py) | Initial DB schema + test data |

---

## Performance Considerations

- **Static file caching**: 1 hour for `/static/*` files
- **No-cache headers**: Dynamic endpoints use `Cache-Control: no-cache`
- **JSON serialization**: Uses custom `serialize_datetime()` to handle Decimal/datetime objects
- **Polling**: User orders page + chat use exponential intervals to reduce server load

---

## When Adding Features

1. **New table?** Add to `server.py` startup checks - follow `ensure_*_table_exists()` pattern
2. **New order field?** Update `setup_database.py` schema AND add migration in `server.py`
3. **New images?** Store in `/static/images/menu_items/`, reference in DB as relative path
4. **New endpoint?** Add CORS handling if cross-origin needed; use `json_response()` helper for proper headers
5. **Changes to items JSON?** Update `addToCartById()`, `orderCardHtmlForUser()`, and admin order rendering

