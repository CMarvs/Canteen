from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
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
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y6Bh0RQzxKib@ep-red-violet-a1hjbfb0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

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
            # Check and add missing columns
            try:
                # Get all existing columns
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'menu_items'
                """)
                existing_columns = [row.get('column_name') if isinstance(row, dict) else row[0] for row in cur.fetchall()]
                
                # Check and add category column if missing
                if 'category' not in existing_columns:
                    print("[INFO] Adding category column to menu_items table...")
                    cur.execute("ALTER TABLE menu_items ADD COLUMN category TEXT NOT NULL DEFAULT 'foods';")
                    conn.commit()
                    print("[SUCCESS] category column added successfully!")
                
                # Check and add is_available column if missing
                if 'is_available' not in existing_columns:
                    print("[INFO] Adding is_available column to menu_items table...")
                    cur.execute("ALTER TABLE menu_items ADD COLUMN is_available BOOLEAN DEFAULT TRUE;")
                    conn.commit()
                    print("[SUCCESS] is_available column added successfully!")
                
                # Check and add quantity column if missing
                if 'quantity' not in existing_columns:
                    print("[INFO] Adding quantity column to menu_items table...")
                    cur.execute("ALTER TABLE menu_items ADD COLUMN quantity INTEGER DEFAULT 0;")
                    conn.commit()
                    print("[SUCCESS] quantity column added successfully!")
                
                # Check and add created_at column if missing
                if 'created_at' not in existing_columns:
                    print("[INFO] Adding created_at column to menu_items table...")
                    cur.execute("ALTER TABLE menu_items ADD COLUMN created_at TIMESTAMP DEFAULT NOW();")
                    conn.commit()
                    print("[SUCCESS] created_at column added successfully!")
                
                # Create indexes if they don't exist
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);")
                    conn.commit()
                except Exception as idx_error:
                    print(f"[WARNING] Could not create indexes: {idx_error}")
                    
            except Exception as col_error:
                print(f"[WARNING] Could not check/add columns: {col_error}")
                import traceback
                traceback.print_exc()
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
            # Add aggressive no-cache headers to prevent browser and CDN caching
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT"
            }
            return HTMLResponse(content=content, headers=headers)
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
        
        # Check if id_proof column exists, if not add it
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id_proof'
            """)
            has_id_proof = cur.fetchone() is not None
            
            if not has_id_proof:
                print("[INFO] Adding id_proof column to users table...")
                cur.execute("ALTER TABLE users ADD COLUMN id_proof TEXT;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add id_proof column: {col_error}")
        
        # Check if selfie_proof column exists, if not add it
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'selfie_proof'
            """)
            has_selfie_proof = cur.fetchone() is not None
            
            if not has_selfie_proof:
                print("[INFO] Adding selfie_proof column to users table...")
                cur.execute("ALTER TABLE users ADD COLUMN selfie_proof TEXT;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add selfie_proof column: {col_error}")
        
        # Check if is_approved column exists, if not add it
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'is_approved'
            """)
            has_is_approved = cur.fetchone() is not None
            
            if not has_is_approved:
                print("[INFO] Adding is_approved column to users table...")
                cur.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;")
                # Set existing users (except admin) as approved
                cur.execute("UPDATE users SET is_approved = TRUE WHERE role != 'admin' OR role IS NULL;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add is_approved column: {col_error}")
        
        cur.execute("SELECT 1 FROM users WHERE email=%s", (data.get("email"),))
        if cur.fetchone():
            raise HTTPException(400, "Email already registered")
        
        # Check if this is the first user - make them admin automatically
        cur.execute("SELECT COUNT(*) as count FROM users")
        result = cur.fetchone()
        user_count = result.get('count') if isinstance(result, dict) else (result[0] if result else 0)
        is_first_user = user_count == 0
        
        # Determine role and approval status
        if is_first_user:
            # First user becomes admin and is automatically approved
            user_role = 'admin'
            is_approved = True
            id_proof = data.get("id_proof")  # Optional for first admin
            selfie_proof = data.get("selfie_proof")  # Optional for first admin
            message = "Admin account created successfully! You can now login."
        else:
            # Subsequent users need approval
            user_role = 'user'
            is_approved = False
            id_proof = data.get("id_proof")
            selfie_proof = data.get("selfie_proof")
            if not id_proof:
                raise HTTPException(400, "ID proof is required for registration")
            if not selfie_proof:
                raise HTTPException(400, "Selfie proof is required for registration")
            message = "User registered successfully. Account pending admin approval."
        
        cur.execute(
            "INSERT INTO users(name,email,password,role,id_proof,selfie_proof,is_approved) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (data.get("name"), data.get("email"), data.get("password"), user_role, id_proof, selfie_proof, is_approved)
        )
        conn.commit()
        return {"ok": True, "message": message}
    except HTTPException:
        raise
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
        
        # Check if user is approved (admin accounts are always approved)
        # First, ensure all existing admin accounts are approved
        if isinstance(user, dict):
            role = user.get("role")
            is_approved = user.get("is_approved")
            user_id = user.get("id")
        else:
            # Handle tuple response - get column names to find correct index
            col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
            try:
                id_idx = col_names.index('id') if 'id' in col_names else 0
                role_idx = col_names.index('role') if 'role' in col_names else 4
                is_approved_idx = col_names.index('is_approved') if 'is_approved' in col_names else 6
                user_id = user[id_idx] if len(user) > id_idx else None
                role = user[role_idx] if len(user) > role_idx else None
                is_approved = user[is_approved_idx] if len(user) > is_approved_idx else None
            except:
                # Fallback to default positions
                user_id = user[0] if len(user) > 0 else None
                role = user[4] if len(user) > 4 else None
                is_approved = user[6] if len(user) > 6 else None
        
        # Admin accounts are always approved - check role first
        if role == 'admin':
            # Auto-approve admin if not already approved (fix for existing admins)
            if is_approved is False or is_approved == 0 or is_approved is None:
                try:
                    cur.execute("UPDATE users SET is_approved = TRUE WHERE id = %s AND role = 'admin'", (user_id,))
                    conn.commit()
                    # Update the user dict/tuple for return
                    if isinstance(user, dict):
                        user['is_approved'] = True
                except:
                    pass  # Continue even if update fails
            # Admin can always login regardless of approval status
            return user
        
        # Regular users need approval
        if is_approved is False or is_approved == 0 or is_approved is None:
            raise HTTPException(403, "Account pending admin approval. Please wait for approval.")
        
        return user
    except HTTPException:
        raise
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
        
        # Check and add payment columns if they don't exist
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'payment_method'
            """)
            has_payment_method = cur.fetchone() is not None
            
            if not has_payment_method:
                print("[INFO] Adding payment_method column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'cash';")
                conn.commit()
            
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'payment_status'
            """)
            has_payment_status = cur.fetchone() is not None
            
            if not has_payment_status:
                print("[INFO] Adding payment_status column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'pending';")
                conn.commit()
            
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'payment_intent_id'
            """)
            has_payment_intent_id = cur.fetchone() is not None
            
            if not has_payment_intent_id:
                print("[INFO] Adding payment_intent_id column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN payment_intent_id TEXT;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add payment columns: {col_error}")
        
        # Insert order with payment information
        payment_method = data.get("payment_method", "cash")
        payment_status = data.get("payment_status", "pending")
        
        cur.execute("""
            INSERT INTO orders(user_id,fullname,contact,location,items,total,payment_method,payment_status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            data.get("user_id"), data.get("fullname"), data.get("contact"),
            data.get("location"), json.dumps(items), data.get("total"),
            payment_method, payment_status
        ))
        result = cur.fetchone()
        conn.commit()
        return {"ok": True, "message": "Order placed successfully", "order": result}
    except Exception as e:
        print(f"[ERROR] Order placement error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Order placement failed: {str(e)}")
    finally:
        conn.close()

# --- Payment Callback (Webhook) ---
@app.post("/payment/callback")
async def payment_callback(request: Request):
    """Handle payment callbacks from PayMongo/GCash"""
    try:
        data = await request.json()
        
        # PayMongo webhook format
        event_type = data.get("data", {}).get("attributes", {}).get("type") or data.get("type")
        payment_intent_data = data.get("data", {}).get("attributes", {}).get("data", {})
        
        # Extract payment intent ID
        payment_intent_id = None
        if payment_intent_data:
            payment_intent_id = payment_intent_data.get("id")
        if not payment_intent_id:
            payment_intent_id = data.get("data", {}).get("id") or data.get("payment_intent_id")
        
        # Extract status
        status = None
        if payment_intent_data:
            status = payment_intent_data.get("attributes", {}).get("status")
        if not status:
            status = data.get("data", {}).get("attributes", {}).get("status") or data.get("status")
        
        print(f"[INFO] Payment callback received: event={event_type}, payment_intent_id={payment_intent_id}, status={status}")
        
        if not payment_intent_id:
            return {"ok": False, "message": "Missing payment intent ID"}
        
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            
            # Find order by payment_intent_id
            cur.execute("SELECT id, payment_status FROM orders WHERE payment_intent_id = %s", (payment_intent_id,))
            order = cur.fetchone()
            
            if order:
                order_id = order.get("id")
                current_status = order.get("payment_status")
                
                # Update payment status based on webhook
                if status == "succeeded" and current_status != "paid":
                    cur.execute("""
                        UPDATE orders 
                        SET payment_status = 'paid'
                        WHERE id = %s
                    """, (order_id,))
                    conn.commit()
                    print(f"[SUCCESS] Order {order_id} payment confirmed via webhook")
                elif status == "failed" and current_status != "failed":
                    cur.execute("""
                        UPDATE orders 
                        SET payment_status = 'failed'
                        WHERE id = %s
                    """, (order_id,))
                    conn.commit()
                    print(f"[INFO] Order {order_id} payment failed via webhook")
            else:
                print(f"[WARNING] Order not found for payment_intent_id: {payment_intent_id}")
            
            return {"ok": True, "message": "Payment callback processed"}
        finally:
            conn.close()
            
    except Exception as e:
        print(f"[ERROR] Payment callback error: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "message": str(e)}

# Note: GCash QR code generation removed - GCash doesn't accept generic QR codes
# Users will manually send payment via GCash app with instructions shown in modal

# --- Check Payment Status ---
@app.get("/payment/status/{payment_intent_id}")
async def check_payment_status(payment_intent_id: str):
    """Check payment status from payment gateway"""
    try:
        from payment_gateway import check_payment_status_paymongo
        
        status = check_payment_status_paymongo(payment_intent_id)
        
        # Update order status if payment succeeded
        if status.get("paid"):
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                # Find order by payment_intent_id
                cur.execute("""
                    UPDATE orders 
                    SET payment_status = 'paid'
                    WHERE payment_intent_id = %s
                    AND payment_status != 'paid'
                """, (payment_intent_id,))
                conn.commit()
                print(f"[INFO] Updated order payment status to paid for payment_intent_id: {payment_intent_id}")
            finally:
                conn.close()
        
        return status
    except Exception as e:
        print(f"[ERROR] Check payment status error: {e}")
        raise HTTPException(500, f"Failed to check payment status: {str(e)}")

# --- Payment Processing ---
@app.post("/payment/process")
async def process_payment(request: Request):
    """Process payment for an order"""
    data = await request.json()
    order_id = data.get("order_id")
    payment_method = data.get("payment_method")
    amount = data.get("amount")
    payment_details = data.get("payment_details", {})
    
    if not order_id or not payment_method or not amount:
        raise HTTPException(400, "Missing required payment information")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Verify order exists
        cur.execute("SELECT id, total, payment_status FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        
        if order.get("payment_status") == "paid":
            return {"success": True, "message": "Payment already processed", "order_id": order_id}
        
        # Process payment based on method
        if payment_method == "card":
            # Simulate card payment processing
            # In production, integrate with Stripe, PayPal, or other payment gateway
            card_number = payment_details.get("cardNumber", "")
            card_expiry = payment_details.get("cardExpiry", "")
            card_cvv = payment_details.get("cardCVV", "")
            card_name = payment_details.get("cardName", "")
            
            # Basic validation
            if not card_number or len(card_number) < 13:
                raise HTTPException(400, "Invalid card number")
            if not card_expiry or len(card_expiry) != 5:
                raise HTTPException(400, "Invalid expiry date")
            if not card_cvv or len(card_cvv) < 3:
                raise HTTPException(400, "Invalid CVV")
            if not card_name:
                raise HTTPException(400, "Cardholder name required")
            
            # Simulate payment processing (replace with real gateway API call)
            # For demo: accept any valid format
            payment_success = True
            payment_message = "Card payment processed successfully"
            
        elif payment_method == "gcash":
            # Process GCash payment via PayMongo or direct GCash API
            from payment_gateway import process_gcash_payment
            
            gcash_number = payment_details.get("gcashNumber", "")
            
            if not gcash_number or len(gcash_number) != 11:
                raise HTTPException(400, "Invalid GCash number. Please enter a valid 11-digit mobile number.")
            
            # Get order details for payment
            cur.execute("SELECT fullname, contact FROM orders WHERE id = %s", (order_id,))
            order_info = cur.fetchone()
            
            order_details = {
                "customer_name": order_info.get("fullname", "") if order_info else "",
                "customer_contact": order_info.get("contact", "") if order_info else "",
                "customer_email": "",
                "return_url": f"{os.getenv('APP_URL', 'https://your-app.onrender.com')}/orders.html",
                "callback_url": f"{os.getenv('APP_URL', 'https://your-app.onrender.com')}/payment/callback"
            }
            
            try:
                # Process GCash payment (direct GCash-to-GCash transfer)
                payment_result = process_gcash_payment(
                    order_id=order_id,
                    amount=float(amount),
                    gcash_number=gcash_number,
                    order_details=order_details,
                    use_direct=True  # Use direct GCash-to-GCash transfer to admin number
                )
                
                payment_success = payment_result.get("success", False)
                payment_message = payment_result.get("message", "GCash payment processed")
                payment_status = payment_result.get("status", "pending")
                payment_intent_id = payment_result.get("payment_intent_id")
                
                # Store payment intent ID if available (for status checking)
                if payment_intent_id:
                    cur.execute("""
                        UPDATE orders 
                        SET payment_status = %s, payment_method = %s, payment_intent_id = %s
                        WHERE id = %s
                    """, (payment_status, payment_method, payment_intent_id, order_id))
                    conn.commit()
                else:
                    # Update status without payment_intent_id
                    cur.execute("""
                        UPDATE orders 
                        SET payment_status = %s, payment_method = %s
                        WHERE id = %s
                    """, (payment_status, payment_method, order_id))
                    conn.commit()
                
                # If payment requires action (redirect to GCash)
                if payment_result.get("requires_action"):
                    return {
                        "success": False,
                        "requires_action": True,
                        "message": payment_message,
                        "redirect_url": payment_result.get("redirect_url"),
                        "payment_intent_id": payment_intent_id,
                        "order_id": order_id
                    }
                
                # Check if direct GCash transfer
                payment_type = payment_result.get("payment_type", "")
                if payment_type == "direct_gcash":
                    return {
                        "success": True,
                        "payment_type": "direct_gcash",
                        "message": payment_message,
                        "order_id": order_id,
                        "payment_method": payment_method,
                        "amount": amount,
                        "payment_intent_id": payment_intent_id,
                        "status": payment_status,
                        "admin_gcash_number": payment_result.get("admin_gcash_number", "09947784922"),
                        "reference": payment_result.get("reference", payment_intent_id),
                        "instructions": payment_result.get("instructions", ""),
                        "qr_data": payment_result.get("qr_data", "")
                    }
                
                # Return success response for GCash
                return {
                    "success": payment_success,
                    "message": payment_message,
                    "order_id": order_id,
                    "payment_method": payment_method,
                    "amount": amount,
                    "payment_intent_id": payment_intent_id,
                    "status": payment_status
                }
                
            except Exception as payment_error:
                print(f"[ERROR] GCash payment error: {payment_error}")
                import traceback
                traceback.print_exc()
                
                # If payment gateway is not configured, use demo mode
                if "not set" in str(payment_error) or "not configured" in str(payment_error) or "PAYMONGO" in str(payment_error):
                    # Demo mode - mark as pending
                    cur.execute("""
                        UPDATE orders 
                        SET payment_status = 'pending', payment_method = %s
                        WHERE id = %s
                    """, (payment_method, order_id))
                    conn.commit()
                    
                    return {
                        "success": True,
                        "message": "GCash payment request sent. Please confirm in your GCash app. (Demo mode - configure PayMongo API keys for real payments)",
                        "order_id": order_id,
                        "payment_method": payment_method,
                        "amount": amount,
                        "status": "pending",
                        "demo_mode": True
                    }
                else:
                    raise HTTPException(500, f"GCash payment failed: {str(payment_error)}")
            
        else:
            raise HTTPException(400, f"Unsupported payment method: {payment_method}")
        
        # Update order payment status (for card payments)
        if payment_success and payment_method == "card":
            cur.execute("""
                UPDATE orders 
                SET payment_status = 'paid', payment_method = %s
                WHERE id = %s
            """, (payment_method, order_id))
            conn.commit()
            
            return {
                "success": True,
                "message": payment_message,
                "order_id": order_id,
                "payment_method": payment_method,
                "amount": amount
            }
        else:
            # Payment failed
            cur.execute("""
                UPDATE orders 
                SET payment_status = 'failed'
                WHERE id = %s
            """, (order_id,))
            conn.commit()
            
            raise HTTPException(400, "Payment processing failed")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Payment processing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Payment processing failed: {str(e)}")
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
    # Ensure table exists first (this manages its own connection)
    try:
        ensure_menu_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure menu table exists: {e}")
        # Continue anyway, will try to query
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM menu_items ORDER BY category, name")
        items = cur.fetchall()
        # Always return a list, even if empty
        return items if items else []
    except psycopg2_errors.UndefinedTable as e:
        print(f"[WARNING] Table doesn't exist: {e}")
        # Try to create table one more time
        try:
            ensure_menu_table_exists()
            # Return empty list since table was just created
            return []
        except Exception as create_error:
            print(f"[ERROR] Table creation failed: {create_error}")
            # Return empty list instead of raising error to prevent frontend crashes
            return []
    except Exception as e:
        print(f"[ERROR] Get menu items error: {e}")
        error_msg = str(e)
        if "does not exist" in error_msg or "relation" in error_msg.lower():
            # Try to create table
            try:
                ensure_menu_table_exists()
                return []
            except:
                pass
        # Return empty list instead of raising error to prevent frontend crashes
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# --- Menu Items: Add new menu item (Admin only) ---
@app.post("/menu")
async def add_menu_item(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse request JSON: {e}")
        raise HTTPException(400, "Invalid JSON in request body")
    
    # Validate required fields
    name = data.get("name")
    price = data.get("price")
    
    if not name or not isinstance(name, str) or not name.strip():
        raise HTTPException(400, "Name is required and must be a non-empty string")
    
    if price is None:
        raise HTTPException(400, "Price is required")
    
    try:
        price = float(price)
        if price <= 0:
            raise HTTPException(400, "Price must be greater than 0")
    except (ValueError, TypeError):
        raise HTTPException(400, "Price must be a valid number")
    
    # Ensure table exists first
    try:
        ensure_menu_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure menu table exists: {e}")
        # Continue anyway, will try to insert
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Ensure all required columns exist (this should have been done by ensure_menu_table_exists, but double-check)
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'menu_items'
        """)
        existing_columns = [row.get('column_name') if isinstance(row, dict) else row[0] for row in cur.fetchall()]
        
        # If category is missing, add it now
        if 'category' not in existing_columns:
            print("[WARNING] category column missing, adding it now...")
            cur.execute("ALTER TABLE menu_items ADD COLUMN category TEXT NOT NULL DEFAULT 'foods';")
            conn.commit()
            existing_columns.append('category')
        
        category = data.get("category", "foods")
        is_available = data.get("is_available", True)
        quantity = data.get("quantity", 0)
        if quantity is None:
            quantity = 0
        
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 0
        
        # Build INSERT statement based on available columns
        has_quantity = 'quantity' in existing_columns
        
        if has_quantity:
            cur.execute("""
                INSERT INTO menu_items (name, price, category, is_available, quantity)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (
                name.strip(),
                price,
                category,
                is_available,
                quantity
            ))
        else:
            # Table doesn't have quantity column, insert without it
            cur.execute("""
                INSERT INTO menu_items (name, price, category, is_available)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (
                name.strip(),
                price,
                category,
                is_available
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
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise
    except psycopg2_errors.IntegrityError as e:
        print(f"[ERROR] Database integrity error: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # Check for common integrity errors
        if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
            raise HTTPException(400, "A menu item with this name already exists")
        raise HTTPException(400, f"Database constraint error: {error_msg}")
    except psycopg2_errors.ProgrammingError as e:
        print(f"[ERROR] Database programming error: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # Check if it's a column error
        if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
            # Try to add missing column and retry
            try:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    conn.close()
                # Add quantity column if missing
                ensure_menu_table_exists()  # This should add missing columns
                # Retry insert
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO menu_items (name, price, category, is_available, quantity)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    name.strip(),
                    price,
                    category,
                    is_available,
                    quantity
                ))
                conn.commit()
                result = cur.fetchone()
                conn.close()
                return {"ok": True, "message": "Menu item added successfully", "item": result}
            except Exception as retry_error:
                print(f"[ERROR] Retry after column fix failed: {retry_error}")
                import traceback
                traceback.print_exc()
                raise HTTPException(500, f"Failed to add menu item. Please check table structure. Error: {str(retry_error)}")
        raise HTTPException(500, f"Database error: {error_msg}")
    except Exception as e:
        print(f"[ERROR] Add menu item error: {e}")
        print(f"[ERROR] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        
        # Check for table not found errors
        if "does not exist" in error_msg or "relation" in error_msg.lower() or "UndefinedTable" in str(type(e)):
            # Try to create table and retry
            try:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    conn.close()
                ensure_menu_table_exists()
                # Retry with new connection
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO menu_items (name, price, category, is_available, quantity)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    name.strip(),
                    price,
                    category,
                    is_available,
                    quantity
                ))
                conn.commit()
                result = cur.fetchone()
                conn.close()
                return {"ok": True, "message": "Menu item added successfully", "item": result}
            except Exception as retry_error:
                print(f"[ERROR] Retry after table creation failed: {retry_error}")
                import traceback
                traceback.print_exc()
                raise HTTPException(500, f"Failed to add menu item after table creation. Error: {str(retry_error)}")
        
        # For other errors, provide a more helpful message
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
        
        # Check if order exists and get current status and user_id
        cur.execute("SELECT status, user_id, items FROM orders WHERE id=%s", (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        # Get order data (handle both dict and tuple responses)
        if isinstance(order, dict):
            current_status = order.get("status")
            order_user_id = order.get("user_id")
            old_items = order.get("items")
        else:
            current_status = order[0] if len(order) > 0 else None
            order_user_id = order[1] if len(order) > 1 else None
            old_items = order[2] if len(order) > 2 else None
        
        # If user_id is provided, verify ownership (for user edits)
        user_id = data.get("user_id")
        if user_id is not None:
            if order_user_id != user_id:
                raise HTTPException(403, "You can only edit your own orders")
        
        # If updating order details (not just status), check if order is Pending
        if "fullname" in data or "contact" in data or "location" in data or "items" in data or "total" in data:
            if current_status != "Pending":
                raise HTTPException(400, f"Cannot edit order. Only orders with 'Pending' status can be edited. Current status: {current_status}")
            
            # Handle stock updates if items are being changed
            if "items" in data:
                # Restore stock from old items
                if old_items:
                    try:
                        old_items_list = json.loads(old_items) if isinstance(old_items, str) else old_items
                        for item in old_items_list:
                            item_id = item.get("id")
                            qty_ordered = item.get("qty", 0)
                            if item_id and qty_ordered > 0:
                                try:
                                    cur.execute("SELECT quantity FROM menu_items WHERE id = %s", (item_id,))
                                    result = cur.fetchone()
                                    if result:
                                        current_qty = result.get("quantity") if isinstance(result, dict) else (result[0] if result else 0)
                                        new_qty = current_qty + qty_ordered  # Restore
                                        cur.execute("UPDATE menu_items SET quantity = %s WHERE id = %s", (new_qty, item_id))
                                        if current_qty == 0 and new_qty > 0:
                                            cur.execute("UPDATE menu_items SET is_available = TRUE WHERE id = %s", (item_id,))
                                except Exception as stock_error:
                                    print(f"[WARNING] Could not restore stock for item {item_id}: {stock_error}")
                    except Exception as items_error:
                        print(f"[WARNING] Could not parse old items for stock restoration: {items_error}")
                
                # Deduct stock for new items
                new_items = data.get("items", [])
                for item in new_items:
                    item_id = item.get("id")
                    qty_ordered = item.get("qty", 0)
                    if item_id and qty_ordered > 0:
                        try:
                            cur.execute("SELECT quantity FROM menu_items WHERE id = %s", (item_id,))
                            result = cur.fetchone()
                            if result:
                                current_qty = result.get("quantity") if isinstance(result, dict) else (result[0] if result else 0)
                                new_qty = max(0, current_qty - qty_ordered)  # Deduct
                                cur.execute("UPDATE menu_items SET quantity = %s WHERE id = %s", (new_qty, item_id))
                                if new_qty == 0:
                                    cur.execute("UPDATE menu_items SET is_available = FALSE WHERE id = %s", (item_id,))
                        except Exception as stock_error:
                            print(f"[WARNING] Could not update stock for item {item_id}: {stock_error}")
            
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

# --- Delete/Cancel order (Users can cancel their own, Admins can cancel any) ---
@app.delete("/orders/{oid}")
async def delete_order(oid: int, request: Request):
    # Try to get user_id from request body if provided (for user cancellations)
    user_id = None
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.body()
            if body:
                data = json.loads(body.decode())
                user_id = data.get("user_id")
    except:
        pass  # If no body or parsing fails, user_id remains None (admin cancellation)
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if order exists and get full order data (including items and user_id)
        cur.execute("SELECT id, status, items, user_id FROM orders WHERE id=%s", (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        # Get order data (handle both dict and tuple responses)
        if isinstance(order, dict):
            order_status = order.get("status")
            order_items = order.get("items")
            order_user_id = order.get("user_id")
        else:
            order_status = order[1] if len(order) > 1 else None
            order_items = order[2] if len(order) > 2 else None
            order_user_id = order[3] if len(order) > 3 else None
        
        # Only allow cancellation if status is Pending
        if order_status != "Pending":
            raise HTTPException(400, f"Cannot cancel order. Only orders with 'Pending' status can be cancelled. Current status: {order_status}")
        
        # If user_id is provided, verify the order belongs to that user
        # (This allows users to cancel their own orders, admins can cancel any by not providing user_id)
        if user_id is not None:
            if order_user_id != user_id:
                raise HTTPException(403, "You can only cancel your own orders")
        
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

# --- Admin: Get all users ---
@app.get("/users")
def get_users():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, role, is_approved, id_proof, selfie_proof FROM users ORDER BY id DESC")
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Get users error: {e}")
        raise HTTPException(500, f"Failed to get users: {str(e)}")
    finally:
        conn.close()

# --- Admin: Approve/Reject user and set role ---
@app.put("/users/{user_id}/approve")
async def approve_user(user_id: int, request: Request):
    data = await request.json()
    is_approved = data.get("is_approved", True)
    new_role = data.get("role")  # Optional: 'admin' or 'user'
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, role FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        # Get current role
        if isinstance(user, dict):
            current_role = user.get("role")
        else:
            current_role = user[1] if len(user) > 1 else None
        
        # Don't allow changing the first admin's role
        if current_role == 'admin':
            # Check if this is the first user (lowest ID with admin role)
            cur.execute("SELECT MIN(id) as first_admin_id FROM users WHERE role='admin'")
            first_admin_result = cur.fetchone()
            first_admin_id = first_admin_result.get('first_admin_id') if isinstance(first_admin_result, dict) else (first_admin_result[0] if first_admin_result else None)
            
            if user_id == first_admin_id:
                raise HTTPException(400, "Cannot modify the first admin account")
        
        # Build update query
        updates = []
        params = []
        
        if "is_approved" in data:
            updates.append("is_approved = %s")
            params.append(is_approved)
        
        if new_role and new_role in ['admin', 'user']:
            updates.append("role = %s")
            params.append(new_role)
        
        if not updates:
            raise HTTPException(400, "No fields to update")
        
        # If rejecting a user (is_approved = False), delete them from database completely
        if "is_approved" in data and is_approved == False:
            # Always attempt to delete rejected users
            try:
                # First, delete all orders associated with this user (if any)
                # This handles foreign key constraints
                try:
                    cur.execute("DELETE FROM orders WHERE user_id = %s", (user_id,))
                    deleted_orders = cur.rowcount
                    if deleted_orders > 0:
                        print(f"[INFO] Deleted {deleted_orders} order(s) for user {user_id}")
                except Exception as orders_delete_error:
                    print(f"[WARNING] Could not delete orders for user {user_id}: {orders_delete_error}")
                    # Continue with user deletion attempt anyway
                
                # Now delete the user
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                
                if cur.rowcount > 0:
                    print(f"[INFO] User {user_id} rejected and deleted successfully from database")
                    return {"ok": True, "message": f"User rejected and removed from database successfully", "deleted": True}
                else:
                    print(f"[WARNING] User {user_id} not found or already deleted")
                    raise HTTPException(404, f"User {user_id} not found")
                    
            except HTTPException:
                raise
            except Exception as delete_error:
                print(f"[ERROR] Failed to delete user {user_id}: {delete_error}")
                import traceback
                traceback.print_exc()
                # If deletion fails, try to at least mark as rejected as fallback
                # But this should rarely happen
                try:
                    params.append(user_id)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING *"
                    cur.execute(query, params)
                    conn.commit()
                    result = cur.fetchone()
                    print(f"[WARNING] User {user_id} could not be deleted, marked as rejected instead")
                    return {"ok": True, "message": f"User rejected (deletion attempted but failed, marked as rejected)", "deleted": False, "user": result}
                except Exception as fallback_error:
                    print(f"[ERROR] Fallback rejection also failed: {fallback_error}")
                    raise HTTPException(500, f"Failed to reject user: {str(delete_error)}")
        else:
            # Approving user - normal update
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING *"
            cur.execute(query, params)
            conn.commit()
            result = cur.fetchone()
        
        role_msg = f" as {new_role}" if new_role else ""
        return {"ok": True, "message": f"User {'approved' if is_approved else 'rejected'}{role_msg} successfully", "user": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Approve user error: {e}")
        raise HTTPException(500, f"Failed to update user approval: {str(e)}")
    finally:
        conn.close()

# --- Reset: Delete all users (for development/testing) ---
@app.delete("/reset/users")
async def reset_all_users():
    """
    WARNING: This endpoint deletes ALL users and orders from the database.
    Use with caution! Only for development/testing.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Delete orders first (they reference users via foreign key)
        cur.execute("DELETE FROM orders")
        orders_deleted = cur.rowcount
        # Then delete all users
        cur.execute("DELETE FROM users")
        users_deleted = cur.rowcount
        conn.commit()
        return {"ok": True, "message": f"Deleted {orders_deleted} order(s) and {users_deleted} user(s). You can now register as the first admin."}
    except Exception as e:
        print(f"Reset users error: {e}")
        raise HTTPException(500, f"Failed to reset users: {str(e)}")
    finally:
        conn.close()
