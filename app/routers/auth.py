from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from app.database import get_db
from app.models.user import  User
from app.auth.utils import hash_password, verify_password
from app.auth.auth import create_access_token
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str

@router.post("/signup") 
def signup(user : UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username== user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=user.username,
        hashed_password = hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    return {"message": "User created succesfully"}

@router.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}
