import os
from app.server import app, ensure_db

if __name__ == "__main__":
    ensure_db()
    # 로컬은 18080, Render 등은 PORT 환경변수를 주입하므로 그걸 우선 사용
    port = int(os.environ.get("PORT", 18080))
    app.run(host="0.0.0.0", port=port, debug=True)
