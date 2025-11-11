# 🍽️ RMLCanteen - Food Ordering System

A full-stack food ordering system with FastAPI backend and NeonDB PostgreSQL database.

## 📋 Features

- ✅ User Authentication (Login/Register)
- ✅ Menu Browsing with Categories
- ✅ Shopping Cart System
- ✅ Order Placement & Tracking
- ✅ Admin Dashboard with Statistics
- ✅ Order Status Management
- ✅ Menu Availability (Sold Out/Available)
- ✅ Print Orders
- ✅ Search & Filter Orders
- ✅ Responsive Design

## 🗂️ Project Structure

```
CANTEENORG/
├── templates/          # HTML files
│   ├── home.html      # Landing page
│   ├── index.html     # Login page
│   ├── register.html  # Registration
│   ├── order.html     # Menu & Cart
│   ├── orders.html    # User order history
│   ├── profile.html   # User profile
│   ├── admin.html     # Admin dashboard (improved)
│   └── adminmenu.html # Menu management
├── static/            # CSS & JavaScript
│   ├── style.css      # Global styles
│   ├── auth.css       # Login/Register styles
│   ├── order.css      # Menu page styles
│   ├── orders.css     # Orders list styles
│   ├── profile.css    # Profile page styles
│   ├── admin.css      # Admin dashboard styles
│   ├── adminmenu.css  # Admin menu styles
│   ├── home.css       # Landing page styles
│   └── script.js      # Frontend JavaScript
├── server.py          # FastAPI backend
├── requirements.txt   # Python dependencies
├── START_SERVER.bat   # Quick start script (Windows)
└── README.md          # This file
```

## 🚀 Quick Start

### Option 1: One-Click Start (Windows)

Simply **double-click** `START_SERVER.bat`

### Option 2: Manual Start

```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Start the server
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

## 🌐 Access the Application

Once the server is running:

- **Home Page**: http://localhost:8000/
- **Login**: http://localhost:8000/index.html
- **Register**: http://localhost:8000/register.html

## 🔑 Test Accounts

### Admin Account
- **Email**: `admin@canteen`
- **Password**: `admin123`

### Demo User
- **Email**: `user@demo`
- **Password**: `user123`

## 💾 Database Schema

The application uses **NeonDB PostgreSQL** with the following tables:

### users
```sql
- id (SERIAL PRIMARY KEY)
- name (TEXT)
- email (TEXT UNIQUE)
- password (TEXT)
- role (TEXT DEFAULT 'user')
```

### orders
```sql
- id (SERIAL PRIMARY KEY)
- user_id (INT REFERENCES users(id))
- fullname (TEXT)
- contact (TEXT)
- location (TEXT)
- items (JSONB)
- total (NUMERIC)
- status (TEXT DEFAULT 'Pending')
- created_at (TIMESTAMP DEFAULT NOW())
```

### soldout_items
```sql
- id (SERIAL PRIMARY KEY)
- item_id (TEXT UNIQUE)
```

## 🎨 Features Overview

### For Customers:
- Browse menu with categories (Budget Meals, Foods, Drinks)
- Add items to cart with quantity selection
- View cart with subtotal and delivery fee
- Place orders with delivery details
- Track order status
- Cancel pending orders
- Update profile

### For Admins:
- **Dashboard with Statistics**: Total orders, revenue, status breakdown
- **Order Management**: Update status, delete orders
- **Search & Filter**: Find orders by name, contact, or status
- **Print Orders**: Print individual orders or all orders
- **Menu Management**: Mark items as sold out or available
- **Real-time Updates**: All changes reflect immediately

## 📦 Dependencies

```
fastapi==0.115.0
uvicorn==0.32.0
psycopg2-binary==2.9.11
```

## 🛠️ Tech Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (NeonDB)
- **Styling**: Custom CSS with Poppins font
- **Icons**: Unicode Emojis

## 📱 Responsive Design

The application is fully responsive and works on:
- 💻 Desktop
- 📱 Tablets
- 📱 Mobile phones

## 🔧 Development

### File Organization
- All HTML templates are in `/templates`
- All CSS and JavaScript files are in `/static`
- Backend logic is in `server.py`

### Adding New Features
1. Add HTML template to `/templates`
2. Add corresponding CSS to `/static`
3. Add route in `server.py`
4. Link with `/static/` prefix in HTML

## ⚠️ Important Notes

1. **Database Connection**: Update the PostgreSQL connection string in `server.py` if needed
2. **CORS**: Currently allows all origins - restrict in production
3. **Security**: Passwords are stored in plain text - use hashing in production
4. **Static Files**: Always reference CSS/JS with `/static/` prefix

## 📞 Support

For issues or questions:
- FB Page: RML Canteen Delivery
- Contact: 09097444885
- Email: RMLCanteen@gmail.com

## 📜 License

See LICENSE file for details.

---

**Enjoy your RMLCanteen ordering system!** 🍽️✨

