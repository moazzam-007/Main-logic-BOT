# main.py (Final Simple Version)
import os
import logging
from app import create_app

# Gunicorn is file ko load karega aur 'app' variable ko dhoondhega
app = create_app()

# Yeh hissa sirf local machine par test karne ke liye hai
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"🚀 Starting Bot locally on port {port}...")
    # debug=True local testing ke liye aasan hai
    app.run(host='0.0.0.0', port=port, debug=True)
