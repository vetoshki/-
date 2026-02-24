import asyncio
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base
from app.database import engine
from app import models


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(models.Role))
        if result.scalars().first():
            print("База уже инициализирована")
            return

        roles = [
            models.Role(code="user", name="Пользователь"),
            models.Role(code="specialist", name="Специалист"),
            models.Role(code="admin", name="Администратор"),
        ]
        session.add_all(roles)

        statuses = [
            models.TicketStatus(code="open", name="Открыта"),
            models.TicketStatus(code="in_work", name="В работе"),
            models.TicketStatus(code="done", name="Выполнена"),
            models.TicketStatus(code="closed", name="Закрыта"),
        ]
        session.add_all(statuses)

        await session.flush()

        admin_role = (await session.execute(
            select(models.Role).where(models.Role.code == "admin")
        )).scalar_one()

        specialist_role = (await session.execute(
            select(models.Role).where(models.Role.code == "specialist")
        )).scalar_one()

        user_role = (await session.execute(
            select(models.Role).where(models.Role.code == "user")
        )).scalar_one()

        users = [
            models.User(
                email="admin@example.com",
                password_hash=hash_password("password123"),
                full_name="Администратор Системы",
                role_id=admin_role.id,
                is_active=True,
            ),
            models.User(
                email="specialist@example.com",
                password_hash=hash_password("password123"),
                full_name="Иванов Иван Иванович",
                role_id=specialist_role.id,
                is_active=True,
            ),
            models.User(
                email="user@example.com",
                password_hash=hash_password("password123"),
                full_name="Петров Петр Петрович",
                role_id=user_role.id,
                is_active=True,
            ),
        ]
        session.add_all(users)

        kb = [
            models.KnowledgeItem(
                problem="Не включается компьютер",
                solution="Проверить питание и кабель, затем нажать кнопку включения",
                frequency=5,
                is_auto_generated=False,
            ),
            models.KnowledgeItem(
                problem="Медленно работает интернет",
                solution="Перезагрузить роутер и проверить кабель",
                frequency=3,
                is_auto_generated=False,
            ),
            models.KnowledgeItem(
                problem="Принтер не печатает",
                solution="Проверить подключение, очередь печати и драйвер",
                frequency=2,
                is_auto_generated=False,
            ),
        ]
        session.add_all(kb)

        await session.commit()
        print("База данных создана")


if __name__ == "__main__":
    asyncio.run(init_db())
