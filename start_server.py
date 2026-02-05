#!/usr/bin/env python3
"""
Simple script to start the server with proper configuration
"""
import uvicorn
import sys
import os

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Online Canteen Server")
    print("=" * 60)
    print()
    print("Server will start at: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server")
    print()
    
    # Check if database URL is set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print(f"✅ Using DATABASE_URL from environment")
    else:
        print("⚠️ Using default DATABASE_URL from server.py")
    print()
    
    try:
        uvicorn.run(
            "server:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

