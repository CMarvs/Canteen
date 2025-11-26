# 🚀 Deploy to Render - Complete Guide

This guide will help you deploy your FastAPI Canteen application to Render.

## 📋 Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Render Account** - Sign up at [render.com](https://render.com) (free tier available)
3. **NeonDB Database** - You already have this set up

---

## 🔧 Step 1: Prepare Your Code

### 1.1 Update Database URL (Already Done ✅)
Your `server.py` now uses environment variables for the database URL.

### 1.2 Push Code to GitHub

If you haven't already, create a GitHub repository and push your code:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Ready for Render deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

**Important Files to Include:**
- ✅ `server.py`
- ✅ `requirements.txt`
- ✅ `static/` folder
- ✅ `templates/` folder
- ❌ Don't commit `.env` files or sensitive data

---

## 🌐 Step 2: Deploy on Render

### 2.1 Create a New Web Service

1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** button in the dashboard
3. Select **"Web Service"**
4. Connect your GitHub account if not already connected
5. Select your repository from the list

### 2.2 Configure Your Service

Fill in the following settings:

**Basic Settings:**
- **Name**: `rml-canteen` (or any name you prefer)
- **Region**: Choose closest to your users (e.g., `Singapore` or `Oregon`)
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (or `.` if needed)

**Build & Deploy:**
- **Runtime**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  uvicorn server:app --host 0.0.0.0 --port $PORT
  ```
  ⚠️ **Important**: 
  - Render sets the `$PORT` environment variable automatically - **always use `$PORT`**
  - Use `0.0.0.0` (not `127.0.0.1`) to allow external connections
  - Don't use `--reload` in production (only for local development)

### 2.3 Environment Variables

Click on **"Environment"** tab and add:

| Key | Value | Description |
|-----|-------|-------------|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_Y2KOWuHn9DMU@ep-lingering-tooth-a1kqy37g-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require` | Your NeonDB connection string (use your current connection string) |

**⚠️ Security Note**: In production, consider using Render's environment variable encryption feature.

### 2.4 Advanced Settings (Optional)

- **Auto-Deploy**: Enable to automatically deploy on every push to main branch
- **Health Check Path**: `/ping` (if you have a health check endpoint)

### 2.5 Deploy

Click **"Create Web Service"** and wait for deployment to complete (usually 2-5 minutes).

---

## ✅ Step 3: Verify Deployment

1. Once deployed, Render will give you a URL like: `https://your-app-name.onrender.com`
2. Visit the URL to test your application
3. Check the logs in Render dashboard for any errors

---

## 🔍 Troubleshooting

### Common Issues:

**1. Build Fails**
- Check that `requirements.txt` has all dependencies
- Verify Python version compatibility

**2. Application Crashes**
- Check logs in Render dashboard
- Ensure `$PORT` is used in start command (not a fixed port)
- Verify database connection string is correct

**3. Static Files Not Loading**
- Ensure `static/` and `templates/` folders are in the repository
- Check file paths are relative, not absolute

**4. Database Connection Errors**
- Verify `DATABASE_URL` environment variable is set correctly
- Check NeonDB allows connections from Render's IPs (usually enabled by default)

---

## 🔄 Updating Your App

After making changes:

1. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```

2. If Auto-Deploy is enabled, Render will automatically redeploy
3. Otherwise, manually trigger deployment from Render dashboard

---

## 💰 Render Free Tier Limits

- **Free Tier**:
  - Services spin down after 15 minutes of inactivity
  - First request after spin-down takes ~30 seconds (cold start)
  - 750 hours/month free
  - Perfect for development/testing

- **Paid Plans**:
  - Services stay always-on
  - No cold starts
  - Better performance

---

## 🔐 Security Best Practices

1. **Never commit sensitive data** to GitHub
2. **Use environment variables** for all secrets (database URLs, API keys)
3. **Enable HTTPS** (Render does this automatically)
4. **Review CORS settings** - Consider restricting origins in production

---

## 📝 Quick Reference

**Render Dashboard**: https://dashboard.render.com
**Your App URL**: `https://your-app-name.onrender.com`
**Logs**: Available in Render dashboard under your service

---

## 🆘 Need Help?

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- Check your application logs in Render dashboard

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Web Service created on Render
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- [ ] `DATABASE_URL` environment variable set
- [ ] Service deployed successfully
- [ ] Application accessible via Render URL
- [ ] Database connection working
- [ ] Static files loading correctly

---

**🎉 Congratulations! Your app is now live on Render!**

