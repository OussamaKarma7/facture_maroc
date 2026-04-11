from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.identity import User, Company, CompanyUser, RoleEnum
from app.schemas.auth import UserCreate
from app.utils.security import get_password_hash

async def register_user_and_company(db: AsyncSession, user_in: UserCreate) -> User:
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # 1. Create User
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True
    )
    db.add(new_user)
    await db.flush() # flush to get new_user.id

    # 2. Create Company
    new_company = Company(
        name=user_in.company_name,
        ice=user_in.company_ice,
        tax_id=user_in.company_if
    )
    db.add(new_company)
    await db.flush()

    # 3. Create CompanyUser link with ADMIN role
    company_user = CompanyUser(
        user_id=new_user.id,
        company_id=new_company.id,
        role=RoleEnum.ADMIN
    )
    db.add(company_user)
    await db.commit()
    await db.refresh(new_user)

    # Initialiser le Plan Comptable Marocain pour la nouvelle entreprise
    from app.services.pcm import initialize_pcm
    await initialize_pcm(db, new_company.id)

    return new_user
