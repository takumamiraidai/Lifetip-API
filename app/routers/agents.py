from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import schemas
from app.crud import crud
from typing import List

router = APIRouter(
    prefix="/agents",
    tags=["agents"]
)

@router.post("/{user_id}", response_model=schemas.AgentResponse)
def create_agent(
    user_id: str,
    agent: schemas.AgentCreate,
    db: Session = Depends(get_db)
):
    return crud.create_agent(db=db, agent=agent, user_id=user_id)

@router.get("/{user_id}", response_model=List[schemas.AgentResponse])
def read_agents(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    agents = crud.get_agents_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return agents

@router.get("/detail/{agent_id}", response_model=schemas.AgentResponse)
def read_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    print(f"Fetching agent with ID: {agent_id}")
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        print(f"Agent not found with ID: {agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found")
        
    print(f"Agent found: {db_agent.name}")
    print(f"Voice type: {db_agent.voice_type}")
    print(f"Has custom voice: {db_agent.has_custom_voice}")
    print(f"Voice speaker ID: {db_agent.voice_speaker_id}")
    
    # SQLAlchemyモデルの属性を直接確認
    print(f"Agent attributes: {dir(db_agent)}")
    print(f"Agent __dict__: {db_agent.__dict__}")
    
    # カスタム応答を作成（デバッグ用）
    response = {
        "agent_id": db_agent.agent_id,
        "user_id": db_agent.user_id,
        "name": db_agent.name,
        "tone": db_agent.tone,
        "personality1": db_agent.personality1,
        "personality2": db_agent.personality2,
        "voice_type": db_agent.voice_type,
        "has_custom_voice": bool(db_agent.has_custom_voice),
        "voice_speaker_id": db_agent.voice_speaker_id,
        "created_at": db_agent.created_at,
        "updated_at": db_agent.updated_at
    }
    print(f"Response: {response}")
    
    return db_agent

@router.put("/{agent_id}", response_model=schemas.AgentResponse)
def update_agent(
    agent_id: str,
    agent: schemas.AgentUpdate,
    db: Session = Depends(get_db)
):
    db_agent = crud.update_agent(db, agent_id=agent_id, agent=agent)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    success = crud.delete_agent(db, agent_id=agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return None

@router.get("/debug/{agent_id}")
def debug_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    エージェントの詳細情報をデバッグ用に取得する
    """
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # SQLAlchemyオブジェクトからディクショナリに変換
    agent_data = {
        "agent_id": db_agent.agent_id,
        "user_id": db_agent.user_id,
        "name": db_agent.name,
        "tone": db_agent.tone,
        "personality1": db_agent.personality1,
        "personality2": db_agent.personality2,
        "voice_type": getattr(db_agent, "voice_type", "not_set"),
        "has_custom_voice": getattr(db_agent, "has_custom_voice", "not_set"),
        "voice_speaker_id": getattr(db_agent, "voice_speaker_id", "not_set"),
        "created_at": str(db_agent.created_at),
        "updated_at": str(db_agent.updated_at)
    }
    
    # データベースの生のクエリ結果も取得
    raw_query = db.execute(f"SELECT * FROM agents WHERE agent_id = '{agent_id}'").fetchone()
    raw_data = dict(raw_query) if raw_query else None
    
    # テーブル構造を確認
    table_info = db.execute("PRAGMA table_info(agents)").fetchall()
    columns = [{"cid": col[0], "name": col[1], "type": col[2]} for col in table_info]
    
    return {
        "agent_data": agent_data,
        "raw_data": raw_data,
        "columns": columns,
        "sqlalchemy_dict": {k: str(v) for k, v in db_agent.__dict__.items() if not k.startswith('_')}
    }