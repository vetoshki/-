import hashlib
from typing import List

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from . import models
from . import schemas
from .database import get_db
from .ml_logic import get_recommendations


app = FastAPI(title="Система управления заявками")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


async def get_user(db: AsyncSession, user_id: int) -> models.User:
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.role))
        .where(models.User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

    return user


def require_role(user: models.User, role_code: str) -> None:
    if user.role.code not in [role_code, "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -------------------- АВТОРИЗАЦИЯ --------------------

@app.post("/api/login")
async def login(data: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.role))
        .where(models.User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if user.password_hash != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role.code,
    }


@app.get("/api/users/me")
async def get_me(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.code,
    }


# -------------------- ЗАЯВКИ --------------------

@app.post("/api/tickets", response_model=schemas.TicketResponse)
async def create_ticket(
    data: schemas.TicketCreate,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "user")

    ticket = models.Ticket(
        description=data.description,
        contact_info=data.contact_info,
        status_id=1,
        client_user_id=user.id,
    )

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return ticket


@app.get("/api/tickets/my", response_model=List[schemas.TicketResponse])
async def my_tickets(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)
    require_role(user, "user")

    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.client_user_id == user.id)
        .order_by(models.Ticket.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/tickets/open", response_model=List[schemas.TicketResponse])
async def open_tickets(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)
    require_role(user, "specialist")

    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.status_id == 1)
        .order_by(models.Ticket.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/tickets/assigned", response_model=List[schemas.TicketResponse])
async def assigned_tickets(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)
    require_role(user, "specialist")

    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.status_id == 2)
        .where(models.Ticket.specialist_user_id == user.id)
        .order_by(models.Ticket.created_at.desc())
    )
    return result.scalars().all()


@app.put("/api/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "specialist")

    result = await db.execute(
        select(models.Ticket).where(models.Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if ticket.status_id != 1:
        raise HTTPException(status_code=400, detail="Заявка уже в работе")

    ticket.status_id = 2
    ticket.specialist_user_id = user.id

    await db.commit()

    return {"message": "Заявка взята в работу"}


@app.get("/api/tickets/{ticket_id}/recommendations")
async def ticket_recommendations(
    ticket_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "specialist")

    result = await db.execute(
        select(models.Ticket).where(models.Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    result = await db.execute(
        select(models.KnowledgeItem)
        .order_by(models.KnowledgeItem.frequency.desc())
        .limit(100)
    )
    kb_items = result.scalars().all()

    kb_data = [
        {"id": i.id, "problem": i.problem, "solution": i.solution}
        for i in kb_items
    ]

    rec_data = get_recommendations(ticket.description, kb_data)

    for rec in rec_data["recommendations"]:
        db.add(
            models.TicketRecommendation(
                ticket_id=ticket.id,
                kb_item_id=rec["kb_id"],
                similarity=rec["similarity"],
                rank=rec["rank"],
            )
        )

    await db.commit()

    return {
        "ticket_id": ticket.id,
        "description": ticket.description,
        "contact_info": ticket.contact_info,
        "status_id": ticket.status_id,
        "is_novel": rec_data["is_novel"],
        "max_similarity": rec_data["max_similarity"],
        "recommendations": rec_data["recommendations"],
    }


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: int,
    data: schemas.ResolveRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "specialist")

    result = await db.execute(
        select(models.Ticket).where(models.Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if ticket.status_id != 2:
        raise HTTPException(status_code=400, detail="Заявка не в работе")

    ticket.status_id = 3
    added_to_kb = False

    if data.used_kb and data.accepted_kb_id:
        result = await db.execute(
            select(models.KnowledgeItem)
            .where(models.KnowledgeItem.id == data.accepted_kb_id)
        )
        kb_item = result.scalar_one_or_none()

        if kb_item:
            kb_item.frequency += 1

        await db.execute(
            update(models.TicketRecommendation)
            .where(models.TicketRecommendation.ticket_id == ticket.id)
            .where(models.TicketRecommendation.kb_item_id == data.accepted_kb_id)
            .values(was_accepted=True)
        )

    else:
        if not data.applied_solution.strip():
            raise HTTPException(status_code=400, detail="Введите решение")

        result = await db.execute(
            select(models.KnowledgeItem)
            .where(models.KnowledgeItem.solution.ilike(
                f"%{data.applied_solution[:50]}%"
            ))
        )
        exists = result.scalar_one_or_none()

        if not exists:
            db.add(
                models.KnowledgeItem(
                    problem=ticket.description[:1000],
                    solution=data.applied_solution,
                    frequency=1,
                    is_auto_generated=True,
                )
            )
            added_to_kb = True

    await db.commit()

    return {"message": "Заявка выполнена", "added_to_kb": added_to_kb}


@app.post("/api/tickets/{ticket_id}/confirm")
async def confirm_ticket(
    ticket_id: int,
    data: schemas.ConfirmRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "user")

    result = await db.execute(
        select(models.Ticket).where(models.Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if ticket.client_user_id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    if ticket.status_id != 3:
        raise HTTPException(status_code=400, detail="Заявка ещё не выполнена")

    if data.is_confirmed:
        ticket.status_id = 4
        msg = "Заявка закрыта"
    else:
        ticket.status_id = 2
        ticket.specialist_user_id = None
        msg = "Заявка возвращена в работу"

    await db.commit()
    return {"message": msg}


# -------------------- БАЗА ЗНАНИЙ --------------------

@app.get("/api/knowledge", response_model=List[schemas.KnowledgeItemResponse])
async def get_knowledge(
    user_id: int,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    require_role(user, "admin")

    result = await db.execute(
        select(models.KnowledgeItem)
        .order_by(models.KnowledgeItem.frequency.desc())
        .limit(limit)
    )
    return result.scalars().all()


# -------------------- СТАТИСТИКА --------------------

@app.get("/api/stats")
async def get_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)
    require_role(user, "admin")

    result = await db.execute(select(func.count(models.Ticket.id)))
    tickets_total = result.scalar() or 0

    result = await db.execute(
        select(func.count(models.Ticket.id))
        .where(models.Ticket.status_id == 1)
    )
    tickets_open = result.scalar() or 0

    result = await db.execute(select(func.count(models.KnowledgeItem.id)))
    knowledge_total = result.scalar() or 0

    result = await db.execute(select(func.sum(models.KnowledgeItem.frequency)))
    knowledge_usage = result.scalar() or 0

    return {
        "tickets_total": tickets_total,
        "tickets_open": tickets_open,
        "knowledge_total": knowledge_total,
        "knowledge_usage": knowledge_usage,
    }
