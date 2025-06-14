from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ユーザー関連のスキーマ
class UserBase(BaseModel):
    user_id: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# エージェント関連のスキーマ
class AgentBase(BaseModel):
    name: str
    tone: str
    personality1: str
    personality2: Optional[str] = None

class AgentCreate(AgentBase):
    pass

class AgentUpdate(AgentBase):
    name: Optional[str] = None
    tone: Optional[str] = None
    personality1: Optional[str] = None
    personality2: Optional[str] = None

class AgentResponse(AgentBase):
    agent_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 会話関連のスキーマ
class ConversationBase(BaseModel):
    user_message: str

class ConversationCreate(ConversationBase):
    pass

class ConversationWithUser(ConversationBase):
    user_id: str

class ConversationResponse(ConversationBase):
    id: int
    user_id: str
    agent_id: str
    agent_response: str
    created_at: datetime

    class Config:
        from_attributes = True

# チャット関連のスキーマ
class ChatRequest(BaseModel):
    user_message: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    text: str
    audio_url: str
    audio_data: Optional[str] = None  # Base64エンコードされた音声データ

# オーディオ関連のスキーマ
class AudioQueryRequest(BaseModel):
    text: str
    speaker: int = 1

class SynthesisRequest(BaseModel):
    audio_query: dict
    speaker: int = 1