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
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
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