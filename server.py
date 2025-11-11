from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import psycopg2, json
from psycopg2.extras import RealDictCursor
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NeonDB connection
DB_URL = "postgresql://neondb_owner:npg_O0LrfcY7oGZN@ep-silent-rain-a19bkdss-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise HTTPException(500, f"Database connection failed: {str(e)}")

# --- Safe FileResponse helper ---
def safe_file_response(path: str):
    try:
        if os.path.exists(path):
            return FileResponse(path)
        else:
            print(f"❌ File not found: {path}")
            return JSONResponse(status_code=404, content={"error": "File not found", "path": path})
    except Exception as e:
        print(f"❌ Error serving file {path}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Routes
@app.get("/")
def home(): return safe_file_response("templates/home.html")
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
def register(data: dict):
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
def login(data: dict):
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

# --- Place order ---
@app.post("/orders")
def place_order(data: dict):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders(user_id,fullname,contact,location,items,total)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            data.get("user_id"), data.get("fullname"), data.get("contact"),
            data.get("location"), json.dumps(data.get("items")), data.get("total")
        ))
        conn.commit()
        return {"ok": True, "message": "Order placed successfully"}
    except Exception as e:
        print(f"❌ Order placement error: {e}")
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

# --- Admin: Update order status ---
@app.put("/orders/{oid}")
def update_order(oid: int, data: dict):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status=%s WHERE id=%s RETURNING *",
                    (data.get("status"), oid))
        conn.commit()
        return cur.fetchone()
    except Exception as e:
        print(f"❌ Update order error: {e}")
        raise HTTPException(500, f"Failed to update order: {str(e)}")
    finally:
        conn.close()
