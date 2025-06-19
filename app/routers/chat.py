from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import schemas
from app.crud import crud
from app.services import api_service
import os
from typing import Optional, List

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/{agent_id}", response_model=schemas.ChatResponse)
async def chat_with_agent(
    agent_id: str,
    chat_request: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # エージェントの存在確認
    agent = crud.get_agent(db, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # メッセージ履歴の取得（ユーザーIDが提供されている場合）
    message_history = []
    if chat_request.user_id:
        conversations = crud.get_conversations(
            db, 
            user_id=chat_request.user_id, 
            agent_id=agent_id, 
            limit=5
        )
        
        for conv in reversed(conversations):
            message_history.append({"role": "user", "content": conv.user_message})
            message_history.append({"role": "assistant", "content": conv.agent_response})
    
    # システムプロンプトの作成
    system_prompt = f"あなたは{agent.personality1}"
    if agent.personality2:
        system_prompt += f"かつ{agent.personality2}"
    system_prompt += f"なAIです。{agent.tone}な口調で話してください。"
    
    # メッセージの作成
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(message_history)
    messages.append({"role": "user", "content": chat_request.user_message})
    
    # カスタム音声合成を使用するかチェック
    use_custom_voice = False
    if agent.voice_type == "custom" and agent.has_custom_voice:
        use_custom_voice = True
    
    # 高速レスポンスモード - テキスト生成のみを先に実行
    # まずテキスト応答だけを取得
    text_result = await api_service.generate_chat_response(messages)
    
    # 会話履歴を保存（ユーザーIDが提供されている場合）
    if chat_request.user_id:
        crud.create_conversation(
            db, 
            user_id=chat_request.user_id,
            agent_id=agent_id,
            user_message=chat_request.user_message,
            agent_response=text_result
        )
    
    # 音声合成を非同期で実行（バックグラウンドタスク）
    audio_filename = f"processing_{agent_id}_{os.urandom(4).hex()}.wav"
    audio_url = f"/audio/{audio_filename}"
    
    # 音声合成を実行（バックグラウンドで）
    if use_custom_voice:
        print(f"カスタム音声合成をバックグラウンドで実行: agent_id={agent_id}")
        # 合成が完了したら他のタスクをするためにスピーカーIDも渡す
        background_tasks.add_task(
            api_service.synthesize_voice_background, 
            text_result, 
            agent_id, 
            agent.voice_speaker_id,
            "custom"
        )
        # カスタム音声合成中と表示するための特別なレスポンス
        return {
            "text": text_result,
            "audio_url": "/processing",  # 特別な値で処理中を表す
            "audio_data": None,  # カスタム音声は時間がかかるのでまずNullを返す
            "processing": True   # 処理中フラグ
        }
    else:
        # 通常のVoiceVox音声合成（これは比較的早いので、同期的に実行）
        result = await api_service.process_text_to_voice(text_result, agent_id, agent.voice_speaker_id)
        
        # 音声ファイルのURLを生成
        audio_filename = os.path.basename(result["filepath"])
        audio_url = f"/audio/{audio_filename}"
        
        return {
            "text": text_result,
            "audio_url": audio_url,
            "audio_data": result["audio_data"]  # Base64エンコードされた音声データ
        }

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = os.path.join("audio_files", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/wav")