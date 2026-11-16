from app.server import app, ensure_db

if __name__ == "__main__":
    ensure_db()
    app.run(host="0.0.0.0", port=18080, debug=True)
