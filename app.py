from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, quote, unquote, urlparse
import hashlib
import hmac
import html
import os
import secrets
import sqlite3
import threading
import time
import webbrowser


ROOT = Path(__file__).resolve().parent
DATABASE_DIR = Path(os.environ.get("DATABASE_DIR", ROOT / "database")).resolve()
USING_DEFAULT_DATABASE_PATH = "DATABASE_PATH" not in os.environ
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATABASE_DIR / "hexacare.sqlite3")).resolve()
LEGACY_DATABASE_PATH = DATABASE_DIR / "equafund.sqlite3"
STATIC_DIR = ROOT / "assets"
SECRET_PATH = DATABASE_DIR / ".secret_key"
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")


EVENT_SEED = [
    {
        "slug": "beasiswa-anak-pesisir",
        "title": "Beasiswa Anak Pesisir",
        "location": "Kupang, NTT",
        "category": "Pendidikan",
        "summary": "Perlengkapan sekolah, biaya transport, dan kelas pendamping untuk anak pesisir.",
        "target_amount": 85000000,
        "base_raised": 53750000,
        "image_url": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=900&q=80",
    },
    {
        "slug": "paket-pangan-keluarga-rentan",
        "title": "Paket Pangan Keluarga Rentan",
        "location": "Bekasi, Jawa Barat",
        "category": "Pangan",
        "summary": "Distribusi bahan pokok bulanan untuk keluarga terdampak krisis pendapatan.",
        "target_amount": 60000000,
        "base_raised": 36250000,
        "image_url": "https://images.unsplash.com/photo-1593113598332-cd288d649433?auto=format&fit=crop&w=900&q=80",
    },
    {
        "slug": "klinik-keliling-desa",
        "title": "Klinik Keliling Desa Terpencil",
        "location": "Sigi, Sulawesi Tengah",
        "category": "Kesehatan",
        "summary": "Pemeriksaan dasar, obat esensial, dan edukasi kesehatan ibu-anak.",
        "target_amount": 120000000,
        "base_raised": 78400000,
        "image_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=900&q=80",
    },
    {
        "slug": "rumah-layak-huni",
        "title": "Perbaikan Rumah Layak Huni",
        "location": "Lombok Timur, NTB",
        "category": "Hunian",
        "summary": "Renovasi atap, sanitasi, dan akses air bersih untuk keluarga pra-sejahtera.",
        "target_amount": 95000000,
        "base_raised": 42100000,
        "image_url": "https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=900&q=80",
    },
]


def ensure_secret():
    DATABASE_DIR.mkdir(exist_ok=True)
    if not SECRET_PATH.exists():
        SECRET_PATH.write_text(secrets.token_hex(32), encoding="utf-8")
    return SECRET_PATH.read_text(encoding="utf-8").strip().encode("utf-8")


SECRET_KEY = ensure_secret()


def connect_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATABASE_DIR.mkdir(exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USING_DEFAULT_DATABASE_PATH and LEGACY_DATABASE_PATH.exists() and not DATABASE_PATH.exists():
        LEGACY_DATABASE_PATH.rename(DATABASE_PATH)
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                target_amount INTEGER NOT NULL,
                base_raised INTEGER NOT NULL DEFAULT 0,
                image_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                donor_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                note TEXT,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (event_id) REFERENCES events(id)
            );
            """
        )
        total = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if total == 0:
            now = int(time.time())
            db.executemany(
                """
                INSERT INTO events
                (slug, title, location, category, summary, target_amount, base_raised, image_url, created_at)
                VALUES (:slug, :title, :location, :category, :summary, :target_amount, :base_raised, :image_url, :created_at)
                """,
                [{**event, "created_at": now} for event in EVENT_SEED],
            )


def rupiah(value):
    return "Rp" + f"{int(value):,}".replace(",", ".")


def esc(value):
    return html.escape(str(value or ""), quote=True)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return hmac.compare_digest(check, digest)


def sign_value(value):
    signature = hmac.new(SECRET_KEY, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{value}.{signature}"


def unsign_value(signed):
    if not signed or "." not in signed:
        return None
    value, signature = signed.rsplit(".", 1)
    expected = hmac.new(SECRET_KEY, value.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(signature, expected):
        return value
    return None


def get_user_from_cookie(header):
    if not header:
        return None
    jar = cookies.SimpleCookie()
    try:
        jar.load(header)
    except cookies.CookieError:
        return None
    morsel = jar.get("hexacare_session")
    user_id = unsign_value(morsel.value if morsel else "")
    if not user_id:
        return None
    with connect_db() as db:
        return db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()


def read_template(folder):
    return (ROOT / folder / "index.html").read_text(encoding="utf-8")


def render(folder, context=None):
    context = context or {}
    context.setdefault("year", time.strftime("%Y"))
    context.setdefault("alert", "")
    context.setdefault("auth_nav", "")
    return Template(read_template(folder)).safe_substitute(context)


def event_rows():
    with connect_db() as db:
        return db.execute(
            """
            SELECT e.*,
            e.base_raised + COALESCE(SUM(t.amount), 0) AS raised
            FROM events e
            LEFT JOIN transactions t ON t.event_id = e.id AND t.status = 'SUCCESS'
            WHERE e.status = 'ACTIVE'
            GROUP BY e.id
            ORDER BY e.created_at ASC
            """
        ).fetchall()


def transaction_rows(user_id=None, limit=20):
    params = []
    where = ""
    if user_id:
        where = "WHERE t.user_id = ?"
        params.append(user_id)
    params.append(limit)
    with connect_db() as db:
        return db.execute(
            f"""
            SELECT t.*, e.title AS event_title, e.location AS event_location
            FROM transactions t
            JOIN events e ON e.id = t.event_id
            {where}
            ORDER BY t.created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()


def build_auth_nav(user):
    if user:
        return f"""
        <span class="user-chip">Halo, {esc(user["name"])}</span>
        <a class="ghost-button" href="/Logout/">Keluar</a>
        """
    return """
    <a class="ghost-button" href="/Login/">Masuk</a>
    <a class="primary-button" href="/Registrasi/">Daftar</a>
    """


def build_event_cards():
    cards = []
    for event in event_rows():
        percent = min(round((event["raised"] / event["target_amount"]) * 100), 100)
        cards.append(
            f"""
            <article class="event-card">
              <img src="{esc(event["image_url"])}" alt="{esc(event["title"])}">
              <div class="event-body">
                <div class="card-topline">
                  <span>{esc(event["category"])}</span>
                  <span>{esc(event["location"])}</span>
                </div>
                <h3>{esc(event["title"])}</h3>
                <p>{esc(event["summary"])}</p>
                <div class="progress" aria-label="Progress {percent}%"><span style="width: {percent}%"></span></div>
                <div class="fund-row">
                  <strong>{rupiah(event["raised"])}</strong>
                  <small>dari {rupiah(event["target_amount"])}</small>
                </div>
                <a class="primary-button full-button" href="/Donasi/?event={quote(event["slug"])}">Donasi</a>
              </div>
            </article>
            """
        )
    return "\n".join(cards)


def build_event_options(selected_slug=""):
    options = []
    for event in event_rows():
        selected = " selected" if event["slug"] == selected_slug else ""
        options.append(f'<option value="{event["id"]}"{selected}>{esc(event["title"])}</option>')
    return "\n".join(options)


def build_transaction_list(user_id=None):
    rows = transaction_rows(user_id=user_id)
    if not rows:
        return '<div class="empty-state">Belum ada transaksi. Donasi pertama akan muncul di sini.</div>'
    items = []
    for trx in rows:
        date_text = time.strftime("%d %b %Y %H:%M", time.localtime(trx["created_at"]))
        items.append(
            f"""
            <article class="transaction-card">
              <div>
                <span class="reference">{esc(trx["reference"])}</span>
                <h3>{esc(trx["event_title"])}</h3>
                <p>{esc(trx["donor_name"])} - {esc(trx["payment_method"])} - {date_text}</p>
              </div>
              <strong>{rupiah(trx["amount"])}</strong>
            </article>
            """
        )
    return "\n".join(items)


def build_stats():
    with connect_db() as db:
        event_count, base_total = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(base_raised), 0) FROM events WHERE status = 'ACTIVE'"
        ).fetchone()
        transaction_count, donation_total = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM transactions WHERE status = 'SUCCESS'"
        ).fetchone()
    return {
        "event_count": event_count,
        "transaction_count": transaction_count,
        "donation_total": rupiah(donation_total),
        "public_total": rupiah(base_total + donation_total),
    }


class HexaCareHandler(BaseHTTPRequestHandler):
    server_version = "HexaCare/1.0"

    def do_GET(self):
        parsed = urlparse(unquote(self.path))
        path = parsed.path
        query = parse_qs(parsed.query)
        user = get_user_from_cookie(self.headers.get("Cookie"))

        if path.startswith("/assets/"):
            self.serve_static(path)
        elif path in ("/", "/index.html"):
            self.home(user)
        elif path in ("/Login/", "/Login"):
            self.login_page(user)
        elif path in ("/Registrasi/", "/Registrasi"):
            self.register_page(user)
        elif path in ("/Tampilan-Event/", "/Tampilan Event/", "/Tampilan-Event", "/Tampilan Event"):
            self.events_page(user)
        elif path in ("/Donasi/", "/Donasi"):
            self.donation_page(user, query)
        elif path in ("/Proses-Transaksi/", "/Proses Transaksi/", "/Proses-Transaksi", "/Proses Transaksi"):
            self.process_page(user, query)
        elif path in ("/Total-Donasi/", "/Total Donasi/", "/Total-Donasi", "/Total Donasi"):
            self.total_page(user)
        elif path in ("/Logout/", "/Logout"):
            self.logout()
        elif path == "/api/health":
            self.send_json('{"ok": true}')
        else:
            self.not_found()

    def do_POST(self):
        parsed = urlparse(unquote(self.path))
        user = get_user_from_cookie(self.headers.get("Cookie"))
        form = self.read_form()
        if parsed.path in ("/Login/", "/Login"):
            self.handle_login(form)
        elif parsed.path in ("/Registrasi/", "/Registrasi"):
            self.handle_register(form)
        elif parsed.path in ("/Proses-Transaksi/", "/Proses Transaksi"):
            self.handle_transaction(user, form)
        else:
            self.not_found()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return {key: values[0].strip() for key, values in parse_qs(body).items()}

    def write_html(self, content, status=200, extra_headers=None):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location, headers=None):
        self.send_response(303)
        self.send_header("Location", location)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def send_json(self, content):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, request_path):
        file_path = (ROOT / request_path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
            self.not_found()
            return
        content_types = {
            ".css": "text/css; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
        }
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def common_context(self, user):
        return {"auth_nav": build_auth_nav(user)}

    def home(self, user):
        stats = build_stats()
        self.write_html(
            render(
                "Home",
                {
                    **self.common_context(user),
                    **stats,
                    "event_cards": build_event_cards(),
                    "transaction_list": build_transaction_list(limit_user(user)),
                },
            )
        )

    def login_page(self, user, alert=""):
        self.write_html(render("Login", {**self.common_context(user), "alert": alert}))

    def register_page(self, user, alert=""):
        self.write_html(render("Registrasi", {**self.common_context(user), "alert": alert}))

    def events_page(self, user):
        stats = build_stats()
        self.write_html(render("Tampilan Event", {**self.common_context(user), **stats, "event_cards": build_event_cards()}))

    def donation_page(self, user, query, alert=""):
        selected = query.get("event", [""])[0]
        donor_name = user["name"] if user else ""
        self.write_html(
            render(
                "Donasi",
                {
                    **self.common_context(user),
                    "alert": alert,
                    "event_options": build_event_options(selected),
                    "donor_name": esc(donor_name),
                    "disabled": "" if user else "disabled",
                    "login_notice": "" if user else '<p class="form-note">Kamu harus login dulu sebelum transaksi.</p>',
                },
            )
        )

    def process_page(self, user, query):
        reference = query.get("ref", [""])[0]
        transaction = None
        if reference:
            with connect_db() as db:
                transaction = db.execute(
                    """
                    SELECT t.*, e.title AS event_title
                    FROM transactions t
                    JOIN events e ON e.id = t.event_id
                    WHERE t.reference = ?
                    """,
                    (reference,),
                ).fetchone()
        context = {
            **self.common_context(user),
            "reference": esc(reference or "-"),
            "event_title": esc(transaction["event_title"] if transaction else "Belum ada transaksi"),
            "amount": rupiah(transaction["amount"]) if transaction else rupiah(0),
            "status": esc(transaction["status"] if transaction else "MENUNGGU"),
            "transaction_list": build_transaction_list(limit_user(user)),
        }
        self.write_html(render("Proses Transaksi", context))

    def total_page(self, user):
        stats = build_stats()
        self.write_html(
            render(
                "Total Donasi",
                {
                    **self.common_context(user),
                    **stats,
                    "transaction_list": build_transaction_list(None),
                },
            )
        )

    def handle_login(self, form):
        email = form.get("email", "").lower()
        password = form.get("password", "")
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            self.login_page(None, '<div class="alert error">Email atau password belum cocok.</div>')
            return
        header = f"hexacare_session={sign_value(str(user['id']))}; HttpOnly; Path=/; SameSite=Lax"
        self.redirect("/", {"Set-Cookie": header})

    def handle_register(self, form):
        name = form.get("name", "")
        email = form.get("email", "").lower()
        password = form.get("password", "")
        if len(name) < 2 or len(password) < 6 or "@" not in email:
            self.register_page(None, '<div class="alert error">Isi nama, email valid, dan password minimal 6 karakter.</div>')
            return
        try:
            with connect_db() as db:
                cursor = db.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, hash_password(password), int(time.time())),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            self.register_page(None, '<div class="alert error">Email sudah terdaftar. Silakan login.</div>')
            return
        header = f"hexacare_session={sign_value(str(user_id))}; HttpOnly; Path=/; SameSite=Lax"
        self.redirect("/", {"Set-Cookie": header})

    def handle_transaction(self, user, form):
        if not user:
            self.redirect("/Login/")
            return
        try:
            amount = int(form.get("amount", "0"))
            event_id = int(form.get("event_id", "0"))
        except ValueError:
            self.donation_page(user, {"event": [""]}, '<div class="alert error">Nominal donasi belum valid.</div>')
            return
        if amount < 10000:
            self.donation_page(user, {"event": [""]}, '<div class="alert error">Minimal donasi Rp10.000.</div>')
            return

        reference = f"HC-{int(time.time())}-{secrets.token_hex(3).upper()}"
        donor_name = form.get("donor_name") or user["name"]
        payment_method = form.get("payment_method", "Transfer Bank")
        note = form.get("note", "")

        with connect_db() as db:
            event = db.execute("SELECT id FROM events WHERE id = ? AND status = 'ACTIVE'", (event_id,)).fetchone()
            if not event:
                self.donation_page(user, {"event": [""]}, '<div class="alert error">Event tidak ditemukan.</div>')
                return
            db.execute(
                """
                INSERT INTO transactions
                (reference, user_id, event_id, donor_name, amount, payment_method, note, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'SUCCESS', ?)
                """,
                (reference, user["id"], event_id, donor_name, amount, payment_method, note, int(time.time())),
            )
        self.redirect(f"/Proses-Transaksi/?ref={quote(reference)}")

    def logout(self):
        self.redirect("/", {"Set-Cookie": "hexacare_session=; Max-Age=0; HttpOnly; Path=/; SameSite=Lax"})

    def not_found(self):
        self.write_html(render("Home", {"auth_nav": build_auth_nav(None), "event_cards": "", "transaction_list": ""}), status=404)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def limit_user(user):
    return user["id"] if user else None


if __name__ == "__main__":
    init_db()
    local_url = f"http://127.0.0.1:{PORT}/"
    print(f"HexaCare running at {local_url}")
    if os.environ.get("OPEN_BROWSER") == "1":
        threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()
    ThreadingHTTPServer((HOST, PORT), HexaCareHandler).serve_forever()

