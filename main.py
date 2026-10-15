import os
import re
import time

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Text,
    DateTime,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    Session,
)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


# --------------------------------------------------
# Database
# --------------------------------------------------

DB = os.getenv(
    "DATABASE_URL",
    "sqlite:///./restaurant_ai.db"
)

engine = create_engine(
    DB,
    connect_args={
        "check_same_thread": False
    } if DB.startswith("sqlite") else {},
    pool_pre_ping=True,
)


class Base(DeclarativeBase):
    pass


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    guest_name: Mapped[str] = mapped_column(
        String(120)
    )

    phone: Mapped[str] = mapped_column(
        String(50)
    )

    party_size: Mapped[int] = mapped_column(
        Integer
    )

    date: Mapped[str] = mapped_column(
        String(20)
    )

    time: Mapped[str] = mapped_column(
        String(20)
    )

    notes: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="confirmed"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


Base.metadata.create_all(engine)


# --------------------------------------------------
# FastAPI App
# --------------------------------------------------

app = FastAPI(
    title="ServeAI Restaurant MVP"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Static Frontend
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


# --------------------------------------------------
# Schemas
# --------------------------------------------------

class RIn(BaseModel):
    guest_name: str = Field(
        min_length=2
    )

    phone: str = Field(
        min_length=5
    )

    party_size: int = Field(
        ge=1,
        le=20
    )

    date: str
    time: str
    notes: str = ""


class CIn(BaseModel):
    message: str = Field(
        min_length=2,
        max_length=1200
    )


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def intent(text):
    text = text.lower()

    if any(
        x in text
        for x in [
            "book",
            "reserve",
            "reservation",
            "table",
        ]
    ):
        return "reservation"

    if any(
        x in text
        for x in [
            "menu",
            "allergy",
            "vegan",
            "gluten",
        ]
    ):
        return "menu_question"

    if any(
        x in text
        for x in [
            "hours",
            "open",
            "close",
            "location",
        ]
    ):
        return "business_info"

    if any(
        x in text
        for x in [
            "complaint",
            "refund",
            "wrong",
            "late",
        ]
    ):
        return "support"

    return "general"


def fallback(intent_name):

    messages = {

        "reservation":
            "I can help with a reservation. "
            "Please provide guest name, phone, party size, date, and time.",

        "menu_question":
            "I can answer menu questions after the approved menu is connected. "
            "I will not invent menu details.",

        "business_info":
            "Business hours and location should come from the restaurant "
            "approved data source.",

        "support":
            "I can capture this issue and escalate it to a staff member.",

        "general":
            "I can help automate reservations, customer questions, "
            "follow-ups, and restaurant workflows.",
    }

    return messages[intent_name]


# --------------------------------------------------
# Frontend Route
# --------------------------------------------------

@app.get("/")
def root():

    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Frontend index.html not found"
        )

    return FileResponse(index_file)


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "ai_mode":
            "openai"
            if os.getenv("OPENAI_API_KEY")
            else "safe-demo",
    }


# --------------------------------------------------
# AI Chat
# --------------------------------------------------

@app.post("/api/chat")
def chat(p: CIn):

    started = time.perf_counter()

    detected_intent = intent(
        p.message
    )

    reply = fallback(
        detected_intent
    )

    source = "safe-demo"

    if (
        os.getenv("OPENAI_API_KEY")
        and OpenAI
    ):

        try:

            client = OpenAI(
                api_key=os.getenv(
                    "OPENAI_API_KEY"
                )
            )

            response = client.responses.create(

                model=os.getenv(
                    "OPENAI_MODEL",
                    "gpt-4o-mini"
                ),

                input=[
                    {
                        "role": "system",
                        "content":
                            "You are a concise restaurant operations assistant. "
                            "Do not invent menu, hours, prices, policies, or availability. "
                            "If data is missing, say it must be connected."
                    },
                    {
                        "role": "user",
                        "content": p.message
                    }
                ],

                timeout=12
            )

            reply = (
                response.output_text
                or reply
            ).strip()

            source = "openai"

        except Exception:
            pass

    return {

        "reply":
            reply,

        "intent":
            detected_intent,

        "source":
            source,

        "latency_ms":
            int(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            ),
    }


# --------------------------------------------------
# Create Reservation
# --------------------------------------------------

@app.post("/api/reservations")
def create(p: RIn):

    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        p.date
    ):

        raise HTTPException(
            status_code=422,
            detail="Date must be YYYY-MM-DD"
        )

    with Session(engine) as session:

        reservation = Reservation(
            **p.model_dump()
        )

        session.add(
            reservation
        )

        session.commit()

        session.refresh(
            reservation
        )

        return {

            "id":
                reservation.id,

            "guest_name":
                reservation.guest_name,

            "party_size":
                reservation.party_size,

            "date":
                reservation.date,

            "time":
                reservation.time,

            "status":
                reservation.status,
        }


# --------------------------------------------------
# Reservation List
# --------------------------------------------------

@app.get("/api/reservations")
def reservations():

    with Session(engine) as session:

        rows = session.scalars(

            select(
                Reservation
            )

            .order_by(
                Reservation.id.desc()
            )

            .limit(20)

        ).all()

        return [

            {

                "id":
                    row.id,

                "guest_name":
                    row.guest_name,

                "party_size":
                    row.party_size,

                "date":
                    row.date,

                "time":
                    row.time,

                "status":
                    row.status,

            }

            for row in rows
        ]


# --------------------------------------------------
# Operations Summary
# --------------------------------------------------

@app.get("/api/ops")
def ops():

    with Session(engine) as session:

        count = len(

            session.scalars(
                select(
                    Reservation
                )
            ).all()

        )

    return {

        "reservations_total":
            count,

        "automation_ideas": [

            {

                "title":
                    "Reservation Agent",

                "impact":
                    "Handle booking requests and reduce missed calls.",

                "status":
                    "Working in MVP",

            },

            {

                "title":
                    "Customer FAQ Agent",

                "impact":
                    "Answer approved FAQs and escalate unknowns.",

                "status":
                    "Needs menu/FAQ data",

            },

            {

                "title":
                    "Manager Daily Brief",

                "impact":
                    "Summarize reservations, issues, and follow-ups.",

                "status":
                    "Needs POS/CRM integration",

            },

        ],

    }
