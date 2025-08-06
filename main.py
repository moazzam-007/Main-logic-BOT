from app import create_app

# Gunicorn is 'app' variable ko dhoondhega
app = create_app()

# Local testing ke liye
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
