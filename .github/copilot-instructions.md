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

### 1. Item Images - Complete System
**Storage**: Images uploaded via admin panel to `/static/images/menu_items/` directory
- Customers see **180×180px fixed frame** images in menu
- Admin sees **140×140px fixed frame** images in management page
- Cart/orders show **70×70px fixed frame** images

**Database field**: `image_url` in `menu_items` table stores relative path (`static/images/menu_items/filename.jpg`)

**Display pattern**: 
```javascript
// Always use this URL construction pattern
let imageUrl = '/static/images/menu_items/default.jpg';
if (item.image_url) {
  const url = String(item.image_url).trim();
  imageUrl = url.startsWith('/') ? url : `/${url}`;
}
// Always add error handler for missing images
<img src="${imageUrl}" onerror="this.src='/static/images/menu_items/default.jpg';">
```

**Admin Upload Flow**:
1. Admin selects image in Menu Management "Add Photo" section
2. Frontend calls `POST /upload-menu-image` with multipart/form-data
3. Backend saves file to `/static/images/menu_items/` with timestamp-based unique name
4. Returns JSON with `image_url` path for storage in database
5. When adding menu item, `image_url` is stored in database via POST `/menu`

**File size limits**: Max 5MB, JPEG/PNG only

### 2. Menu Item Display in Customer View
- **Function**: `itemCardHtml()` renders each menu item with **180×180px fixed-size image frame**
- **Layout**: Image at top in container, name, price, stock badge, quantity/add-to-cart below
- **Stock display**: Color-coded badge (green >10 in stock, orange <10, red out-of-stock)  
- **Sold-out items**: Show "SOLD OUT" label instead of add-to-cart button

### 3. Admin Menu Management Interface  
New unified UI in admin.html with easy image upload:
- **Add Item Section**: Grid inputs for Name, Price, Category, Stock (all visible at once)
- **Add Photo Section**: Dedicated file upload field with drag-drop, preview, and upload button
- **Upload endpoint**: `POST /upload-menu-image` with multipart/form-data
  - Returns: `{ok: true, image_url: "static/images/menu_items/file_timestamp.jpg"}`
  - Files saved with Unix timestamp to ensure uniqueness
  - Constraints: JPG/PNG only, max 5MB
- **Item Display**: Each menu item shows **140×140px image on left** + info/controls on right
- **Stock Update**: Quick edit fields for each item without modal dialogs

### 4. Order Status Flow
Possible statuses: `Pending` → `Preparing` → `Out for Delivery` → `Delivered`
- Admin updates via PUT `/orders/{oid}` with `{status: "new_status"}`
- Users see "Edit" button only on Pending orders
- Completed orders show "Rate Service" button

### 5. Cart to Order Pipeline
1. User adds items via `addToCartById(id, qty)` - **includes `image_url` from menu_items**
2. Cart displayed with **70×70px images**, quantity, and calculations
3. User places order: cart items serialized as JSON → `orders.items` column
4. Admin views orders with **70×70px thumbnails** in order detail
5. Customer sees order history with **70×70px thumbnails** per item

### 6. User Approval Workflow
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

---

## Image Upload System (Detailed)

### Backend Endpoint: POST /upload-menu-image
**Location**: [server.py](server.py#L1946)
**Request**: multipart/form-data with file field
**Response**: 
```json
{
  "ok": true,
  "image_url": "static/images/menu_items/pizza_1702541234567.jpg",
  "filename": "pizza_1702541234567.jpg"
}
```
**File validation**:
- Content-Type: `image/jpeg` or `image/png` only
- File size: ≤ 5MB (5242880 bytes)
- Directory: `/static/images/menu_items/` auto-created if missing
- Filename format: `{original_name}_{unix_timestamp_ms}.{ext}` to prevent collisions

### Frontend Upload Function
**Location**: [templates/admin.html](templates/admin.html#L66)
**Function**: `uploadItemImage()`
- Validates file type/size on client before upload
- Shows upload status message (success/error) to admin
- Returns `image_url` value for database storage

### Image Display in Customer Menu
**Function**: [itemCardHtml()](static/script.js#L604)
- Displays **180×180px fixed-size image frame** at top of card
- Uses `object-fit: cover` to fill frame without distortion
- Includes `onerror` handler to fallback to default.jpg
- Stock badge (green/orange/red) overlays bottom-right

### Image Display in Admin Management  
**Function**: [renderAdminMenuList()](templates/admin.html#L2049)
- Shows **140×140px fixed-size image on left** side of item row
- Right side displays: name, price, stock, action buttons (edit, delete, toggle availability)
- Grid layout keeps UI compact and scannable

### Image Display in Cart
**Function**: [renderCart()](static/script.js#L770)
- Shows **70×70px image thumbnail** on left
- Right side: item name, quantity selector, price calculation
- `flex-shrink: 0` prevents image distortion
- Fallback for missing images automatic via onerror

### Image Display in Order History
**Function**: [orderCardHtmlForUser()](static/script.js#L880)
- Shows **70×70px image thumbnail** for each item in order
- Displays in flexible grid layout
- Includes item name, quantity, and unit price
- Order total shows below all items

### URL Handling Across All Functions
**Critical pattern** used everywhere images display:
```javascript
let imageUrl = '/static/images/menu_items/default.jpg';
if (item.image_url) {
  const url = String(item.image_url).trim();
  // Handle both 'static/...' and '/static/...' formats
  imageUrl = url.startsWith('/') ? url : `/${url}`;
}
// Use with error handler
<img src="${imageUrl}" onerror="this.src='/static/images/menu_items/default.jpg';">
```

### Database Integration
- **Table**: `menu_items`
- **Column**: `image_url` (text/varchar)
- **What's stored**: Relative path like `static/images/menu_items/pizza_1702541234567.jpg`
- **When saving menu item**: POST `/menu` endpoint receives `image_url` from upload response
- **When order placed**: `addToCartById()` includes item's `image_url` in cart object
- **In orders table**: Each order's `items` JSON includes `image_url` for all items

### Default Placeholder Image
- **Location**: `/static/images/menu_items/default.jpg`
- **Created by**: [create_default_image.py](create_default_image.py)
- **Size**: 180×180px (works for all display contexts)
- **What it shows**: Gray background with camera emoji (📷)
- **Usage**: Automatic fallback when image URL is missing or 404s

### Adding Images to Existing Menu Items
1. Admin goes to admin.html → Menu Management section
2. Clicks "📸 Add Photo for Item" file input
3. Selects JPG/PNG file (max 5MB)
4. Clicks "Upload Photo" button
5. File uploads via POST /upload-menu-image
6. Success message shows filename
7. Creates new menu item with that image_url, OR
8. Edit existing item and replace image_url field

### Error Handling
- **Missing image**: Displays default.jpg via onerror handler
- **404 on image URL**: Caught by onerror handler
- **Invalid file upload**: Backend returns 400 with error message
- **File too large**: Frontend validates before upload (also backend enforces)
- **Wrong file type**: Backend rejects with 400 Bad Request

