from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Pet, PetType, User
from app.schemas import PetCreate, PetOut, PetTypeOut
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=PetOut)
def create_pet(
    pet: PetCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ensure the user_id matches the current user
    pet_data = pet.dict()
    pet_data['user_id'] = current_user.id
    db_pet = Pet(**pet_data)
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

@router.get("/", response_model=list[PetOut])
def list_pets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Pet).filter(Pet.user_id == current_user.id).all()

@router.get("/types", response_model=list[PetTypeOut])
def list_pet_types(db: Session = Depends(get_db)):
    return db.query(PetType).all()

@router.get("/{pet_id}", response_model=PetOut)
def get_pet(
    pet_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_pet = db.query(Pet).filter(Pet.id == pet_id, Pet.user_id == current_user.id).first()
    if not db_pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return db_pet
