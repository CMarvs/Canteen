from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
import psycopg2, json
from psycopg2.extras import RealDictCursor
from psycopg2 import errors as psycopg2_errors
import os

app = FastAPI()

# Mount static files
try:
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
    else:
        print("⚠️ Warning: static directory not found, static files will not be served")
except Exception as e:
    print(f"⚠️ Warning: Could not mount static files: {e}")

# CORS - Allow all origins (works for both localhost and production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you can restrict this to your Render domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NeonDB connection - use environment variable or fallback to default
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_O0LrfcY7oGZN@ep-silent-rain-a19bkdss-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise HTTPException(500, f"Database connection failed: {str(e)}")

# --- Initialize menu_items table if it doesn't exist ---
def ensure_menu_table_exists():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'menu_items'
            ) as exists;
        """)
        result = cur.fetchone()
        # RealDictCursor returns a dict, so get the 'exists' key
        table_exists = result.get('exists') if isinstance(result, dict) else (result[0] if result else False)
        
        if not table_exists:
            print("[INFO] Creating menu_items table...")
            cur.execute("""
                CREATE TABLE menu_items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    price NUMERIC(10, 2) NOT NULL,
                    category TEXT NOT NULL DEFAULT 'foods',
                    is_available BOOLEAN DEFAULT TRUE,
                    quantity INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);")
            conn.commit()
            print("[SUCCESS] menu_items table created successfully!")
        else:
            print("[INFO] menu_items table already exists")
            # Check if quantity column exists, if not add it
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'menu_items' AND column_name = 'quantity'
                """)
                has_quantity = cur.fetchone() is not None
                
                if not has_quantity:
                    print("[INFO] Adding quantity column to menu_items table...")
                    cur.execute("ALTER TABLE menu_items ADD COLUMN quantity INTEGER DEFAULT 0;")
                    conn.commit()
                    print("[SUCCESS] quantity column added successfully!")
            except Exception as col_error:
                print(f"[WARNING] Could not check/add quantity column: {col_error}")
    except Exception as e:
        print(f"[ERROR] Error ensuring menu table exists: {e}")
        conn.rollback()
    finally:
        conn.close()

# Initialize table on startup (non-blocking)
try:
    ensure_menu_table_exists()
except Exception as e:
    print(f"[WARNING] Could not initialize menu table on startup: {e}")
    print("[INFO] The table will be created automatically when needed.")

# --- Safe FileResponse helper ---
def safe_file_response(path: str):
    try:
        full_path = os.path.abspath(path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            print(f"❌ File not found: {full_path}")
            return JSONResponse(status_code=404, content={"error": "File not found", "path": path})
    except Exception as e:
        print(f"❌ Error serving file {path}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# Routes
@app.get("/")
def home():
    try:
        return safe_file_response("templates/home.html")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Failed to serve home page: {str(e)}"})
@app.get("/index.html")
def index(): return safe_file_response("templates/index.html")
@app.get("/register.html")
def register_page(): return safe_file_response("templates/register.html")
@app.get("/order.html")
def order_page(): return safe_file_response("templates/order.html")
@app.get("/orders.html")
def orders_page(): return safe_file_response("templates/orders.html")
@app.get("/profile.html")
def profile_page(): return safe_file_response("templates/profile.html")
@app.get("/admin.html")
def admin_page(): return safe_file_response("templates/admin.html")
@app.get("/adminmenu.html")
def adminmenu_page(): return safe_file_response("templates/adminmenu.html")
@app.get("/home.html")
def home_page(): return safe_file_response("templates/home.html")

# Health check
@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# --- Test endpoint ---
@app.get("/ping")
def ping():
    return {"ok": True, "message": "Server works"}

# --- Register user ---
@app.post("/register")
async def register(request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE email=%s", (data.get("email"),))
        if cur.fetchone():
            raise HTTPException(400, "Email already registered")
        cur.execute(
            "INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,'user')",
            (data.get("name"), data.get("email"), data.get("password"))
        )
        conn.commit()
        return {"ok": True, "message": "User registered successfully"}
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(500, f"Registration failed: {str(e)}")
    finally:
        conn.close()

# --- Login ---
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (data.get("email"), data.get("password"))
        )
        user = cur.fetchone()
        if not user:
            raise HTTPException(400, "Invalid credentials")
        return user
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")
    finally:
        conn.close()

# --- Update user profile ---
@app.put("/users/{user_id}")
async def update_user(user_id: int, request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(404, f"User {user_id} not found")
        
        # Build update query based on provided fields
        updates = []
        params = []
        
        if "name" in data and data.get("name"):
            updates.append("name = %s")
            params.append(data.get("name"))
        
        if "password" in data and data.get("password"):
            if len(data.get("password")) < 4:
                raise HTTPException(400, "Password must be at least 4 characters")
            updates.append("password = %s")
            params.append(data.get("password"))
        
        if not updates:
            raise HTTPException(400, "No fields to update")
        
        # Add user_id for WHERE clause
        params.append(user_id)
        
        # Execute update
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, params)
        conn.commit()
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(500, "Failed to update user")
        
        return {"ok": True, "message": "Profile updated successfully", "user": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update user error: {e}")
        raise HTTPException(500, f"Failed to update profile: {str(e)}")
    finally:
        conn.close()

# --- Place order ---
@app.post("/orders")
async def place_order(request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if id_proof column exists, if not add it
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'id_proof'
            """)
            has_id_proof = cur.fetchone() is not None
            
            if not has_id_proof:
                print("[INFO] Adding id_proof column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN id_proof TEXT;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add id_proof column: {col_error}")
        
        # Decrement stock for ordered items
        items = data.get("items", [])
        for item in items:
            item_id = item.get("id")
            qty_ordered = item.get("qty", 0)
            if item_id and qty_ordered > 0:
                try:
                    # Get current quantity
                    cur.execute("SELECT quantity FROM menu_items WHERE id = %s", (item_id,))
                    result = cur.fetchone()
                    if result:
                        current_qty = result.get("quantity") or 0
                        new_qty = max(0, current_qty - qty_ordered)  # Don't go below 0
                        # Update quantity
                        cur.execute("UPDATE menu_items SET quantity = %s WHERE id = %s", (new_qty, item_id))
                        # If quantity reaches 0, mark as unavailable
                        if new_qty == 0:
                            cur.execute("UPDATE menu_items SET is_available = FALSE WHERE id = %s", (item_id,))
                except Exception as stock_error:
                    print(f"[WARNING] Could not update stock for item {item_id}: {stock_error}")
                    # Continue with order placement even if stock update fails
        
        # Insert order with id_proof
        id_proof = data.get("id_proof")
        cur.execute("""
            INSERT INTO orders(user_id,fullname,contact,location,items,total,id_proof)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            data.get("user_id"), data.get("fullname"), data.get("contact"),
            data.get("location"), json.dumps(items), data.get("total"),
            id_proof
        ))
        conn.commit()
        return {"ok": True, "message": "Order placed successfully"}
    except Exception as e:
        print(f"[ERROR] Order placement error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Order placement failed: {str(e)}")
    finally:
        conn.close()

# --- Admin: Get orders ---
@app.get("/orders")
def get_orders():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders ORDER BY id DESC")
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Get orders error: {e}")
        raise HTTPException(500, f"Failed to get orders: {str(e)}")
    finally:
        conn.close()

# --- Menu Items: Get all menu items ---
@app.get("/menu")
def get_menu_items():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM menu_items ORDER BY category, name")
        return cur.fetchall()
    except psycopg2_errors.UndefinedTable as e:
        print(f"❌ Table doesn't exist: {e}")
        conn.close()
        # Try to create table
        try:
            ensure_menu_table_exists()
            # Return empty list since table was just created
            return []
        except Exception as create_error:
            print(f"❌ Table creation failed: {create_error}")
            raise HTTPException(500, f"Menu table not found. Please run CREATE_MENU_TABLE.sql in your database.")
    except Exception as e:
        print(f"❌ Get menu items error: {e}")
        error_msg = str(e)
        if "does not exist" in error_msg or "relation" in error_msg.lower():
            raise HTTPException(404, f"Menu table not found. Please create the menu_items table. See CREATE_MENU_TABLE.sql")
        raise HTTPException(500, f"Failed to get menu items: {error_msg}")
    finally:
        conn.close()

# --- Menu Items: Add new menu item (Admin only) ---
@app.post("/menu")
async def add_menu_item(request: Request):
    data = await request.json()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        category = data.get("category", "foods")
        is_available = data.get("is_available", True)
        quantity = data.get("quantity", 0)
        if quantity is None:
            quantity = 0
        
        cur.execute("""
            INSERT INTO menu_items (name, price, category, is_available, quantity)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (
            data.get("name"),
            data.get("price"),
            category,
            is_available,
            quantity
        ))
        conn.commit()
        result = cur.fetchone()
        return {"ok": True, "message": "Menu item added successfully", "item": result}
    except psycopg2_errors.UndefinedTable as e:
        print(f"[ERROR] Table doesn't exist: {e}")
        if conn:
            conn.close()
        # Try to create table
        try:
            ensure_menu_table_exists()
            # Retry with new connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO menu_items (name, price, category, is_available, quantity)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data.get("name"),
                data.get("price"),
                data.get("category", "foods"),
                data.get("is_available", True),
                data.get("quantity", 0) or 0
            ))
            conn.commit()
            result = cur.fetchone()
            conn.close()
            return {"ok": True, "message": "Menu item added successfully", "item": result}
        except Exception as retry_error:
            print(f"[ERROR] Retry failed: {retry_error}")
            raise HTTPException(500, f"Table creation failed. Please run CREATE_MENU_TABLE.sql in your database. Error: {str(retry_error)}")
    except Exception as e:
        print(f"[ERROR] Add menu item error: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # Check for table not found errors
        if "does not exist" in error_msg or "relation" in error_msg.lower() or "UndefinedTable" in str(type(e)):
            # Try to create table and retry
            try:
                if conn:
                    conn.close()
                ensure_menu_table_exists()
                # Retry with new connection
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO menu_items (name, price, category, is_available)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                """, (
                    data.get("name"),
                    data.get("price"),
                    data.get("category", "foods"),
                    data.get("is_available", True)
                ))
                conn.commit()
                result = cur.fetchone()
                conn.close()
                return {"ok": True, "message": "Menu item added successfully", "item": result}
            except Exception as retry_error:
                print(f"[ERROR] Retry after table creation failed: {retry_error}")
                raise HTTPException(500, f"Failed to add menu item. Error: {str(retry_error)}")
        raise HTTPException(500, f"Failed to add menu item: {error_msg}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# --- Menu Items: Update menu item (Admin only) ---
@app.put("/menu/{item_id}")
async def update_menu_item(item_id: int, request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        updates = []
        params = []
        
        if "name" in data:
            updates.append("name = %s")
            params.append(data.get("name"))
        if "price" in data:
            updates.append("price = %s")
            params.append(data.get("price"))
        if "category" in data:
            updates.append("category = %s")
            params.append(data.get("category"))
        if "is_available" in data:
            updates.append("is_available = %s")
            params.append(data.get("is_available"))
        if "quantity" in data:
            updates.append("quantity = %s")
            params.append(data.get("quantity"))
        
        if not updates:
            raise HTTPException(400, "No fields to update")
        
        params.append(item_id)
        query = f"UPDATE menu_items SET {', '.join(updates)} WHERE id = %s RETURNING *"
        cur.execute(query, params)
        conn.commit()
        result = cur.fetchone()
        if not result:
            raise HTTPException(404, f"Menu item {item_id} not found")
        return {"ok": True, "message": "Menu item updated successfully", "item": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update menu item error: {e}")
        raise HTTPException(500, f"Failed to update menu item: {str(e)}")
    finally:
        conn.close()

# --- Menu Items: Delete menu item (Admin only) ---
@app.delete("/menu/{item_id}")
async def delete_menu_item(item_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM menu_items WHERE id=%s", (item_id,))
        if not cur.fetchone():
            raise HTTPException(404, f"Menu item {item_id} not found")
        
        cur.execute("DELETE FROM menu_items WHERE id=%s", (item_id,))
        conn.commit()
        return {"ok": True, "message": f"Menu item {item_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete menu item error: {e}")
        raise HTTPException(500, f"Failed to delete menu item: {str(e)}")
    finally:
        conn.close()

# --- Admin: Update order status or details ---
@app.put("/orders/{oid}")
async def update_order(oid: int, request: Request):
    data = await request.json()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Check if order exists and get current status
        cur.execute("SELECT status FROM orders WHERE id=%s", (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        current_status = order.get("status") if isinstance(order, dict) else order[0] if order else None
        
        # If updating order details (not just status), check if order is Pending
        if "fullname" in data or "contact" in data or "location" in data or "items" in data or "total" in data:
            if current_status != "Pending":
                raise HTTPException(400, f"Cannot edit order. Only orders with 'Pending' status can be edited. Current status: {current_status}")
            
            # Build update query for order details
            updates = []
            params = []
            
            if "fullname" in data:
                updates.append("fullname = %s")
                params.append(data.get("fullname"))
            if "contact" in data:
                updates.append("contact = %s")
                params.append(data.get("contact"))
            if "location" in data:
                updates.append("location = %s")
                params.append(data.get("location"))
            if "items" in data:
                updates.append("items = %s")
                params.append(json.dumps(data.get("items")))
            if "total" in data:
                updates.append("total = %s")
                params.append(data.get("total"))
            
            # Also update status if provided
            if "status" in data:
                updates.append("status = %s")
                params.append(data.get("status"))
            
            if updates:
                params.append(oid)
                query = f"UPDATE orders SET {', '.join(updates)} WHERE id = %s RETURNING *"
                cur.execute(query, params)
                conn.commit()
                result = cur.fetchone()
                return {"ok": True, "message": "Order updated successfully", "order": result}
        
        # If only updating status
        if "status" in data:
            cur.execute("UPDATE orders SET status=%s WHERE id=%s RETURNING *",
                        (data.get("status"), oid))
            conn.commit()
            result = cur.fetchone()
            if not result:
                raise HTTPException(404, f"Order {oid} not found")
            return result
        
        raise HTTPException(400, "No valid fields to update")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update order error: {e}")
        raise HTTPException(500, f"Failed to update order: {str(e)}")
    finally:
        conn.close()

# --- Admin: Delete/Cancel order ---
@app.delete("/orders/{oid}")
async def delete_order(oid: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if order exists and get full order data (including items)
        cur.execute("SELECT id, status, items FROM orders WHERE id=%s", (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        # Get status (handle both dict and tuple responses)
        if isinstance(order, dict):
            order_status = order.get("status")
            order_items = order.get("items")
        else:
            order_status = order[1] if len(order) > 1 else None
            order_items = order[2] if len(order) > 2 else None
        
        # Only allow cancellation if status is Pending
        if order_status != "Pending":
            raise HTTPException(400, f"Cannot cancel order. Only orders with 'Pending' status can be cancelled. Current status: {order_status}")
        
        # Restore stock for all items in the order
        if order_items:
            try:
                # Parse items if it's a JSON string
                items = json.loads(order_items) if isinstance(order_items, str) else order_items
                
                for item in items:
                    item_id = item.get("id")
                    qty_ordered = item.get("qty", 0)
                    
                    if item_id and qty_ordered > 0:
                        try:
                            # Get current quantity
                            cur.execute("SELECT quantity FROM menu_items WHERE id = %s", (item_id,))
                            result = cur.fetchone()
                            if result:
                                current_qty = result.get("quantity") if isinstance(result, dict) else (result[0] if result else 0)
                                new_qty = current_qty + qty_ordered  # Restore the quantity
                                
                                # Update quantity
                                cur.execute("UPDATE menu_items SET quantity = %s WHERE id = %s", (new_qty, item_id))
                                
                                # If stock was 0 and now has items, mark as available
                                if current_qty == 0 and new_qty > 0:
                                    cur.execute("UPDATE menu_items SET is_available = TRUE WHERE id = %s", (item_id,))
                                
                                print(f"[INFO] Restored {qty_ordered} units of item {item_id}. New stock: {new_qty}")
                        except Exception as stock_error:
                            print(f"[WARNING] Could not restore stock for item {item_id}: {stock_error}")
                            # Continue with other items even if one fails
            except Exception as items_error:
                print(f"[WARNING] Could not parse order items for stock restoration: {items_error}")
                # Continue with order deletion even if stock restoration fails
        
        # Delete the order
        cur.execute("DELETE FROM orders WHERE id=%s", (oid,))
        conn.commit()
        return {"ok": True, "message": f"Order {oid} cancelled successfully and stock restored"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete order error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to cancel order: {str(e)}")
    finally:
        conn.close()
