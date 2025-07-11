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
                timeout=120.0  # チャットAPI呼び出しのタイムアウトを延長（2分）
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Chat API error: {response.text}")
                
            return response.json()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call chat API: {str(e)}")

async def create_audio_query(text, speaker):
    """
    テキストから音声クエリを生成する
    """
    print(f"Creating audio query with speaker ID: {speaker}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUDIO_QUERY_API_URL}?text={text}&speaker={speaker}",
                headers={"accept": "application/json"},
                timeout=60.0  # 音声クエリAPIのタイムアウトを延長（1分）
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
                timeout=60.0  # 音声合成APIのタイムアウトを延長（1分）
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
    
    # エージェントの音声タイプとスピーカーIDを取得
    speaker_id = 1  # デフォルト値
    voice_type = "voicevox"  # デフォルト値
    use_custom_voice = False
    
    if agent_id:
        from app.db.database import get_db
        from app.crud import crud
        db = next(get_db())
        db_agent = crud.get_agent(db, agent_id=agent_id)
        if db_agent:
            # 音声タイプとカスタム音声設定を取得
            if db_agent.voice_speaker_id:
                speaker_id = db_agent.voice_speaker_id
            if db_agent.voice_type:
                voice_type = db_agent.voice_type
            if db_agent.has_custom_voice:
                use_custom_voice = bool(db_agent.has_custom_voice)
            
            print(f"Agent voice settings: type={voice_type}, custom={use_custom_voice}, speaker_id={speaker_id}")
    
    # カスタム音声を使用するか判断
    audio_result = None
    if voice_type == "custom" and use_custom_voice:
        print(f"カスタム音声合成を使用: agent_id={agent_id}")
        try:
            # 外部音声合成サービスを呼び出す
            import uuid
            import aiofiles
            import base64
            import asyncio
            
            AUDIO_DIR = "audio_files"
            VOICE_SYNTHESIS_URL = os.getenv("CUSTOM_VOICE_API_URL", "http://localhost:8000")
            
            # カスタム音声合成リクエスト
            synthesis_data = {
                'text': response_text,
                'wav_filename': f"{agent_id}.wav",
                'language': 'ja'
            }
            
            generate_url = f"{VOICE_SYNTHESIS_URL}/generate"
            print(f"カスタム音声合成リクエスト: {generate_url}")
            print(f"音声合成パラメータ: {synthesis_data}")
            
            # 非同期HTTPクライアントを使用
            async with httpx.AsyncClient() as client:
                try:
                    print(f"音声合成リクエスト送信中: {generate_url}")
                    synthesis_response = await client.post(
                        generate_url,
                        data=synthesis_data,
                        timeout=120.0  # カスタム音声合成のタイムアウトを延長（2分）
                    )
                    
                    if synthesis_response.status_code == 200:
                        # 音声ファイルを保存
                        output_filename = f"generated_{agent_id}_{uuid.uuid4().hex[:8]}.wav"
                        filepath = os.path.join(AUDIO_DIR, output_filename)
                        
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(synthesis_response.content)
                        
                        # Base64エンコードされた音声データを返す
                        audio_data_base64 = base64.b64encode(synthesis_response.content).decode('utf-8')
                        
                        audio_result = {
                            "filepath": filepath,
                            "audio_data": audio_data_base64
                        }
                        print(f"音声合成完了: {output_filename}")
                        print(f"カスタム音声合成成功: {filepath}")
                    else:
                        print(f"カスタム音声合成エラー: {synthesis_response.status_code}")
                        raise Exception(f"カスタム音声合成エラー: {synthesis_response.status_code} {synthesis_response.text}")
                except httpx.TimeoutException as timeout_err:
                    print(f"音声合成API接続エラー: {str(timeout_err)}")
                    raise Exception(f"音声合成タイムアウト: {str(timeout_err)}")
                except Exception as req_err:
                    print(f"リクエスト例外: {str(req_err)}")
                    raise Exception(f"リクエスト例外: {str(req_err)}")
        except Exception as custom_err:
            print(f"カスタム音声合成例外: {str(custom_err)}。VoiceVoxにフォールバックを試行します。")
    
    # カスタム音声合成に失敗したか、そもそもカスタム音声を使用しない場合はVoiceVoxを使用
    if audio_result is None:
        try:
            print(f"VoiceVox音声合成を使用: speaker_id={speaker_id}")
            # 音声クエリを生成
            audio_query = await create_audio_query(response_text, speaker=speaker_id)
            
            # 音声を合成
            audio_result = await synthesize_speech(audio_query, speaker=speaker_id)
        except Exception as voicevox_err:
            print(f"VoiceVox合成エラー: {str(voicevox_err)}")
            # 最終的なフォールバック: 音声なしでテキストだけ返す
            return {
                "text": response_text,
                "audio_path": "",
                "audio_data": ""  # 音声データなし
            }
    
    # 結果を返す
    return {
        "text": response_text,
        "audio_path": audio_result["filepath"],
        "audio_data": audio_result["audio_data"]
    }