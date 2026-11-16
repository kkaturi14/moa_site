import os
import sqlite3
import hashlib
from .config import DB_PATH, ADMIN_BOOTSTRAP


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    nickname TEXT,
    phone TEXT,
    address TEXT,
    avatar TEXT,
    bio TEXT,
    role TEXT DEFAULT 'user',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    price INTEGER,
    category TEXT,
    location TEXT,
    image TEXT,
    status TEXT DEFAULT 'selling',
    views INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER,
    product_id INTEGER,
    amount INTEGER,
    pay_method TEXT,
    card_last4 TEXT,
    receipt_file TEXT,
    status TEXT DEFAULT 'paid',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    product_id INTEGER,
    body TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    author_id INTEGER,
    author_name TEXT,
    rating INTEGER,
    content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def seed(conn):
    c = conn.cursor()
    users = [
        ("admin", md5(ADMIN_BOOTSTRAP["password"]), ADMIN_BOOTSTRAP["email"], "관리자", "010-0000-0000", "서울시 중구 본사", None, "", "admin"),
        ("jiwoo", md5("rabbit1234"), "jiwoo@gmail.com", "지우", "010-1111-2222", "서울시 성북구", None, "직거래 선호합니다", "user"),
        ("yuna", md5("soccer!2024"), "yuna@naver.com", "유나네", "010-3333-4444", "경기도 수원시", None, "안 쓰는 물건 정리중", "user"),
        ("soyeon", md5("qwerasdf"), "soyeon@daum.net", "소연", "010-5555-6666", "부산시 해운대구", None, "빠른 답장 드려요", "user"),
        ("doghouse", md5("doge2020"), "doghouse@gmail.com", "댕댕이집사", "010-7777-8888", "인천시 연수구", None, "반려용품 많아요", "user"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO users (username,password,email,nickname,phone,address,avatar,bio,role) VALUES (?,?,?,?,?,?,?,?,?)",
        users,
    )

    products = [
        (2, "아이폰 14 프로 256기가 딥퍼플", "작년에 구매한 아이폰 14 프로입니다. 케이스 끼고 써서 깨끗해요. 배터리 성능 93%. 액정 무파손, 정품 박스/케이블 포함입니다.", 780000, "디지털기기", "서울 성북구", "iphone.jpg", "selling", 142),
        (3, "삼성 비스포크 냉장고 (냉장고만)", "이사가면서 내놓습니다. 2년 사용했고 작동 완벽합니다. 직접 보러 오셔서 확인하세요. 설치 도와드려요.", 450000, "가전", "경기 수원시", "fridge.jpg", "selling", 88),
        (4, "거의 새것 캠핑 테이블 세트", "작년 여름에 두 번 쓰고 보관만 했어요. 의자 4개 포함 풀세트입니다. 접이식이라 보관 편해요.", 65000, "스포츠/레저", "부산 해운대구", "camping.jpg", "selling", 53),
        (5, "강아지 자동 급식기 미개봉", "선물 받았는데 저희 집은 이미 있어서 팝니다. 미개봉 새상품이에요. 앱 연동되는 모델입니다.", 38000, "반려동물", "인천 연수구", "feeder.jpg", "selling", 120),
        (3, "닌텐도 스위치 OLED 화이트", "유광 화이트 올레드 모델입니다. 젤다+마리오카트 칩 같이 드려요. 조이콘 쏠림 없습니다.", 290000, "디지털기기", "경기 수원시", "switch.jpg", "selling", 201),
        (2, "이케아 책상 린몬/아딜스", "자취방 정리하면서 내놓아요. 상판 깨끗하고 흔들림 없습니다. 분해해서 드립니다.", 25000, "가구/인테리어", "서울 성북구", "desk.jpg", "sold", 44),
        (4, "다이슨 V11 무선청소기", "헤드 3종 다 있고 필터 교체했습니다. 흡입력 짱짱해요. 박스는 없습니다.", 210000, "가전", "부산 해운대구", "dyson.jpg", "selling", 167),
    ]
    c.executemany(
        "INSERT INTO products (seller_id,title,description,price,category,location,image,status,views) VALUES (?,?,?,?,?,?,?,?,?)",
        products,
    )

    orders = [
        (3, 1, 780000, "card", "4312", None, "paid"),
        (2, 5, 290000, "card", "9981", None, "paid"),
        (5, 4, 65000, "transfer", None, None, "shipping"),
        (4, 2, 450000, "card", "2207", None, "done"),
    ]
    c.executemany(
        "INSERT INTO orders (buyer_id,product_id,amount,pay_method,card_last4,receipt_file,status) VALUES (?,?,?,?,?,?,?)",
        orders,
    )

    messages = [
        (3, 2, 1, "아이폰 아직 판매하나요? 네고 가능할까요?", 1),
        (2, 3, 1, "네 가능합니다. 직거래시 2만원 빼드릴게요.", 0),
        (5, 4, 4, "캠핑 테이블 상태 사진 더 볼 수 있을까요?", 0),
        (4, 5, 5, "급식기 오늘 거래 가능하세요?", 1),
    ]
    c.executemany(
        "INSERT INTO messages (sender_id,receiver_id,product_id,body,is_read) VALUES (?,?,?,?,?)",
        messages,
    )

    reviews = [
        (1, 3, "유나네", 5, "판매자님 친절하시고 상태도 설명대로였어요. 강추합니다!"),
        (5, 2, "지우", 4, "빠른 거래 감사했습니다. 포장도 꼼꼼했어요."),
        (4, 5, "댕댕이집사", 5, "직거래로 받았는데 새상품 맞네요. 좋아요~"),
    ]
    c.executemany(
        "INSERT INTO reviews (product_id,author_id,author_name,rating,content) VALUES (?,?,?,?,?)",
        reviews,
    )

    conn.commit()


def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript(SCHEMA)
    count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    if count == 0:
        seed(conn)
    conn.close()
