from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import schemas
from app.crud import crud
from app.services import api_service
import os
from typing import Optional, List
import asyncio

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/{agent_id}", response_model=schemas.ChatResponse)
async def chat_with_agent(
    agent_id: str,
    chat_request: schemas.ChatRequest,
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
    
    try:
        # チャットAPIと音声APIを呼び出す（タイムアウトを設定）
        result = await asyncio.wait_for(
            api_service.process_chat_and_voice(messages, chat_request.user_id, agent_id),
            timeout=180.0  # クライアント側と同じ3分のタイムアウト
        )
        
        # 会話履歴を保存（ユーザーIDが提供されている場合）
        if chat_request.user_id:
            crud.create_conversation(
                db, 
                user_id=chat_request.user_id,
                agent_id=agent_id,
                user_message=chat_request.user_message,
                agent_response=result["text"]
            )
        
        # 音声ファイルのURLを生成
        audio_filename = os.path.basename(result["audio_path"])
        audio_url = f"/audio/{audio_filename}"
        
        return {
            "text": result["text"],
            "audio_url": audio_url,
            "audio_data": result["audio_data"]  # Base64エンコードされた音声データを返す
        }
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,  # Gateway Timeout
            detail="処理に時間がかかりすぎています。もう少し短いメッセージでお試しください。"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"内部サーバーエラー: {str(e)}"
        )

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = os.path.join("audio_files", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/wav")