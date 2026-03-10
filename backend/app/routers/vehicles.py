from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import ContractVehicle, User
from app.schemas.schemas import (
    ContractVehicle as ContractVehicleSchema,
)
from app.schemas.schemas import (
    ContractVehicleCreate,
    ContractVehiclePatch,
    ContractVehicleUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/vehicles", tags=["contract_vehicles"])


def _check_vehicle_authorization(vehicle: ContractVehicle, current_user: User):
    """Only creator or admin can modify/delete a vehicle."""
    if vehicle.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this contract vehicle",
        )


@router.get("", response_model=List[ContractVehicleSchema])
def get_vehicles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(ContractVehicle).order_by(ContractVehicle.name).offset(skip).limit(limit).all()


@router.get("/{vehicle_id}", response_model=ContractVehicleSchema)
def get_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    vehicle = db.query(ContractVehicle).filter(ContractVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract vehicle not found"
        )
    return vehicle


@router.post("", response_model=ContractVehicleSchema, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle: ContractVehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    new_vehicle = ContractVehicle(
        id=generate_id(),
        name=vehicle.name,
        agency=vehicle.agency,
        contract_number=vehicle.contract_number,
        expiration_date=vehicle.expiration_date,
        ceiling_value=vehicle.ceiling_value,
        prime_or_sub=vehicle.prime_or_sub,
        notes=vehicle.notes,
        created_by_user_id=current_user.id,
    )
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle


@router.put("/{vehicle_id}", response_model=ContractVehicleSchema)
def update_vehicle(
    vehicle_id: str,
    vehicle_update: ContractVehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    vehicle = db.query(ContractVehicle).filter(ContractVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract vehicle not found"
        )

    _check_vehicle_authorization(vehicle, current_user)

    vehicle.name = vehicle_update.name
    vehicle.agency = vehicle_update.agency
    vehicle.contract_number = vehicle_update.contract_number
    vehicle.expiration_date = vehicle_update.expiration_date
    vehicle.ceiling_value = vehicle_update.ceiling_value
    vehicle.prime_or_sub = vehicle_update.prime_or_sub
    vehicle.notes = vehicle_update.notes

    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.patch("/{vehicle_id}", response_model=ContractVehicleSchema)
def patch_vehicle(
    vehicle_id: str,
    updates: ContractVehiclePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    vehicle = db.query(ContractVehicle).filter(ContractVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract vehicle not found"
        )

    _check_vehicle_authorization(vehicle, current_user)

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    vehicle = db.query(ContractVehicle).filter(ContractVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract vehicle not found"
        )

    _check_vehicle_authorization(vehicle, current_user)

    db.delete(vehicle)
    db.commit()
    return None
