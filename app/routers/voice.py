from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil
import requests
from typing import Optional
from app.db.database import get_db
from app.crud import crud
from app.models import schemas

router = APIRouter(
    prefix="/voice",
    tags=["voice"]
)

# 音声ファイル保存ディレクトリ
AUDIO_DIR = "audio_files"
VOICE_SYNTHESIS_URL = "http://localhost:8000"  # 音声合成APIのURL

@router.post("/upload")
async def upload_voice(
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """エージェント用の音声ファイルをアップロード"""
    try:
        # ファイル拡張子をチェック
        if not file.filename.lower().endswith(('.wav', '.mp3', '.ogg', '.flac')):
            raise HTTPException(status_code=400, detail="音声ファイル形式が無効です")
        
        # エージェントIDをファイル名にする
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{agent_id}{file_extension}"
        file_path = os.path.join(AUDIO_DIR, filename)
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(AUDIO_DIR, exist_ok=True)
        
        # ファイルを保存
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # エージェントのカスタム音声フラグを更新
        db_agent = crud.get_agent(db, agent_id=agent_id)
        if db_agent:
            # エージェントのvoice_typeとhas_custom_voiceを更新
            update_data = {"has_custom_voice": True}
            for key, value in update_data.items():
                setattr(db_agent, key, value)
            db.commit()
        
        return {
            "message": "音声ファイルのアップロードが完了しました",
            "filename": filename,
            "agent_id": agent_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルアップロードエラー: {str(e)}")

@router.post("/synthesize")
async def synthesize_voice(
    text: str = Form(...),
    agent_id: str = Form(...),
    voice_type: str = Form(default="voicevox")  # "voicevox" or "custom"
):
    """音声合成を実行"""
    try:
        if voice_type == "custom":
            # カスタム音声合成（アップロードされた音声を使用）
            return await synthesize_custom_voice(text, agent_id)
        else:
            # VoiceVox音声合成
            return await synthesize_voicevox(text, agent_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声合成エラー: {str(e)}")

async def synthesize_custom_voice(text: str, agent_id: str):
    """カスタム音声による音声合成"""
    # アップロードされた音声ファイルを確認
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.startswith(agent_id)]
    if not audio_files:
        raise HTTPException(status_code=404, detail="このエージェントの音声ファイルが見つかりません")
    
    reference_audio = audio_files[0]
    reference_path = os.path.join(AUDIO_DIR, reference_audio)
    
    try:
        # 外部音声合成APIに送信
        with open(reference_path, 'rb') as audio_file:
            files = {
                'file': audio_file,
                'filename': (None, agent_id)
            }
            
            # まず音声ファイルをアップロード
            upload_response = requests.post(
                f"{VOICE_SYNTHESIS_URL}/upload",
                files=files
            )
            upload_response.raise_for_status()
        
        # 音声合成を実行
        synthesis_data = {
            'text': text,
            'wav_filename': reference_audio,
            'language': 'ja'
        }
        
        synthesis_response = requests.post(
            f"{VOICE_SYNTHESIS_URL}/generate",
            data=synthesis_data
        )
        synthesis_response.raise_for_status()
        
        # 合成された音声ファイルを保存
        output_filename = f"generated_{agent_id}_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(AUDIO_DIR, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(synthesis_response.content)
        
        return {
            "message": "カスタム音声合成が完了しました",
            "audio_url": f"/audio/{output_filename}",
            "filename": output_filename
        }
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"音声合成サービスとの通信エラー: {str(e)}")

async def synthesize_voicevox(text: str, agent_id: str):
    """VoiceVoxによる音声合成"""
    try:
        # エージェントのスピーカーIDを取得
        from app.db.database import get_db
        db = next(get_db())
        from app.crud import crud
        
        db_agent = crud.get_agent(db, agent_id=agent_id)
        speaker_id = 1  # デフォルト値
        
        print(f"Agent for voice synthesis: {db_agent.name if db_agent else 'Not found'}")
        if db_agent:
            print(f"Agent voice_speaker_id: {db_agent.voice_speaker_id}")
            print(f"Agent voice_speaker_id type: {type(db_agent.voice_speaker_id)}")
        
        if db_agent and db_agent.voice_speaker_id:
            # speaker_idが文字列の場合は整数に変換
            if isinstance(db_agent.voice_speaker_id, str):
                try:
                    speaker_id = int(db_agent.voice_speaker_id)
                    print(f"Converted string speaker_id '{db_agent.voice_speaker_id}' to int: {speaker_id}")
                except ValueError:
                    print(f"Failed to convert speaker_id '{db_agent.voice_speaker_id}' to int, using default")
            else:
                speaker_id = db_agent.voice_speaker_id
            
        print(f"Using speaker_id: {speaker_id} (type: {type(speaker_id)}) for voice synthesis")
        
        # VoiceVoxのAPIエンドポイント（ローカル）
        voicevox_url = "http://localhost:50021"
        
        # 音声クエリを作成
        query_url = f"{voicevox_url}/audio_query"
        query_params = {'text': text, 'speaker': speaker_id}
        print(f"Calling audio_query API: {query_url} with params: {query_params}")
        
        audio_query_response = requests.post(
            query_url,
            params=query_params
        )
        audio_query_response.raise_for_status()
        audio_query = audio_query_response.json()
        
        # 音声合成を実行
        synthesis_url = f"{voicevox_url}/synthesis"
        synthesis_params = {'speaker': speaker_id}
        print(f"Calling synthesis API: {synthesis_url} with params: {synthesis_params}")
        
        synthesis_response = requests.post(
            synthesis_url,
            params=synthesis_params,
            json=audio_query
        )
        synthesis_response.raise_for_status()
        
        # 合成された音声ファイルを保存
        output_filename = f"voicevox_{agent_id}_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(AUDIO_DIR, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(synthesis_response.content)
        
        return {
            "message": "VoiceVox音声合成が完了しました",
            "audio_url": f"/audio/{output_filename}",
            "filename": output_filename
        }
    
    except requests.exceptions.RequestException as e:
        # VoiceVoxが利用できない場合はエラー
        raise HTTPException(status_code=503, detail=f"VoiceVoxサービスが利用できません: {str(e)}")

@router.get("/file/{filename}")
async def get_voice_file(filename: str):
    """音声ファイルを取得"""
    file_path = os.path.join(AUDIO_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="音声ファイルが見つかりません")
    
    return FileResponse(file_path, media_type="audio/wav")

@router.delete("/{agent_id}")
async def delete_voice_files(agent_id: str):
    """エージェントの音声ファイルを削除"""
    try:
        deleted_files = []
        
        # エージェントIDで始まる音声ファイルを削除
        for file in os.listdir(AUDIO_DIR):
            if file.startswith(agent_id):
                file_path = os.path.join(AUDIO_DIR, file)
                os.remove(file_path)
                deleted_files.append(file)
                
        # カスタム音声フラグを更新
        from app.db.database import get_db
        db = next(get_db())
        from app.crud import crud
        
        db_agent = crud.get_agent(db, agent_id=agent_id)
        if db_agent:
            db_agent.has_custom_voice = False
            db.commit()
        
        return {
            "message": "音声ファイルが正常に削除されました",
            "deleted_files": deleted_files
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声ファイル削除エラー: {str(e)}")

@router.get("/voicevox/speakers")
async def get_voicevox_speakers():
    """VoiceVoxの利用可能なスピーカー一覧を取得"""
    try:
        # VoiceVoxのAPIエンドポイント（ローカル）
        voicevox_url = "http://localhost:50021"
        
        # スピーカー一覧を取得
        response = requests.get(f"{voicevox_url}/speakers")
        response.raise_for_status()
        
        return {
            "speakers": response.json()
        }
    
    except requests.exceptions.RequestException as e:
        # VoiceVoxが利用できない場合はモック応答を返す
        mock_speakers = [
            {"id": 1, "name": "四国めたん", "styles": [{"id": 2, "name": "ノーマル"}]},
            {"id": 2, "name": "ずんだもん", "styles": [{"id": 3, "name": "ノーマル"}]},
            {"id": 3, "name": "春日部つむぎ", "styles": [{"id": 8, "name": "ノーマル"}]},
            {"id": 8, "name": "波音リツ", "styles": [{"id": 9, "name": "ノーマル"}]},
            {"id": 10, "name": "玄野武宏", "styles": [{"id": 11, "name": "ノーマル"}]},
        ]
        return {
            "speakers": mock_speakers,
            "info": "VoiceVoxサービスが利用できないため、モックデータを表示しています"
        }
