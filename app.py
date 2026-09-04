"""
帳號申請系統 - Flask + SQLite
提供簡單的網頁 UI 讓使用者填寫: 姓名、工號、帳號、密碼、電話
這個應用被設計成可容器化並部署到 Kubernetes,用來練習 CI/CD。
"""
import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# SECRET_KEY 用於 flash 訊息;正式環境請用環境變數注入
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# 資料庫路徑。部署到 k8s 時可用環境變數指向掛載的 volume,
# 這樣 Pod 重啟或滾動更新時資料才不會遺失。
DB_PATH = os.environ.get("DB_PATH", "accounts.db")

# 版本號:方便你在滾動更新時,從網頁上肉眼看到新版本已上線
APP_VERSION = os.environ.get("APP_VERSION", "v1.0.0")


def get_db():
    """取得目前請求的資料庫連線(每個請求共用一條連線)。"""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """請求結束時關閉資料庫連線。"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """建立資料表(若不存在)。應用啟動時呼叫。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emp_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/", methods=["GET"])
def index():
    """顯示申請表單。"""
    return render_template("register.html", version=APP_VERSION)


@app.route("/register", methods=["POST"])
def register():
    """處理表單送出,寫入資料庫。"""
    name = request.form.get("name", "").strip()
    emp_id = request.form.get("emp_id", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    phone = request.form.get("phone", "").strip()

    # 基本欄位驗證
    if not all([name, emp_id, username, password, phone]):
        flash("所有欄位皆為必填", "error")
        return redirect(url_for("index"))

    if len(password) < 6:
        flash("密碼長度至少 6 碼", "error")
        return redirect(url_for("index"))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO accounts (name, emp_id, username, password_hash, phone) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, emp_id, username, generate_password_hash(password), phone),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # 工號或帳號重複
        flash("工號或帳號已存在", "error")
        return redirect(url_for("index"))

    return render_template("success.html", name=name, username=username, version=APP_VERSION)


@app.route("/accounts", methods=["GET"])
def list_accounts():
    """簡單列出已申請的帳號(不含密碼),方便你確認資料有寫入。"""
    db = get_db()
    rows = db.execute(
        "SELECT id, name, emp_id, username, phone, created_at "
        "FROM accounts ORDER BY id DESC"
    ).fetchall()
    return render_template("accounts.html", accounts=rows, version=APP_VERSION)


@app.route("/healthz", methods=["GET"])
def healthz():
    """健康檢查端點,給 k8s 的 liveness / readiness probe 使用。"""
    return {"status": "ok", "version": APP_VERSION}, 200


# 應用啟動時就把資料表建好(在 gunicorn 匯入模組時也會執行)
init_db()


if __name__ == "__main__":
    # 本地開發用;正式環境用 gunicorn 啟動
    app.run(host="0.0.0.0", port=5000, debug=True)
