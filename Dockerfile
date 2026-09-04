# 使用輕量的 Python 官方映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 先複製依賴清單並安裝(利用 Docker layer 快取,程式碼改動時不必重裝套件)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY app.py .
COPY templates/ ./templates/

# 建立資料庫要用的資料夾,否則 SQLite 開檔會失敗
RUN mkdir -p /app/data

# 用非 root 使用者執行,較安全
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 容器對外開放 5000 埠
EXPOSE 5000

# 資料庫路徑(可被 k8s 環境變數覆寫指向 volume)
ENV DB_PATH=/app/data/accounts.db

# 用 gunicorn 啟動,2 個 worker;app:app 代表 app.py 裡的 app 物件
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
