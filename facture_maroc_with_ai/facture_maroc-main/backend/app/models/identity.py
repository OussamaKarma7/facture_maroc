import enum
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    ACCOUNTANT = "ACCOUNTANT"
    EMPLOYEE = "EMPLOYEE"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company_associations = relationship("CompanyUser", back_populates="user")

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ice = Column(String)  # Identifiant Commun de l'Entreprise
    tax_id = Column(String)  # Identifiant Fiscal (IF)
    rc = Column(String)  # Registre de Commerce
    address = Column(String)
    logo_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_associations = relationship("CompanyUser", back_populates="company")
    clients = relationship("Client", back_populates="company")
    suppliers = relationship("Supplier", back_populates="company")
    products = relationship("Product", back_populates="company")
    quotes = relationship("Quote", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")

class CompanyUser(Base):
    __tablename__ = "company_users"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.EMPLOYEE, nullable=False)

    user = relationship("User", back_populates="company_associations")
    company = relationship("Company", back_populates="user_associations")
