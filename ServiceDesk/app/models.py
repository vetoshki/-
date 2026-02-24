from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now())

    role = relationship("Role")


class TicketStatus(Base):
    __tablename__ = "ticket_statuses"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    description = Column(Text, nullable=False)
    contact_info = Column(String(500), nullable=False)

    status_id = Column(Integer, ForeignKey("ticket_statuses.id"), nullable=False)
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    specialist_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
    )

    status = relationship("TicketStatus")
    client = relationship("User", foreign_keys=[client_user_id])
    specialist = relationship("User", foreign_keys=[specialist_user_id])


class KnowledgeItem(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)

    problem = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)

    frequency = Column(Integer, default=0)
    is_auto_generated = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP, server_default=func.now())


class TicketRecommendation(Base):
    __tablename__ = "ticket_recommendations"

    id = Column(Integer, primary_key=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    kb_item_id = Column(Integer, ForeignKey("knowledge_base.id"), nullable=False)

    similarity = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)

    was_accepted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    ticket = relationship("Ticket")
    kb_item = relationship("KnowledgeItem")
