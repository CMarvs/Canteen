# 🔄 Database Setup Guide - New NeonDB Database

## Overview
This guide will help you set up your new NeonDB database after changing from your previous one.

---

## Step 1: Update Database Connection String

You have **two options** to set your new database connection string:

### Option A: Set Environment Variable (Recommended)
Set the `DATABASE_URL` environment variable with your new NeonDB connection string:

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL = "postgresql://your-username:your-password@your-host.neon.tech/your-database?sslmode=require"
```

**Windows (Command Prompt):**
```cmd
set DATABASE_URL=postgresql://your-username:your-password@your-host.neon.tech/your-database?sslmode=require
```

**Linux/Mac:**
```bash
export DATABASE_URL="postgresql://your-username:your-password@your-host.neon.tech/your-database?sslmode=require"
```

### Option B: Update server.py directly
Edit `server.py` line 31 and replace the connection string:
```python
DB_URL = os.getenv("DATABASE_URL", "YOUR_NEW_CONNECTION_STRING_HERE")
```

**⚠️ Note:** Option A is recommended because it keeps your credentials out of your code.

---

## Step 2: Run Database Setup Script

Run the setup script to create all tables and initial accounts:

```bash
python setup_database.py
```

This script will:
- ✅ Create all necessary database tables (users, orders, menu_items, soldout_items)
- ✅ Create initial admin account: `admin@canteen` / `admin123`
- ✅ Create initial demo user: `user@demo` / `user123`

---

## Step 3: Verify Setup

1. **Start the server:**
   ```bash
   python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
   ```
   Or double-click `START_SERVER.bat`

2. **Test login:**
   - Go to: http://localhost:8000/index.html
   - Login with: `admin@canteen` / `admin123`

3. **Check database:**
   - The setup script will show you how many users were created
   - You should see at least 2 users (admin and demo user)

---

## Step 4: Create Additional Accounts (Optional)

If you need to create more accounts:

1. **Via Registration Page:**
   - Go to: http://localhost:8000/register.html
   - Register a new account
   - Note: The first user registered becomes admin automatically

2. **Via Database:**
   - You can manually insert users into the database using NeonDB's SQL editor

---

## Troubleshooting

### Connection Error
If you get a connection error:
- ✅ Verify your DATABASE_URL is correct
- ✅ Check that your NeonDB database is active
- ✅ Ensure your network allows connections to NeonDB
- ✅ Make sure SSL mode is set to `require` in the connection string

### Tables Already Exist
If tables already exist, the script will skip creating them (safe to run multiple times).

### Accounts Already Exist
If accounts already exist, the script will skip creating them (safe to run multiple times).

### Reset Everything
If you want to start fresh:
```bash
python DELETE_ALL_USERS.py
python setup_database.py
```

---

## 📝 Quick Reference

**Default Test Accounts:**
- Admin: `admin@canteen` / `admin123`
- User: `user@demo` / `user123`

**Database Tables:**
- `users` - User accounts and authentication
- `orders` - Customer orders
- `menu_items` - Menu items (if using database menu)
- `soldout_items` - Items marked as sold out

---

## 🎉 You're All Set!

Once the setup script completes successfully, you can:
1. Start your server
2. Login with the admin account
3. Start using your canteen application!

