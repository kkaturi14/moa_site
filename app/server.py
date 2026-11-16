import os
import io
import sqlite3
import subprocess
import requests
from flask import (
    Flask, request, redirect, render_template, make_response,
    send_file, jsonify, abort, url_for, Response,
)
from . import config
from .db import get_db, ensure_db, md5

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = config.SECRET_KEY

CATEGORIES = ["디지털기기", "가전", "가구/인테리어", "스포츠/레저", "반려동물", "의류", "도서/티켓"]


def current_user():
    uid = request.cookies.get("uid")
    if not uid:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row


@app.context_processor
def inject_globals():
    return {"me": current_user(), "site_name": config.SITE_NAME, "categories": CATEGORIES}


# -------------------- 홈 / 상품 --------------------
@app.route("/")
def index():
    cat = request.args.get("cat", "")
    conn = get_db()
    if cat:
        rows = conn.execute(
            "SELECT p.*, u.nickname AS seller FROM products p LEFT JOIN users u ON p.seller_id=u.id "
            "WHERE category=? ORDER BY p.created_at DESC", (cat,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT p.*, u.nickname AS seller FROM products p LEFT JOIN users u ON p.seller_id=u.id "
            "ORDER BY p.created_at DESC"
        ).fetchall()
    conn.close()
    return render_template("index.html", products=rows, cat=cat)


@app.route("/product/<int:pid>")
def product(pid):
    conn = get_db()
    conn.execute("UPDATE products SET views=views+1 WHERE id=?", (pid,))
    conn.commit()
    p = conn.execute(
        "SELECT p.*, u.nickname AS seller, u.id AS seller_uid, u.address AS seller_loc "
        "FROM products p LEFT JOIN users u ON p.seller_id=u.id WHERE p.id=?", (pid,)
    ).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (pid,)).fetchall()
    conn.close()
    if not p:
        abort(404)
    return render_template("product.html", p=p, reviews=reviews)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    rows = []
    if q:
        conn = get_db()
        sql = ("SELECT p.*, u.nickname AS seller FROM products p LEFT JOIN users u ON p.seller_id=u.id "
               "WHERE p.title LIKE '%" + q + "%' OR p.description LIKE '%" + q + "%'")
        try:
            rows = conn.execute(sql).fetchall()
        except sqlite3.Error:
            rows = []
        conn.close()
    return render_template("search.html", q=q, products=rows)


@app.route("/product/<int:pid>/review", methods=["POST"])
def add_review(pid):
    me = current_user()
    name = me["nickname"] if me else request.form.get("name", "비회원")
    rating = request.form.get("rating", "5")
    content = request.form.get("content", "")
    conn = get_db()
    conn.execute("INSERT INTO reviews (product_id,author_id,author_name,rating,content) VALUES (?,?,?,?,?)",
                 (pid, me["id"] if me else None, name, rating, content))
    conn.commit()
    conn.close()
    return redirect(url_for("product", pid=pid))


# -------------------- 인증 --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        sql = ("SELECT * FROM users WHERE username='" + username +
               "' AND password='" + md5(password) + "'")
        try:
            user = conn.execute(sql).fetchone()
        except sqlite3.Error:
            user = None
        conn.close()
        if user:
            nxt = request.args.get("next") or request.form.get("next") or url_for("index")
            resp = make_response(redirect(nxt))
            resp.set_cookie("uid", str(user["id"]))
            return resp
        error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        nickname = request.form.get("nickname", "") or username
        conn = get_db()
        exists = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if exists:
            conn.close()
            error = "이미 사용중인 아이디입니다."
        elif not username or not password:
            conn.close()
            error = "아이디와 비밀번호를 입력하세요."
        else:
            conn.execute("INSERT INTO users (username,password,email,nickname,role) VALUES (?,?,?,?,'user')",
                         (username, md5(password), email, nickname))
            conn.commit()
            uid = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"]
            conn.close()
            resp = make_response(redirect(url_for("index")))
            resp.set_cookie("uid", str(uid))
            return resp
    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie("uid")
    return resp


# -------------------- 상품 등록 / 업로드 --------------------
@app.route("/sell", methods=["GET", "POST"])
def sell():
    me = current_user()
    if not me:
        return redirect(url_for("login", next=url_for("sell")))
    if request.method == "POST":
        title = request.form.get("title", "")
        desc = request.form.get("description", "")
        price = request.form.get("price", "0")
        category = request.form.get("category", "")
        location = request.form.get("location", "")
        image_name = None
        file = request.files.get("image")
        if file and file.filename:
            image_name = file.filename
            file.save(os.path.join(config.UPLOAD_DIR, image_name))
        conn = get_db()
        conn.execute(
            "INSERT INTO products (seller_id,title,description,price,category,location,image) "
            "VALUES (?,?,?,?,?,?,?)",
            (me["id"], title, desc, price, category, location, image_name),
        )
        conn.commit()
        pid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.close()
        return redirect(url_for("product", pid=pid))
    return render_template("sell.html")


# -------------------- 마이페이지 / 계정 --------------------
@app.route("/account")
def account():
    me = current_user()
    if not me:
        return redirect(url_for("login", next=url_for("account")))
    conn = get_db()
    products = conn.execute("SELECT * FROM products WHERE seller_id=? ORDER BY id DESC", (me["id"],)).fetchall()
    conn.close()
    return render_template("account.html", products=products)


@app.route("/account/update", methods=["POST"])
def account_update():
    me = current_user()
    if not me:
        abort(401)
    editable = dict(request.form)
    conn = get_db()
    for field, value in editable.items():
        try:
            conn.execute("UPDATE users SET %s=? WHERE id=?" % field, (value, me["id"]))
        except sqlite3.Error:
            pass
    conn.commit()
    conn.close()
    return redirect(url_for("account"))


@app.route("/account/password", methods=["POST"])
def account_password():
    me = current_user()
    if not me:
        abort(401)
    new_pw = request.form.get("new_password", "")
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE id=?", (md5(new_pw), me["id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("account"))


@app.route("/account/avatar/fetch")
def avatar_fetch():
    me = current_user()
    if not me:
        abort(401)
    url = request.args.get("url", "")
    try:
        r = requests.get(url, timeout=5)
        fname = "avatar_%s.img" % me["id"]
        with open(os.path.join(config.UPLOAD_DIR, fname), "wb") as f:
            f.write(r.content)
        conn = get_db()
        conn.execute("UPDATE users SET avatar=? WHERE id=?", (fname, me["id"]))
        conn.commit()
        conn.close()
        return redirect(url_for("account"))
    except Exception as e:
        return "가져오기 실패: %s" % e, 502


# -------------------- 쪽지 --------------------
@app.route("/messages")
def messages():
    me = current_user()
    if not me:
        return redirect(url_for("login", next=url_for("messages")))
    conn = get_db()
    rows = conn.execute(
        "SELECT m.*, s.nickname AS sender_name, p.title AS product_title "
        "FROM messages m LEFT JOIN users s ON m.sender_id=s.id LEFT JOIN products p ON m.product_id=p.id "
        "WHERE m.receiver_id=? ORDER BY m.id DESC", (me["id"],)
    ).fetchall()
    conn.close()
    return render_template("messages.html", messages=rows)


@app.route("/messages/<int:mid>")
def message_detail(mid):
    me = current_user()
    if not me:
        return redirect(url_for("login"))
    conn = get_db()
    m = conn.execute(
        "SELECT m.*, s.nickname AS sender_name, p.title AS product_title "
        "FROM messages m LEFT JOIN users s ON m.sender_id=s.id LEFT JOIN products p ON m.product_id=p.id "
        "WHERE m.id=?", (mid,)
    ).fetchone()
    conn.execute("UPDATE messages SET is_read=1 WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    if not m:
        abort(404)
    return render_template("message_detail.html", m=m)


@app.route("/messages/send", methods=["POST"])
def message_send():
    me = current_user()
    if not me:
        abort(401)
    receiver_id = request.form.get("receiver_id")
    product_id = request.form.get("product_id")
    body = request.form.get("body", "")
    conn = get_db()
    conn.execute("INSERT INTO messages (sender_id,receiver_id,product_id,body) VALUES (?,?,?,?)",
                 (me["id"], receiver_id, product_id, body))
    conn.commit()
    conn.close()
    return redirect(url_for("product", pid=product_id) if product_id else url_for("messages"))


# -------------------- 주문 --------------------
@app.route("/buy/<int:pid>", methods=["POST"])
def buy(pid):
    me = current_user()
    if not me:
        return redirect(url_for("login", next=url_for("product", pid=pid)))
    conn = get_db()
    p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    card = request.form.get("card", "")
    conn.execute(
        "INSERT INTO orders (buyer_id,product_id,amount,pay_method,card_last4) VALUES (?,?,?,?,?)",
        (me["id"], pid, p["price"], request.form.get("pay_method", "card"), card[-4:] if card else None),
    )
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return redirect(url_for("order_detail", oid=oid))


@app.route("/orders")
def orders():
    me = current_user()
    if not me:
        return redirect(url_for("login", next=url_for("orders")))
    conn = get_db()
    rows = conn.execute(
        "SELECT o.*, p.title AS product_title FROM orders o LEFT JOIN products p ON o.product_id=p.id "
        "WHERE o.buyer_id=? ORDER BY o.id DESC", (me["id"],)
    ).fetchall()
    conn.close()
    return render_template("orders.html", orders=rows)


@app.route("/orders/<int:oid>")
def order_detail(oid):
    me = current_user()
    if not me:
        return redirect(url_for("login"))
    conn = get_db()
    o = conn.execute(
        "SELECT o.*, p.title AS product_title FROM orders o LEFT JOIN products p ON o.product_id=p.id "
        "WHERE o.id=?", (oid,)
    ).fetchone()
    conn.close()
    if not o:
        abort(404)
    return render_template("order_detail.html", o=o)


# -------------------- 파일 / 유틸 --------------------
@app.route("/download")
def download():
    f = request.args.get("file", "")
    path = os.path.join(config.UPLOAD_DIR, f)
    try:
        return send_file(os.path.abspath(path))
    except Exception:
        abort(404)


@app.route("/uploads/")
def uploads_index():
    files = os.listdir(config.UPLOAD_DIR)
    items = "".join("<li><a href='/static/uploads/%s'>%s</a></li>" % (x, x) for x in files)
    return "<h3>Index of /uploads/</h3><ul>%s</ul>" % items


@app.route("/go")
def go():
    return redirect(request.args.get("url", "/"))


@app.route("/robots.txt")
def robots():
    body = "User-agent: *\nDisallow: /admin\nDisallow: /backup.sql\nDisallow: /api/\n"
    return Response(body, mimetype="text/plain")


@app.route("/backup.sql")
def backup():
    lines = ["-- moamarket DB dump", "-- generated by nightly cron"]
    conn = get_db()
    for u in conn.execute("SELECT * FROM users").fetchall():
        lines.append("INSERT INTO users VALUES (%s,'%s','%s','%s');" %
                      (u["id"], u["username"], u["password"], u["email"]))
    conn.close()
    return Response("\n".join(lines), mimetype="text/plain")


# -------------------- 관리자 --------------------
@app.route("/admin")
def admin():
    me = current_user()
    if not me or me["role"] != "admin":
        abort(403)
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    orders = conn.execute(
        "SELECT o.*, p.title AS product_title, u.nickname AS buyer "
        "FROM orders o LEFT JOIN products p ON o.product_id=p.id LEFT JOIN users u ON o.buyer_id=u.id "
        "ORDER BY o.id DESC"
    ).fetchall()
    conn.close()
    return render_template("admin.html", users=users, orders=orders)


@app.route("/admin/tools")
def admin_tools():
    me = current_user()
    if not me or me["role"] != "admin":
        abort(403)
    host = request.args.get("host", "")
    output = ""
    if host:
        output = subprocess.getoutput("ping -c 1 " + host)
    return render_template("admin_tools.html", host=host, output=output)


# -------------------- API --------------------
@app.route("/api/users")
def api_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/user/<int:uid>")
def api_user(uid):
    conn = get_db()
    r = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    if not r:
        abort(404)
    return jsonify(dict(r))


@app.route("/api/products")
def api_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    ensure_db()
    app.run(host="0.0.0.0", port=18080, debug=True)
