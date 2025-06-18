from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    agents = relationship("Agent", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

class Agent(Base):
    __tablename__ = "agents"
    
    agent_id = Column(String, primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"))
    name = Column(String, nullable=False)
    tone = Column(String, nullable=False)  # 口調
    personality1 = Column(String, nullable=False)  # 性格1
    personality2 = Column(String, nullable=True)   # 性格2
    voice_type = Column(String, default="voicevox") # 音声タイプ: "voicevox" または "custom"
    has_custom_voice = Column(Integer, default=0)  # カスタム音声を持っているかどうか (0=False, 1=True)
    voice_speaker_id = Column(Integer, default=1)  # VoiceVoxのスピーカーID
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    user = relationship("User", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    user_message = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # リレーションシップ
    user = relationship("User", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")