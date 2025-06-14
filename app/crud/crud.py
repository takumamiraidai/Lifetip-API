from sqlalchemy.orm import Session
from app.models import models, schemas
from typing import List, Optional

# ユーザー関連のCRUD操作
def get_user(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(user_id=user.user_id)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user(db: Session, user_id: str):
    user = get_user(db, user_id)
    if not user:
        user = create_user(db, schemas.UserCreate(user_id=user_id))
    return user

# エージェント関連のCRUD操作
def get_agent(db: Session, agent_id: str):
    return db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()

def get_agents_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.Agent).filter(models.Agent.user_id == user_id).offset(skip).limit(limit).all()

def create_agent(db: Session, agent: schemas.AgentCreate, user_id: str):
    # ユーザーが存在しない場合は作成
    get_or_create_user(db, user_id)
    
    db_agent = models.Agent(
        user_id=user_id,
        name=agent.name,
        tone=agent.tone,
        personality1=agent.personality1,
        personality2=agent.personality2
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def update_agent(db: Session, agent_id: str, agent: schemas.AgentUpdate):
    db_agent = get_agent(db, agent_id)
    if db_agent:
        update_data = agent.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_agent, key, value)
        db.commit()
        db.refresh(db_agent)
    return db_agent

def delete_agent(db: Session, agent_id: str):
    db_agent = get_agent(db, agent_id)
    if db_agent:
        db.delete(db_agent)
        db.commit()
        return True
    return False

# 会話履歴関連のCRUD操作
def create_conversation(db: Session, user_id: str, agent_id: str, user_message: str, agent_response: str):
    db_conversation = models.Conversation(
        user_id=user_id,
        agent_id=agent_id,
        user_message=user_message,
        agent_response=agent_response
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def get_conversations(db: Session, user_id: str, agent_id: str, limit: int = 5):
    return db.query(models.Conversation)\
        .filter(models.Conversation.user_id == user_id, models.Conversation.agent_id == agent_id)\
        .order_by(models.Conversation.created_at.desc())\
        .limit(limit)\
        .all()