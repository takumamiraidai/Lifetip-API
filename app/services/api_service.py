import os
import json
import httpx
from dotenv import load_dotenv
import base64
import uuid
import aiofiles
from fastapi import HTTPException

# 環境変数の読み込み
load_dotenv()

# APIエンドポイント
CHAT_API_URL = os.getenv("CHAT_API_URL")
AUDIO_QUERY_API_URL = os.getenv("AUDIO_QUERY_API_URL")
SYNTHESIS_API_URL = os.getenv("SYNTHESIS_API_URL")

# 音声ファイル保存用のディレクトリ
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

async def create_chat_response(messages):
    """
    チャットAPIを呼び出して応答を取得する
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": "elyza:jp8b",
                "messages": messages,
                "stream": False
            }
            headers = {
                "Content-Type": "application/json",
                "Expect": ""
            }
            
            response = await client.post(
                CHAT_API_URL, 
                json=payload, 
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Chat API error: {response.text}")
                
            return response.json()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call chat API: {str(e)}")

async def create_audio_query(text, speaker=1):
    """
    テキストから音声クエリを生成する
    """
    print(f"Creating audio query with speaker ID: {speaker}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUDIO_QUERY_API_URL}?text={text}&speaker={speaker}",
                headers={"accept": "application/json"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Audio query API error: {response.text}")
                
            return response.json()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call audio query API: {str(e)}")

async def synthesize_speech(audio_query, speaker=1):
    """
    音声クエリから音声を合成する
    """
    try:
        print(f"Synthesizing speech with speaker_id: {speaker}")
        async with httpx.AsyncClient() as client:
            synthesis_url = f"{SYNTHESIS_API_URL}?speaker={speaker}&enable_interrogative_upspeak=true"
            print(f"Calling synthesis API: {synthesis_url}")
            
            response = await client.post(
                synthesis_url,
                headers={
                    "accept": "audio/wav",
                    "Content-Type": "application/json"
                },
                json=audio_query,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Synthesis API error: {response.text}")
            
            # 音声ファイルを保存
            filename = f"{uuid.uuid4()}.wav"
            filepath = f"{AUDIO_DIR}/{filename}"
            
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(response.content)
            
            # Base64エンコードされた音声データを返す
            audio_data_base64 = base64.b64encode(response.content).decode('utf-8')
            
            return {
                "filepath": filepath,
                "audio_data": audio_data_base64
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call synthesis API: {str(e)}")

async def process_chat_and_voice(messages, user_id=None, agent_id=None):
    """
    チャット応答を生成し、それを音声に変換する
    """
    # チャット応答を生成
    chat_response = await create_chat_response(messages)
    
    # レスポンスのテキスト部分を取得
    response_text = chat_response.get("message", {}).get("content", "")
    if not response_text:
        raise HTTPException(status_code=500, detail="No response text received from chat API")
    
    # エージェントのスピーカーIDを取得
    speaker_id = 1  # デフォルト値
    if agent_id:
        from app.db.database import get_db
        from app.crud import crud
        db = next(get_db())
        db_agent = crud.get_agent(db, agent_id=agent_id)
        if db_agent and db_agent.voice_speaker_id:
            speaker_id = db_agent.voice_speaker_id
            print(f"Using agent's voice_speaker_id: {speaker_id} for chat response synthesis")
    
    # 音声クエリを生成
    audio_query = await create_audio_query(response_text)
    
    # 音声を合成
    audio_result = await synthesize_speech(audio_query, speaker=speaker_id)
    
    # 結果を返す
    return {
        "text": response_text,
        "audio_path": audio_result["filepath"],
        "audio_data": audio_result["audio_data"]
    }