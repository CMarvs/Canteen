from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
import psycopg2, json
from psycopg2.extras import RealDictCursor
from psycopg2 import errors as psycopg2_errors
from decimal import Decimal
from datetime import datetime, date
import os

app = FastAPI()

# Security and Performance Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Add security and performance headers to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Ensure Cache-Control is set (use existing or set default)
        # For static files, allow caching; for dynamic content, no-cache
        request_path = str(request.url.path)
        if "/static/" in request_path:
            if "Cache-Control" not in response.headers or not response.headers.get("Cache-Control"):
                response.headers["Cache-Control"] = "public, max-age=3600"  # Cache static files for 1 hour
        else:
            if "Cache-Control" not in response.headers or not response.headers.get("Cache-Control"):
                response.headers["Cache-Control"] = "no-cache"
        # Ensure Content-Type has charset=utf-8 for text/html and application/json
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type and "charset" not in content_type.lower():
            response.headers["Content-Type"] = "text/html; charset=utf-8"
        elif "application/json" in content_type and "charset" not in content_type.lower():
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response

# Helper function to serialize datetime and Decimal objects for JSON
def serialize_datetime(obj):
    """Recursively convert datetime and Decimal objects to JSON-serializable types"""
    # Handle Decimal types (from PostgreSQL numeric fields)
    if isinstance(obj, Decimal):
        return float(obj)
    # Handle datetime objects
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        # Handle RealDictRow and similar dict-like objects
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_datetime(item) for item in obj]
    return obj

# Helper function to create JSONResponse with proper headers
def json_response(content, status_code=200):
    """Create a JSONResponse with proper Content-Type charset and security headers"""
    # Serialize datetime objects before creating JSON response
    content = serialize_datetime(content)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff"
    }
    return JSONResponse(content=content, status_code=status_code, headers=headers)

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

# Add security headers middleware (runs after CORS to ensure headers are set)
app.add_middleware(SecurityHeadersMiddleware)

# NeonDB connection - use environment variable or fallback to default
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y2KOWuHn9DMU@ep-lingering-tooth-a1kqy37g-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.OperationalError as e:
        error_str = str(e)
        print(f"❌ Database connection error: {e}")
        
        # Check for quota exceeded error
        if "exceeded the data transfer quota" in error_str or "quota" in error_str.lower():
            error_message = "Database quota exceeded. Please upgrade your NeonDB plan at https://neon.tech or wait for quota reset. The database has reached its data transfer limit for this billing period."
            raise HTTPException(status_code=503, detail=error_message)
        
        print(f"[ERROR] Failed to connect to database. Check DATABASE_URL environment variable.")
        raise HTTPException(500, f"Database connection failed: {str(e)}")
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Initialize chat_messages table if it doesn't exist ---
def ensure_chat_table_exists():
    """
    Ensure chat_messages table exists
    Returns True if successful, False if database connection failed
    """
    try:
        conn = get_db_connection()
    except Exception as conn_error:
        # Database connection failed - don't crash, just return False
        print(f"[WARNING] Could not connect to database for chat table check: {conn_error}")
        return False
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chat_messages'
            ) as exists;
        """)
        result = cur.fetchone()
        table_exists = result.get('exists') if isinstance(result, dict) else (result[0] if result else False)
        
        if not table_exists:
            print("[INFO] Creating chat_messages table...")
            cur.execute("""
                CREATE TABLE chat_messages (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    sender_role TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    image TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    read_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_order_id ON chat_messages(order_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages(created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_is_read ON chat_messages(is_read);")
            conn.commit()
            print("[SUCCESS] chat_messages table created successfully!")
        else:
            print("[INFO] chat_messages table already exists")
            # Check and add image column if missing
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='chat_messages' AND column_name='image'
                """)
                image_col_exists = cur.fetchone()
                if not image_col_exists:
                    print("[INFO] Adding image column to chat_messages table...")
                    cur.execute("ALTER TABLE chat_messages ADD COLUMN image TEXT;")
                    conn.commit()
            except Exception as img_error:
                print(f"[WARNING] Could not check/add image column: {img_error}")
            
            # Check and add is_read column if missing
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_messages' AND column_name = 'is_read'
                """)
                has_is_read = cur.fetchone()
                if not has_is_read:
                    print("[INFO] Adding is_read and read_at columns to chat_messages table...")
                    cur.execute("ALTER TABLE chat_messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE chat_messages ADD COLUMN read_at TIMESTAMP;")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_is_read ON chat_messages(is_read);")
                    conn.commit()
                    print("[SUCCESS] is_read and read_at columns added successfully!")
            except Exception as col_error:
                print(f"[WARNING] Could not check/add is_read column: {col_error}")
    except Exception as e:
        print(f"[ERROR] Error ensuring chat table exists: {e}")
        conn.rollback()
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Initialize users table if it doesn't exist ---
def ensure_users_table_exists():
    """
    Ensure users table exists with all required columns
    Returns True if successful, False if database connection failed
    """
    try:
        conn = get_db_connection()
    except Exception as conn_error:
        print(f"[WARNING] Could not connect to database for users table check: {conn_error}")
        return False
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            ) as exists;
        """)
        result = cur.fetchone()
        table_exists = result.get('exists') if isinstance(result, dict) else (result[0] if result else False)
        
        if not table_exists:
            print("[INFO] Creating users table...")
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    id_proof TEXT,
                    selfie_proof TEXT,
                    is_approved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
            print("[SUCCESS] users table created successfully!")
        else:
            print("[INFO] users table already exists")
            # Check and add missing columns
            try:
                # Get all existing columns
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                """)
                existing_columns = [row.get('column_name') if isinstance(row, dict) else row[0] for row in cur.fetchall()]
                
                # Check and add id_proof column if missing
                if 'id_proof' not in existing_columns:
                    print("[INFO] Adding id_proof column to users table...")
                    cur.execute("ALTER TABLE users ADD COLUMN id_proof TEXT;")
                    conn.commit()
                    print("[SUCCESS] id_proof column added successfully!")
                
                # Check and add selfie_proof column if missing
                if 'selfie_proof' not in existing_columns:
                    print("[INFO] Adding selfie_proof column to users table...")
                    cur.execute("ALTER TABLE users ADD COLUMN selfie_proof TEXT;")
                    conn.commit()
                    print("[SUCCESS] selfie_proof column added successfully!")
                
                # Check and add is_approved column if missing
                if 'is_approved' not in existing_columns:
                    print("[INFO] Adding is_approved column to users table...")
                    cur.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;")
                    # Set existing users (except admin) as approved
                    cur.execute("UPDATE users SET is_approved = TRUE WHERE role != 'admin' OR role IS NULL;")
                    conn.commit()
                    print("[SUCCESS] is_approved column added successfully!")
                
                # Check and add created_at column if missing
                if 'created_at' not in existing_columns:
                    print("[INFO] Adding created_at column to users table...")
                    cur.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT NOW();")
                    conn.commit()
                    print("[SUCCESS] created_at column added successfully!")
                    
            except Exception as col_error:
                print(f"[WARNING] Could not check/add columns: {col_error}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] Error ensuring users table exists: {e}")
        conn.rollback()
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Initialize service_ratings table if it doesn't exist ---
def ensure_ratings_table_exists():
    """
    Ensure service_ratings table exists
    Returns True if successful, False if database connection failed
    """
    try:
        conn = get_db_connection()
    except Exception as conn_error:
        # Database connection failed - don't crash, just return False
        print(f"[WARNING] Could not connect to database for ratings table check: {conn_error}")
        return False
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'service_ratings'
            ) as exists;
        """)
        result = cur.fetchone()
        table_exists = result.get('exists') if isinstance(result, dict) else (result[0] if result else False)
        
        if not table_exists:
            print("[INFO] Creating service_ratings table...")
            cur.execute("""
                CREATE TABLE service_ratings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON service_ratings(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ratings_created_at ON service_ratings(created_at);")
            conn.commit()
            print("[SUCCESS] service_ratings table created successfully!")
        else:
            print("[INFO] service_ratings table already exists")
    except Exception as e:
        print(f"[ERROR] Error ensuring ratings table exists: {e}")
        conn.rollback()
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# Initialize table on startup (non-blocking)
# This runs on import, so we need to be very careful not to crash the server
try:
    # Only initialize if we can connect to database
    # Don't fail server startup if database is temporarily unavailable
    try:
        ensure_users_table_exists()
        ensure_users_table_exists()
        ensure_menu_table_exists()
        ensure_chat_table_exists()
        ensure_ratings_table_exists()
    except Exception as db_error:
        # Database connection errors shouldn't crash the server
        print(f"[WARNING] Could not initialize tables on startup: {db_error}")
        print("[INFO] The tables will be created automatically when needed.")
        print("[INFO] Server will continue to start. Database will be connected on first request.")
except Exception as e:
    # Catch any other unexpected errors during startup
    print(f"[WARNING] Unexpected error during startup initialization: {e}")
    import traceback
    traceback.print_exc()
    print("[INFO] Server will continue to start. Tables will be created when needed.")

# --- Safe FileResponse helper ---
def safe_file_response(path: str):
    try:
        full_path = os.path.abspath(path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Add aggressive no-cache headers to prevent browser and CDN caching
            headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT"
            }
            return HTMLResponse(content=content, headers=headers)
        else:
            print(f"❌ File not found: {full_path}")
            return json_response({"error": "File not found", "path": path}, status_code=404)
    except Exception as e:
        print(f"❌ Error serving file {path}: {e}")
        import traceback
        traceback.print_exc()
        return json_response({"error": str(e)}, status_code=500)

# Routes
@app.get("/")
def home():
    try:
        return safe_file_response("templates/home.html")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return json_response({"error": f"Failed to serve home page: {str(e)}"}, status_code=500)
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
    try:
        data = await request.json()
    except Exception as json_error:
        print(f"❌ Registration JSON parse error: {json_error}")
        raise HTTPException(400, "Invalid request data")
    
    # Validate required fields
    if not data.get("name") or not data.get("email") or not data.get("password"):
        raise HTTPException(400, "Name, email, and password are required")
    
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
        
        # Validate required fields
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        
        if not name or not name.strip():
            raise HTTPException(400, "Name is required")
        if not email or not email.strip():
            raise HTTPException(400, "Email is required")
        if not password or not password.strip():
            raise HTTPException(400, "Password is required")
        if len(password.strip()) < 4:
            raise HTTPException(400, "Password must be at least 4 characters")
        
        # Normalize email
        email = email.strip().lower()
        password = password.strip()
        name = name.strip()
        
        # Check if email already exists (case-insensitive)
        cur.execute("SELECT 1 FROM users WHERE LOWER(email)=%s", (email,))
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
            (name, email, password, user_role, id_proof, selfie_proof, is_approved)
        )
        conn.commit()
        print(f"[INFO] User registered: {email} (Role: {user_role}, Approved: {is_approved})")
        return {"ok": True, "message": message}
    except HTTPException as http_ex:
        print(f"[ERROR] HTTPException in registration: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Registration failed: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except:
            pass

# --- Login ---
@app.post("/login")
async def login(request: Request):
    try:
        data = await request.json()
    except Exception as json_error:
        print(f"❌ Login JSON parse error: {json_error}")
        raise HTTPException(400, "Invalid request data")
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    
    if not email or not password:
        raise HTTPException(400, "Email and password are required")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # First, try to find user by email (case-insensitive)
        cur.execute(
            "SELECT * FROM users WHERE LOWER(email)=%s",
            (email,)
        )
        user = cur.fetchone()
        
        if not user:
            print(f"[WARNING] Login attempt failed: Email '{email}' not found in database")
            # Check if similar emails exist (for debugging)
            cur.execute("SELECT email FROM users WHERE email ILIKE %s LIMIT 5", (f"%{email.split('@')[0]}%",))
            similar = cur.fetchall()
            if similar:
                print(f"[DEBUG] Similar emails found: {[s.get('email') if isinstance(s, dict) else s[0] for s in similar]}")
            raise HTTPException(400, "Invalid email or password. If you haven't registered yet, please register first.")
        
        # Convert to dict if needed
        if not isinstance(user, dict):
            col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
            user = dict(zip(col_names, user)) if col_names else {}
        
        # Check password - handle None, empty strings, and whitespace
        stored_password = user.get('password') or ''
        stored_password = str(stored_password).strip()
        password = password.strip()
        
        print(f"[DEBUG] Password check - Stored: '{stored_password[:10]}...' (len={len(stored_password)}), Provided: '{password[:10]}...' (len={len(password)})")
        
        if not stored_password or stored_password != password:
            print(f"[WARNING] Login attempt failed: Incorrect password for '{email}'")
            print(f"[DEBUG] Password mismatch - stored length: {len(stored_password)}, provided length: {len(password)}")
            # Don't log actual passwords, but show first/last chars for debugging
            if stored_password:
                print(f"[DEBUG] Stored password starts with: '{stored_password[:2]}...' (length: {len(stored_password)})")
            if password:
                print(f"[DEBUG] Provided password starts with: '{password[:2]}...' (length: {len(password)})")
            raise HTTPException(400, "Invalid email or password. Please check your password and try again.")
        
        print(f"[INFO] Password verified for user: {email}")
        
        # Check if user is approved (admin accounts are always approved)
        # User is already a dict at this point
        role = user.get("role")
        is_approved = user.get("is_approved")
        user_id = user.get("id")
        
        print(f"[INFO] User found: ID={user_id}, Email={email}, Role={role}, Approved={is_approved}")
        
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
            # Ensure user is a dict before returning
            if not isinstance(user, dict):
                col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                user = dict(zip(col_names, user)) if col_names else {}
            
            # Ensure all required fields are present
            if not user.get('id') or not user.get('email') or not user.get('role'):
                print(f"❌ Login: Missing required fields in admin user data: {user}")
                raise HTTPException(500, "Invalid user data returned from database")
            
            # Remove sensitive data
            user.pop('password', None)
            user.pop('id_proof', None)
            user.pop('selfie_proof', None)
            
            print(f"[INFO] Admin login successful: {user.get('email')} (ID: {user.get('id')})")
            print(f"[INFO] Returning user data: {user}")
            
            # Ensure we return a proper dict (not RealDictRow)
            response_data = dict(user)
            return response_data
        
        # Regular users need approval
        if is_approved is False or is_approved == 0 or is_approved is None:
            print(f"[WARNING] Login blocked: User '{email}' is not approved")
            raise HTTPException(403, "Account pending admin approval. Please wait for approval.")
        
        # User is already a dict, ensure all required fields are present
        if not user.get('id') or not user.get('email') or not user.get('role'):
            print(f"❌ Login: Missing required fields in user data: {user}")
            raise HTTPException(500, "Invalid user data returned from database")
        
        # Remove sensitive data before returning
        user.pop('password', None)
        user.pop('id_proof', None)
        user.pop('selfie_proof', None)
        
        print(f"[INFO] User login successful: {user.get('email')} (ID: {user.get('id')}, Role: {user.get('role')})")
        print(f"[INFO] Returning user data: {user}")
        
        # Ensure we return a proper dict (not RealDictRow) - convert to regular dict
        response_data = dict(user)
        return response_data
    except HTTPException as http_ex:
        print(f"[ERROR] HTTPException in login: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Login failed: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection in login: {close_error}")

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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        # COD orders are automatically marked as paid (payment on delivery)
        if payment_method == "cod":
            payment_status = "paid"
        else:
            payment_status = data.get("payment_status", "pending")
        
        # Get payment proof if provided (for GCash payments)
        payment_proof = None
        payment_details = data.get("payment_details", {})
        if payment_method == "gcash" and payment_details:
            payment_proof = payment_details.get("payment_proof")
        
        # Check if payment_proof column exists before inserting
        # This check happens right before the insert to ensure accuracy
        payment_proof_exists = False
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'payment_proof'
            """)
            payment_proof_exists = cur.fetchone() is not None
            
            # If column doesn't exist, try to add it
            if not payment_proof_exists:
                print("[INFO] payment_proof column not found, adding it...")
                cur.execute("ALTER TABLE orders ADD COLUMN payment_proof TEXT;")
                conn.commit()
                payment_proof_exists = True
                print("[INFO] payment_proof column added successfully")
        except Exception as check_error:
            print(f"[WARNING] Could not check/add payment_proof column: {check_error}")
            # Assume column doesn't exist and proceed without it
            payment_proof_exists = False
        
        # Try to insert with payment_proof, but handle case where column might not exist
        try:
            if payment_proof_exists:
                # Insert order with payment information and proof
                cur.execute("""
                    INSERT INTO orders(user_id,fullname,contact,location,items,total,payment_method,payment_status,payment_proof)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING *;
                """, (
                    data.get("user_id"), data.get("fullname"), data.get("contact"),
                    data.get("location"), json.dumps(items), data.get("total"),
                    payment_method, payment_status, payment_proof
                ))
            else:
                # Insert without payment_proof if column doesn't exist
                print("[WARNING] payment_proof column does not exist, inserting without it...")
                cur.execute("""
                    INSERT INTO orders(user_id,fullname,contact,location,items,total,payment_method,payment_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING *;
                """, (
                    data.get("user_id"), data.get("fullname"), data.get("contact"),
                    data.get("location"), json.dumps(items), data.get("total"),
                    payment_method, payment_status
                ))
        except psycopg2_errors.UndefinedColumn as col_error:
            # If payment_proof column doesn't exist, try to add it and retry
            if 'payment_proof' in str(col_error):
                print("[WARNING] payment_proof column missing, attempting to add it...")
                try:
                    cur.execute("ALTER TABLE orders ADD COLUMN payment_proof TEXT;")
                    conn.commit()
                    print("[INFO] payment_proof column added, retrying insert...")
                    # Retry the insert
                    cur.execute("""
                        INSERT INTO orders(user_id,fullname,contact,location,items,total,payment_method,payment_status,payment_proof)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING *;
                    """, (
                        data.get("user_id"), data.get("fullname"), data.get("contact"),
                        data.get("location"), json.dumps(items), data.get("total"),
                        payment_method, payment_status, payment_proof
                    ))
                except Exception as retry_error:
                    print(f"[ERROR] Failed to add payment_proof column or retry insert: {retry_error}")
                    # Fallback: insert without payment_proof
                    cur.execute("""
                        INSERT INTO orders(user_id,fullname,contact,location,items,total,payment_method,payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING *;
                    """, (
                        data.get("user_id"), data.get("fullname"), data.get("contact"),
                        data.get("location"), json.dumps(items), data.get("total"),
                        payment_method, payment_status
                    ))
            else:
                raise  # Re-raise if it's a different column error
        result = cur.fetchone()
        conn.commit()
        return {"ok": True, "message": "Order placed successfully", "order": result}
    except Exception as e:
        print(f"[ERROR] Order placement error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Order placement failed: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
    
    if not payment_method or not amount:
        raise HTTPException(400, "Missing required payment information")
    
    # For GCash, order_id may be null if order hasn't been created yet
    # Order will be created after payment proof is uploaded
    if payment_method == "gcash" and not order_id:
        # Generate payment info without order (for pre-order payment setup)
        from payment_gateway import generate_gcash_payment_link
        import random
        import string
        
        # Generate a temporary reference number
        temp_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        reference = f"ORDER_PENDING_{temp_ref}"
        
        admin_gcash = os.getenv("ADMIN_GCASH_NUMBER", "09947784922")
        gcash_number = payment_details.get("gcashNumber", "")
        
        if not gcash_number or len(gcash_number) != 11:
            raise HTTPException(400, "Invalid GCash number. Please enter a valid 11-digit mobile number.")
        
        # Get static QR code URL
        qr_code_url = os.getenv("GCASH_QR_CODE_URL", "/static/gcash-qr.jpg")
        
        # Generate payment info with static QR code
        payment_info = generate_gcash_payment_link(
            amount=float(amount),
            reference=reference,
            admin_number=admin_gcash,
            qr_code_url=qr_code_url
        )
        
        # Return payment info for modal (order will be created later)
        return {
            "success": True,
            "payment_type": "direct_gcash",
            "admin_gcash_number": admin_gcash,
            "amount": amount,
            "reference": reference,
            "payment_intent_id": reference,
            "qr_code_url": payment_info.get("qr_code_url", qr_code_url),  # Static QR code image URL
            "instructions": payment_info.get("instructions", "")
        }
    
    if not order_id:
        raise HTTPException(400, "Order ID is required for this payment method")
    
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
        if payment_method == "cod":
            # Cash on Delivery - payment is done on delivery, mark as paid
            payment_success = True
            payment_message = "Cash on Delivery - Payment will be collected on delivery"
            
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
                # QR code URL - use environment variable or default path
                qr_code_url = os.getenv("GCASH_QR_CODE_URL", "/static/gcash-qr.jpg")
                
                # Process GCash payment (direct GCash-to-GCash transfer)
                payment_result = process_gcash_payment(
                    order_id=order_id,
                    amount=float(amount),
                    gcash_number=gcash_number,
                    order_details=order_details,
                    use_direct=True,  # Use direct GCash-to-GCash transfer to admin number
                    qr_code_url=qr_code_url  # Pass QR code URL
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
                        "qr_data": payment_result.get("qr_data", ""),
                        "qr_code_url": payment_result.get("qr_code_url", "/static/gcash-qr.jpg")  # Static QR code image
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
        
        # Update order payment status (for COD payments)
        if payment_success and payment_method == "cod":
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
                "amount": amount,
                "status": "paid"
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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Admin: Get orders ---
@app.get("/orders")
async def get_orders():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check which columns exist in the orders table
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders'
        """)
        existing_columns = [row.get('column_name') if isinstance(row, dict) else row[0] for row in cur.fetchall()]
        existing_columns_set = set(existing_columns)
        
        # Build SELECT query with only existing columns
        base_columns = ['id', 'user_id', 'fullname', 'contact', 'location', 'items', 'total', 'status', 'created_at']
        optional_columns = ['payment_method', 'payment_status', 'payment_proof', 'payment_intent_id', 'refund_status']
        
        select_columns = [col for col in base_columns if col in existing_columns_set]
        select_columns.extend([col for col in optional_columns if col in existing_columns_set])
        
        # Optimized query - only select columns that exist
        # Use index-friendly ordering and limit for performance
        query = f"""
            SELECT {', '.join(select_columns)}
            FROM orders
            ORDER BY id DESC
            LIMIT 500
        """
        cur.execute(query)
        orders = cur.fetchall()
        
        # Convert RealDictRow to plain dict for JSON serialization
        orders_list = []
        if orders:
            for order in orders:
                # RealDictCursor returns dict-like objects, convert to plain dict
                if hasattr(order, 'keys'):
                    # RealDictRow or similar dict-like object - convert recursively
                    order_dict = {}
                    for key in order.keys():
                        value = order[key]
                        # Recursively serialize the value to handle nested objects
                        order_dict[key] = serialize_datetime(value)
                elif isinstance(order, dict):
                    # Already a dict, but still need to serialize nested values
                    order_dict = {k: serialize_datetime(v) for k, v in order.items()}
                else:
                    # Handle tuple response (shouldn't happen with RealDictCursor, but just in case)
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else []
                    if col_names:
                        order_dict = {col: serialize_datetime(order[i]) for i, col in enumerate(col_names)}
                    else:
                        # Fallback: create dict from tuple indices
                        order_dict = {
                            'id': serialize_datetime(order[0]) if len(order) > 0 else None,
                            'user_id': serialize_datetime(order[1]) if len(order) > 1 else None,
                            'fullname': serialize_datetime(order[2]) if len(order) > 2 else None,
                            'contact': serialize_datetime(order[3]) if len(order) > 3 else None,
                            'location': serialize_datetime(order[4]) if len(order) > 4 else None,
                            'items': serialize_datetime(order[5]) if len(order) > 5 else None,
                            'total': serialize_datetime(order[6]) if len(order) > 6 else None,
                            'status': serialize_datetime(order[7]) if len(order) > 7 else None,
                            'created_at': serialize_datetime(order[8]) if len(order) > 8 else None,
                            'payment_method': serialize_datetime(order[9]) if len(order) > 9 else None,
                            'payment_status': serialize_datetime(order[10]) if len(order) > 10 else None,
                        }
                
                # Add default values for missing payment columns to prevent frontend errors
                if 'payment_method' not in order_dict:
                    order_dict['payment_method'] = 'cash'
                if 'payment_status' not in order_dict:
                    order_dict['payment_status'] = 'pending'
                if 'payment_proof' not in order_dict:
                    order_dict['payment_proof'] = None
                if 'payment_intent_id' not in order_dict:
                    order_dict['payment_intent_id'] = None
                if 'refund_status' not in order_dict:
                    order_dict['refund_status'] = None
                
                orders_list.append(order_dict)
        
        print(f"[DEBUG] Returning {len(orders_list)} orders")
        return json_response(orders_list)
    except Exception as e:
        print(f"❌ Get orders error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        # Optimized query - only select needed columns
        cur.execute("""
            SELECT id, name, price, category, is_available, quantity, created_at
            FROM menu_items 
            ORDER BY category, name
        """)
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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Admin: Process Refund ---
@app.post("/orders/{order_id}/refund")
async def process_refund(order_id: int, request: Request):
    """Process a refund for an order and notify the user"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Check if refund_status column exists, if not add it
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'refund_status'
            """)
            has_refund_status = cur.fetchone() is not None
            
            if not has_refund_status:
                print("[INFO] Adding refund_status column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN refund_status TEXT DEFAULT NULL;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add refund_status column: {col_error}")
        
        # Get order details
        cur.execute("SELECT id, user_id, total, status, refund_status FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        
        if not order:
            raise HTTPException(404, "Order not found")
        
        # Convert to dict if needed
        if not isinstance(order, dict):
            col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
            order = dict(zip(col_names, order)) if col_names else {}
        
        # Check if already refunded
        if order.get('refund_status') == 'refunded':
            raise HTTPException(400, "This order has already been refunded")
        
        # Check if order is delivered (can't refund delivered orders)
        if order.get('status') == 'Delivered':
            raise HTTPException(400, "Cannot refund delivered orders")
        
        # Check if updated_at column exists
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'updated_at'
            """)
            has_updated_at = cur.fetchone() is not None
            
            if has_updated_at:
                cur.execute("""
                    UPDATE orders 
                    SET refund_status = 'refunded', status = 'Cancelled', updated_at = NOW()
                    WHERE id = %s
                """, (order_id,))
            else:
                cur.execute("""
                    UPDATE orders 
                    SET refund_status = 'refunded', status = 'Cancelled'
                    WHERE id = %s
                """, (order_id,))
        except Exception as update_error:
            print(f"[WARNING] Could not update refund status: {update_error}")
            # Fallback without updated_at
            cur.execute("""
                UPDATE orders 
                SET refund_status = 'refunded', status = 'Cancelled'
                WHERE id = %s
            """, (order_id,))
        
        # Send notification to user via chat
        user_id = order.get('user_id')
        order_total = order.get('total', 0)
        
        if user_id:
            try:
                # Ensure chat_messages table exists
                ensure_chat_table_exists()
                
                # Send refund notification message
                cur.execute("""
                    INSERT INTO chat_messages (order_id, user_id, sender_role, sender_name, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    order_id,
                    user_id,
                    'admin',
                    'Admin',
                    f'💰 Your refund of ₱{float(order_total):.2f} for Order #{order_id} has been processed. The amount will be credited to your account within 3-5 business days.'
                ))
            except Exception as chat_error:
                print(f"[WARNING] Could not send refund notification: {chat_error}")
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Refund processed successfully",
            "order_id": order_id,
            "refund_amount": float(order_total)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Process refund error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to process refund: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Update Payment Proof ---
@app.put("/orders/{oid}/payment-proof")
async def update_payment_proof(oid: int, request: Request):
    """Update payment proof screenshot for an order"""
    data = await request.json()
    payment_proof = data.get("payment_proof")
    
    if not payment_proof:
        raise HTTPException(400, "Payment proof is required")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Check if payment_proof column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders' AND column_name = 'payment_proof'
        """)
        has_payment_proof = cur.fetchone() is not None
        
        if not has_payment_proof:
            print("[INFO] Adding payment_proof column to orders table...")
            cur.execute("ALTER TABLE orders ADD COLUMN payment_proof TEXT;")
            conn.commit()
        
        # Update payment proof
        cur.execute("UPDATE orders SET payment_proof = %s WHERE id = %s RETURNING *", (payment_proof, oid))
        result = cur.fetchone()
        conn.commit()
        
        if not result:
            raise HTTPException(404, f"Order {oid} not found")
        
        print(f"[INFO] Payment proof updated for order {oid}")
        return {"ok": True, "message": "Payment proof updated successfully", "order": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update payment proof error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to update payment proof: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Update Payment Status ---
@app.put("/orders/{oid}/payment")
async def update_payment_status(oid: int, request: Request):
    """Update payment status for an order"""
    data = await request.json()
    payment_status = data.get("payment_status")
    
    if payment_status not in ["paid", "pending", "failed"]:
        raise HTTPException(400, "Invalid payment status. Must be 'paid', 'pending', or 'failed'")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Verify order exists
        cur.execute("SELECT id, payment_method FROM orders WHERE id = %s", (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        # Update payment status
        cur.execute("UPDATE orders SET payment_status = %s WHERE id = %s RETURNING *", 
                   (payment_status, oid))
        conn.commit()
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(404, f"Order {oid} not found")
        
        print(f"[INFO] Order {oid} payment status updated to {payment_status}")
        return {"ok": True, "message": f"Payment status updated to {payment_status}", "order": result}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Update payment status error: {e}")
        raise HTTPException(500, f"Failed to update payment status: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        
        # Check if refund_status column exists
        try:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'refund_status'
            """)
            has_refund_status = cur.fetchone() is not None
            
            if not has_refund_status:
                print("[INFO] Adding refund_status column to orders table...")
                cur.execute("ALTER TABLE orders ADD COLUMN refund_status TEXT DEFAULT NULL;")
                conn.commit()
        except Exception as col_error:
            print(f"[WARNING] Could not check/add refund_status column: {col_error}")
        
        # Check if order exists and get full order data (including items, user_id, and refund_status)
        # Dynamically build SELECT query based on existing columns
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'orders'
        """)
        existing_columns = cur.fetchall()
        existing_columns_set = {col.get('column_name') if isinstance(col, dict) else col[0] for col in existing_columns}
        
        base_columns = ['id', 'status', 'items', 'user_id']
        optional_columns = ['refund_status']
        
        select_columns = [col for col in base_columns if col in existing_columns_set]
        select_columns.extend([col for col in optional_columns if col in existing_columns_set])
        
        query = f"SELECT {', '.join(select_columns)} FROM orders WHERE id=%s"
        cur.execute(query, (oid,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, f"Order {oid} not found")
        
        # Get order data (handle both dict and tuple responses)
        if isinstance(order, dict):
            order_status = order.get("status")
            order_items = order.get("items")
            order_user_id = order.get("user_id")
            order_refund_status = order.get("refund_status", None)
        else:
            # Get column names for tuple response
            col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else []
            order_dict = {col: order[i] for i, col in enumerate(col_names)}
            order_status = order_dict.get("status")
            order_items = order_dict.get("items")
            order_user_id = order_dict.get("user_id")
            order_refund_status = order_dict.get("refund_status", None)
        
        # Allow deletion if:
        # 1. Status is Pending (can be cancelled)
        # 2. Status is Cancelled (already cancelled, can be deleted)
        # 3. Refund status is 'refunded' (already refunded, can be deleted)
        can_delete = (
            order_status == "Pending" or 
            order_status == "Cancelled" or 
            order_refund_status == "refunded"
        )
        
        if not can_delete:
            raise HTTPException(400, f"Cannot delete order. Only orders with 'Pending' or 'Cancelled' status, or refunded orders can be deleted. Current status: {order_status}, Refund status: {order_refund_status}")
        
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
        
        # Delete the order from database
        cur.execute("DELETE FROM orders WHERE id=%s", (oid,))
        deleted_count = cur.rowcount
        conn.commit()
        
        if deleted_count == 0:
            raise HTTPException(404, f"Order {oid} not found or already deleted")
        
        # Verify deletion
        cur.execute("SELECT id FROM orders WHERE id=%s", (oid,))
        verify = cur.fetchone()
        if verify:
            raise HTTPException(500, f"Order {oid} deletion failed - order still exists in database")
        
        print(f"[INFO] Order {oid} permanently deleted from database. Stock restored.")
        return {"ok": True, "message": f"Order {oid} permanently deleted from database. Stock restored."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete order error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to cancel order: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Admin: Get all users ---
@app.get("/users")
async def get_users():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Optimized query with limit for faster loading
        cur.execute("""
            SELECT id, name, email, role, is_approved, id_proof, selfie_proof 
            FROM users 
            ORDER BY id DESC
            LIMIT 500
        """)
        users = cur.fetchall()
        
        # Convert RealDictRow to plain dict for JSON serialization
        if users:
            users_list = []
            for user in users:
                if isinstance(user, dict):
                    users_list.append(dict(user))
                else:
                    # Handle tuple response
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                    if col_names:
                        users_list.append(dict(zip(col_names, user)))
                    else:
                        # Fallback: create dict from tuple indices
                        users_list.append({
                            'id': user[0] if len(user) > 0 else None,
                            'name': user[1] if len(user) > 1 else None,
                            'email': user[2] if len(user) > 2 else None,
                            'role': user[3] if len(user) > 3 else None,
                            'is_approved': user[4] if len(user) > 4 else None,
                            'id_proof': user[5] if len(user) > 5 else None,
                            'selfie_proof': user[6] if len(user) > 6 else None,
                        })
            return json_response(users_list)
        return json_response([])
    except Exception as e:
        print(f"❌ Get users error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get users: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        
        # Convert result to dict if needed
        result_dict = None
        if result:
            if isinstance(result, dict):
                result_dict = dict(result)
            else:
                col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                if col_names:
                    result_dict = dict(zip(col_names, result))
                else:
                    result_dict = result if isinstance(result, dict) else {}
        
        role_msg = f" as {new_role}" if new_role else ""
        return json_response({"ok": True, "message": f"User {'approved' if is_approved else 'rejected'}{role_msg} successfully", "user": result_dict})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Approve user error: {e}")
        raise HTTPException(500, f"Failed to update user approval: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

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
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Chat: Get messages for an order ---
@app.get("/orders/{order_id}/messages")
async def get_order_messages(order_id: int, request: Request):
    """Get all chat messages for a specific order"""
    # Ensure chat table exists
    try:
        ensure_chat_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure chat table exists: {e}")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verify order exists
        cur.execute("SELECT id, user_id FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            # Return empty array instead of 404 for better UX (order might have been deleted)
            # This prevents console errors when checking messages for deleted orders
            return json_response([])
        
        # Get messages for this order - optimized with limit and index-friendly query
        cur.execute("""
            SELECT id, order_id, user_id, sender_role, sender_name, message, image, is_read, read_at, created_at
            FROM chat_messages
            WHERE order_id = %s
            ORDER BY created_at DESC
            LIMIT 100
        """, (order_id,))
        messages = cur.fetchall()
        # Reverse to get chronological order (oldest first)
        messages = list(reversed(messages)) if messages else []
        
        print(f"[DEBUG] Order {order_id}: Found {len(messages) if messages else 0} messages in database")
        
        # Convert RealDictRow to plain dict for JSON serialization
        messages_list = []
        if messages:
            for msg in messages:
                # RealDictCursor returns dict-like objects, convert to plain dict
                if hasattr(msg, 'keys'):
                    # RealDictRow or similar dict-like object - convert recursively
                    msg_dict = {}
                    for key in msg.keys():
                        value = msg[key]
                        # Recursively serialize the value to handle nested objects
                        msg_dict[key] = serialize_datetime(value)
                elif isinstance(msg, dict):
                    # Already a dict, but still need to serialize nested values
                    msg_dict = {k: serialize_datetime(v) for k, v in msg.items()}
                else:
                    # Handle tuple response (shouldn't happen with RealDictCursor, but just in case)
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else []
                    if col_names:
                        msg_dict = {col: serialize_datetime(msg[i]) for i, col in enumerate(col_names)}
                    else:
                        msg_dict = {
                            'id': serialize_datetime(msg[0]) if len(msg) > 0 else None,
                            'order_id': serialize_datetime(msg[1]) if len(msg) > 1 else None,
                            'user_id': serialize_datetime(msg[2]) if len(msg) > 2 else None,
                            'sender_role': serialize_datetime(msg[3]) if len(msg) > 3 else None,
                            'sender_name': serialize_datetime(msg[4]) if len(msg) > 4 else None,
                            'message': serialize_datetime(msg[5]) if len(msg) > 5 else None,
                            'image': serialize_datetime(msg[6]) if len(msg) > 6 else None,
                            'is_read': serialize_datetime(msg[7]) if len(msg) > 7 else None,
                            'read_at': serialize_datetime(msg[8]) if len(msg) > 8 else None,
                            'created_at': serialize_datetime(msg[9]) if len(msg) > 9 else None
                        }
                messages_list.append(msg_dict)
        
        return json_response(messages_list)
    except HTTPException:
        raise
    except psycopg2.OperationalError as db_error:
        error_str = str(db_error)
        print(f"❌ Database error getting messages: {db_error}")
        # Check for quota exceeded
        if "exceeded the data transfer quota" in error_str or "quota" in error_str.lower():
            raise HTTPException(503, "Database temporarily unavailable. Please try again later.")
        raise HTTPException(502, "Database connection error. Please try again.")
    except Exception as e:
        print(f"❌ Get messages error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get messages: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Chat: Send a message for an order ---
@app.post("/orders/{order_id}/messages")
async def send_order_message(order_id: int, request: Request):
    """Send a chat message for a specific order"""
    # Ensure chat table exists
    try:
        ensure_chat_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure chat table exists: {e}")
    
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(400, "Invalid JSON in request body")
    
    message_text = data.get("message", "").strip()
    image_data = data.get("image")  # Base64 encoded image (optional)
    
    # Validate image data if provided
    if image_data:
        # Check if it's a valid base64 image string
        if not isinstance(image_data, str):
            raise HTTPException(400, "Invalid image format")
        
        # Check base64 prefix
        if not image_data.startswith(('data:image/', 'data:image/jpeg', 'data:image/png', 'data:image/gif', 'data:image/webp')):
            raise HTTPException(400, "Invalid image format. Only JPEG, PNG, GIF, and WebP are supported")
        
        # Check image size (base64 is ~33% larger than binary, so 5MB binary = ~6.7MB base64)
        if len(image_data) > 7 * 1024 * 1024:  # 7MB base64 = ~5MB binary
            raise HTTPException(400, "Image size exceeds 5MB limit. Please compress the image.")
    
    # Message or image must be provided
    if not message_text and not image_data:
        raise HTTPException(400, "Message or image is required")
    
    # Get user info from session (stored in request)
    # For now, we'll get it from the request body
    user_id = data.get("user_id")
    sender_role = data.get("sender_role", "user")  # 'user' or 'admin'
    sender_name = data.get("sender_name", "Unknown")
    
    if not user_id:
        raise HTTPException(400, "user_id is required")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verify order exists
        cur.execute("SELECT id, user_id FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        
        # Verify user exists
        cur.execute("SELECT id, name, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        
        # Use actual user name if available
        if not sender_name or sender_name == "Unknown":
            sender_name = user.get("name", "Unknown") if isinstance(user, dict) else (user[1] if len(user) > 1 else "Unknown")
        
        # Preserve sender_role from request, but ensure it's valid
        # If user is admin, they can send as admin; otherwise send as user
        user_role = user.get("role", "user") if isinstance(user, dict) else (user[2] if len(user) > 2 else "user")
        if sender_role == "admin" and user_role != "admin":
            # Non-admin trying to send as admin - force to user
            sender_role = "user"
        elif not sender_role or sender_role not in ["user", "admin"]:
            # Invalid or missing sender_role - use user's actual role
            sender_role = user_role
        
        # Insert message
        cur.execute("""
            INSERT INTO chat_messages (order_id, user_id, sender_role, sender_name, message, image, is_read)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, order_id, user_id, sender_role, sender_name, message, image, is_read, read_at, created_at
        """, (order_id, user_id, sender_role, sender_name, message_text, image_data, False))
        conn.commit()
        message = cur.fetchone()
        
        # Convert message to dict for JSON response
        if message:
            if not isinstance(message, dict):
                col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                if col_names:
                    message = dict(zip(col_names, message))
                else:
                    message = {
                        'id': message[0] if len(message) > 0 else None,
                        'order_id': message[1] if len(message) > 1 else None,
                        'user_id': message[2] if len(message) > 2 else None,
                        'sender_role': message[3] if len(message) > 3 else None,
                        'sender_name': message[4] if len(message) > 4 else None,
                        'message': message[5] if len(message) > 5 else None,
                        'image': message[6] if len(message) > 6 else None,
                        'is_read': message[7] if len(message) > 7 else None,
                        'read_at': message[8] if len(message) > 8 else None,
                        'created_at': message[9] if len(message) > 9 else None
                    }
        
        # If admin sent a message, mark all previous user messages as read
        if sender_role == 'admin':
            cur.execute("""
                UPDATE chat_messages 
                SET is_read = TRUE, read_at = NOW()
                WHERE order_id = %s AND sender_role = 'user' AND is_read = FALSE
            """, (order_id,))
            conn.commit()
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Send message error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to send message: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Chat: Mark messages as read ---
@app.put("/orders/{order_id}/messages/read")
async def mark_messages_read(order_id: int, request: Request):
    """Mark all unread messages for an order as read"""
    # Ensure chat table exists
    try:
        ensure_chat_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure chat table exists: {e}")
    
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    reader_role = data.get("reader_role", "admin")  # Who is reading (admin or user)
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verify order exists
        cur.execute("SELECT id, user_id FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        
        # Mark messages as read based on who is reading
        # If admin is reading, mark user messages as read
        # If user is reading, mark admin messages as read
        if reader_role == 'admin':
            cur.execute("""
                UPDATE chat_messages 
                SET is_read = TRUE, read_at = NOW()
                WHERE order_id = %s AND sender_role = 'user' AND is_read = FALSE
            """, (order_id,))
        else:
            cur.execute("""
                UPDATE chat_messages 
                SET is_read = TRUE, read_at = NOW()
                WHERE order_id = %s AND sender_role = 'admin' AND is_read = FALSE
            """, (order_id,))
        
        conn.commit()
        return {"ok": True, "message": "Messages marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Mark messages read error: {e}")
        raise HTTPException(500, f"Failed to mark messages as read: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Service Rating: Submit rating ---
@app.post("/ratings")
async def submit_rating(request: Request):
    """Submit or update a service rating"""
    # Ensure ratings table exists
    try:
        ensure_ratings_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure ratings table exists: {e}")
    
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(400, "Invalid JSON in request body")
    
    user_id = data.get("user_id")
    rating = data.get("rating")
    comment = data.get("comment", "").strip()
    
    if not user_id:
        raise HTTPException(400, "user_id is required")
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        raise HTTPException(400, "Rating must be an integer between 1 and 5")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verify user exists
        cur.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        
        # Check if user already has a rating
        cur.execute("SELECT id FROM service_ratings WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing rating
            cur.execute("""
                UPDATE service_ratings 
                SET rating = %s, comment = %s, created_at = NOW()
                WHERE user_id = %s
                RETURNING id, user_id, rating, comment, created_at
            """, (rating, comment, user_id))
        else:
            # Insert new rating
            cur.execute("""
                INSERT INTO service_ratings (user_id, rating, comment)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, rating, comment, created_at
            """, (user_id, rating, comment))
        
        conn.commit()
        result = cur.fetchone()
        # Convert result to dict for JSON serialization
        if result:
            if isinstance(result, dict):
                result_dict = dict(result)
            else:
                col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                if col_names:
                    result_dict = dict(zip(col_names, result))
                else:
                    result_dict = {
                        'id': result[0] if len(result) > 0 else None,
                        'user_id': result[1] if len(result) > 1 else None,
                        'rating': result[2] if len(result) > 2 else None,
                        'comment': result[3] if len(result) > 3 else None,
                        'created_at': result[4] if len(result) > 4 else None,
                    }
            return json_response(result_dict)
        return json_response(None)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Submit rating error: {e}")
        raise HTTPException(500, f"Failed to submit rating: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Service Rating: Get user's rating ---
@app.get("/ratings/user/{user_id}")
async def get_user_rating(user_id: int):
    """Get a specific user's rating"""
    # Ensure ratings table exists
    try:
        ensure_ratings_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure ratings table exists: {e}")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, rating, comment, created_at
            FROM service_ratings
            WHERE user_id = %s
        """, (user_id,))
        rating = cur.fetchone()
        
        # Convert RealDictRow to plain dict for JSON serialization
        if rating:
            if isinstance(rating, dict):
                rating_dict = dict(rating)
            else:
                # Handle tuple response
                col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                if col_names:
                    rating_dict = dict(zip(col_names, rating))
                else:
                    rating_dict = {
                        'id': rating[0] if len(rating) > 0 else None,
                        'user_id': rating[1] if len(rating) > 1 else None,
                        'rating': rating[2] if len(rating) > 2 else None,
                        'comment': rating[3] if len(rating) > 3 else None,
                        'created_at': rating[4] if len(rating) > 4 else None,
                    }
            # Convert datetime to string for JSON serialization
            if 'created_at' in rating_dict and rating_dict['created_at']:
                if hasattr(rating_dict['created_at'], 'isoformat'):
                    rating_dict['created_at'] = rating_dict['created_at'].isoformat()
                elif isinstance(rating_dict['created_at'], str):
                    pass  # Already a string
            return json_response(rating_dict)
        return json_response(None)
    except Exception as e:
        print(f"❌ Get user rating error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get rating: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Service Rating: Get all ratings (Admin) ---
@app.get("/ratings")
async def get_all_ratings():
    """Get all service ratings with user information"""
    # Ensure ratings table exists
    try:
        ensure_ratings_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure ratings table exists: {e}")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Optimized query with limit for faster loading
        cur.execute("""
            SELECT r.id, r.user_id, r.rating, r.comment, r.created_at, u.name as user_name, u.email as user_email
            FROM service_ratings r
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
            LIMIT 200
        """)
        ratings = cur.fetchall()
        
        # Convert RealDictRow to plain dict for JSON serialization
        ratings_list = []
        if ratings:
            for rating in ratings:
                # RealDictCursor returns dict-like objects, convert to plain dict
                if hasattr(rating, 'keys'):
                    # RealDictRow or similar dict-like object
                    rating_dict = {key: rating[key] for key in rating.keys()}
                elif isinstance(rating, dict):
                    rating_dict = dict(rating)
                else:
                    # Handle tuple response (shouldn't happen with RealDictCursor, but just in case)
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else []
                    if col_names:
                        rating_dict = dict(zip(col_names, rating))
                    else:
                        rating_dict = {
                            'id': rating[0] if len(rating) > 0 else None,
                            'user_id': rating[1] if len(rating) > 1 else None,
                            'rating': rating[2] if len(rating) > 2 else None,
                            'comment': rating[3] if len(rating) > 3 else None,
                            'created_at': rating[4] if len(rating) > 4 else None,
                            'user_name': rating[5] if len(rating) > 5 else None,
                            'user_email': rating[6] if len(rating) > 6 else None,
                        }
                ratings_list.append(rating_dict)
        
        return json_response(ratings_list)
    except Exception as e:
        print(f"❌ Get all ratings error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get ratings: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Service Rating: Get statistics (Admin) ---
@app.get("/ratings/stats")
async def get_rating_stats():
    """Get rating statistics"""
    # Ensure ratings table exists
    try:
        ensure_ratings_table_exists()
    except Exception as e:
        print(f"[WARNING] Could not ensure ratings table exists: {e}")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Get total count, average rating, and distribution
        cur.execute("""
            SELECT 
                COUNT(*) as total_ratings,
                COALESCE(AVG(rating), 0) as average_rating,
                COUNT(CASE WHEN rating = 5 THEN 1 END) as rating_5,
                COUNT(CASE WHEN rating = 4 THEN 1 END) as rating_4,
                COUNT(CASE WHEN rating = 3 THEN 1 END) as rating_3,
                COUNT(CASE WHEN rating = 2 THEN 1 END) as rating_2,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as rating_1
            FROM service_ratings
        """)
        stats = cur.fetchone()
        return stats if stats else {
            "total_ratings": 0,
            "average_rating": 0,
            "rating_5": 0,
            "rating_4": 0,
            "rating_3": 0,
            "rating_2": 0,
            "rating_1": 0
        }
    except Exception as e:
        print(f"❌ Get rating stats error: {e}")
        raise HTTPException(500, f"Failed to get rating stats: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")

# --- Admin: Get user details with photos and orders ---
@app.get("/users/{user_id}/details")
async def get_user_details(user_id: int):
    """Get detailed user information including profile, photos, and order history"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Check if created_at column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'created_at'
        """)
        has_created_at = cur.fetchone() is not None
        
        # Build SELECT query based on available columns
        if has_created_at:
            cur.execute("""
                SELECT id, name, email, role, id_proof, selfie_proof, is_approved, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, name, email, role, id_proof, selfie_proof, is_approved
                FROM users
                WHERE id = %s
            """, (user_id,))
        
        user = cur.fetchone()
        
        if not user:
            print(f"❌ User not found: {user_id}")
            raise HTTPException(404, "User not found")
        
        # Convert user to dict if needed (RealDictRow handling)
        if not isinstance(user, dict):
            col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
            user = dict(zip(col_names, user)) if col_names else {}
        
        # Add created_at as None if it doesn't exist
        if 'created_at' not in user:
            user['created_at'] = None
        
        # Get user's orders
        cur.execute("""
            SELECT id, fullname, contact, location, items, total, status, payment_method, payment_status, created_at
            FROM orders
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        orders = cur.fetchall()
        
        # Convert orders to list of dicts if needed
        if orders:
            orders_list = []
            for order in orders:
                if not isinstance(order, dict):
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                    orders_list.append(dict(zip(col_names, order)) if col_names else {})
                else:
                    orders_list.append(order)
            orders = orders_list
        
        # Get user's rating if exists
        rating = None
        try:
            cur.execute("""
                SELECT rating, comment, created_at
                FROM service_ratings
                WHERE user_id = %s
            """, (user_id,))
            rating_result = cur.fetchone()
            if rating_result:
                if not isinstance(rating_result, dict):
                    col_names = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
                    rating = dict(zip(col_names, rating_result)) if col_names else {}
                else:
                    rating = rating_result
        except Exception as rating_error:
            print(f"[WARNING] Could not fetch rating: {rating_error}")
            # Rating is optional, continue without it
        
        # Calculate total spent
        total_spent = 0.0
        if orders:
            for order in orders:
                try:
                    total = order.get("total") or 0
                    total_spent += float(total)
                except (ValueError, TypeError):
                    pass
        
        result = {
            "user": user,
            "orders": orders if orders else [],
            "rating": rating,
            "total_orders": len(orders) if orders else 0,
            "total_spent": round(total_spent, 2)
        }
        
        print(f"[INFO] User details fetched successfully for user_id: {user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get user details error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get user details: {str(e)}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"[WARNING] Error closing database connection: {close_error}")
