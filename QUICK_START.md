# Quick Start Guide

## Starting the Website

### Option 1: Using the startup script (Recommended)
```bash
python start_server.py
```

### Option 2: Using uvicorn directly
```bash
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

## Accessing the Website

Once the server is running, open your browser and go to:

- **Login Page**: http://localhost:8000/index.html
- **Register Page**: http://localhost:8000/register.html
- **Home Page**: http://localhost:8000/

## Default Credentials

- **Admin**: 
  - Email: `admin@canteen`
  - Password: `admin123`

- **Test User**: 
  - Email: `user@demo`
  - Password: `user123`

## Troubleshooting

### If the server won't start:

1. **Check Python version**: Should be 3.7+
   ```bash
   python --version
   ```

2. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn psycopg2-binary
   ```

3. **Check database connection**:
   ```bash
   python diagnose_website.py
   ```

4. **Check for errors in the terminal** when starting the server

### If pages don't load:

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Check browser console** (F12 → Console tab) for JavaScript errors
3. **Verify server is running** - you should see logs in the terminal
4. **Try a different browser** or incognito mode

### If login/register doesn't work:

1. **Check browser console** (F12 → Console) for error messages
2. **Check server logs** in the terminal for backend errors
3. **Verify database connection** - run `python diagnose_website.py`
4. **Check network tab** (F12 → Network) to see if API calls are being made

## Common Issues

### "Connection refused" error
- Make sure the server is running
- Check if port 8000 is already in use
- Try a different port: `--port 8001`

### "Database connection failed"
- Check your DATABASE_URL environment variable
- Verify your NeonDB database is accessible
- Check your internet connection

### "Module not found" error
- Install missing modules: `pip install <module-name>`
- Make sure you're in the correct directory

## Getting Help

If you're still having issues:

1. Run the diagnosis script: `python diagnose_website.py`
2. Check the server logs for error messages
3. Check the browser console (F12) for JavaScript errors
4. Share the error messages you see

