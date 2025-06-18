from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.routers import users, agents, chat, voice
from app.db.database import engine
from app.models import models

# 環境変数の読み込み
load_dotenv()

# データベーステーブルの作成
models.Base.metadata.create_all(bind=engine)

# 音声ファイル用ディレクトリの作成
os.makedirs("audio_files", exist_ok=True)

app = FastAPI(
    title="Agent Chat API",
    description="FastAPIとSQLiteを使用したエージェントチャットAPI",
    version="1.0.0"
)

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # ローカル開発環境
        "https://dutch-surgical-speech-bandwidth.trycloudflare.com",  # Cloudflare Tunnelドメイン
        "https://yesterday-warcraft-older-produced.trycloudflare.com",  # 現在のCloudflare Tunnelドメイン
        "https://*.trycloudflare.com",  # すべてのCloudflare Tunnelドメイン
        "https://*.pages.dev",  # Cloudflare Pagesドメイン
        "*",  # すべてのオリジン（開発中のみ推奨）
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 静的ファイルの提供設定
app.mount("/audio", StaticFiles(directory="audio_files"), name="audio")

# ルーターの登録
app.include_router(users.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(voice.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Agent Chat API"}

# アプリケーションの起動設定
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)