import uvicorn
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    # タイムアウト設定を追加
    uvicorn.run(
        "app.main:app", 
        host=host, 
        port=port, 
        reload=True,
        timeout_keep_alive=300,  # キープアライブタイムアウトを5分に設定
    )