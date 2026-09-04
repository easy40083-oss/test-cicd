"""
基本測試,CI pipeline 會執行這些測試。
用臨時資料庫,避免污染正式資料。
"""
import os
import tempfile
import pytest

# 測試前先把 DB_PATH 指到暫存檔
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = _tmp_db.name

import app as app_module  # noqa: E402


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    app_module.init_db()
    with app_module.app.test_client() as c:
        yield c


def test_index_page(client):
    """首頁應該正常顯示,且包含表單欄位。"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "帳號申請".encode("utf-8") in resp.data


def test_healthz(client):
    """健康檢查端點應回傳 ok。"""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_register_success(client):
    """填寫完整資料應可成功註冊。"""
    resp = client.post("/register", data={
        "name": "王小明",
        "emp_id": "E10001",
        "username": "ming",
        "password": "secret123",
        "phone": "0912345678",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert "申請成功".encode("utf-8") in resp.data


def test_register_missing_field(client):
    """缺欄位應被擋下並導回首頁。"""
    resp = client.post("/register", data={
        "name": "缺欄位",
        "emp_id": "",
        "username": "x",
        "password": "secret123",
        "phone": "0900000000",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert "必填".encode("utf-8") in resp.data


def test_register_duplicate(client):
    """重複的工號應被拒絕。"""
    data = {
        "name": "第一人",
        "emp_id": "E20002",
        "username": "user_a",
        "password": "secret123",
        "phone": "0911111111",
    }
    client.post("/register", data=data, follow_redirects=True)
    # 換帳號但同工號
    data2 = dict(data, username="user_b")
    resp = client.post("/register", data=data2, follow_redirects=True)
    assert "已存在".encode("utf-8") in resp.data
