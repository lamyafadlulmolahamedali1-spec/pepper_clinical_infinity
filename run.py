#!/usr/bin/env python3
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════╗
    ║  🚀 PEPPER THERAPY SYSTEM                  ║
    ║  📊 Server starting...                     ║
    ║  🌐 http://localhost:5009                  ║
    ╚════════════════════════════════════════════╝
    """)
    app.run(debug=True, port=5009)
