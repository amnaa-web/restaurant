import os,re,time
from datetime import datetime
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from sqlalchemy import create_engine,String,Integer,Text,DateTime,select
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,Session
try:
 from openai import OpenAI
except Exception:
 OpenAI=None
DB=os.getenv("DATABASE_URL","sqlite:///./restaurant_ai.db")
engine=create_engine(DB,connect_args={"check_same_thread":False} if DB.startswith("sqlite") else {},pool_pre_ping=True)
class Base(DeclarativeBase): pass
class Reservation(Base):
 __tablename__="reservations"
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 guest_name:Mapped[str]=mapped_column(String(120));phone:Mapped[str]=mapped_column(String(50));party_size:Mapped[int]=mapped_column(Integer);date:Mapped[str]=mapped_column(String(20));time:Mapped[str]=mapped_column(String(20));notes:Mapped[str]=mapped_column(Text,default="");status:Mapped[str]=mapped_column(String(30),default="confirmed");created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)
app=FastAPI(title="ServeAI Restaurant MVP")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
class RIn(BaseModel): guest_name:str=Field(min_length=2);phone:str=Field(min_length=5);party_size:int=Field(ge=1,le=20);date:str;time:str;notes:str=""
class CIn(BaseModel): message:str=Field(min_length=2,max_length=1200)
def intent(t):
 t=t.lower()
 if any(x in t for x in ["book","reserve","reservation","table"]): return "reservation"
 if any(x in t for x in ["menu","allergy","vegan","gluten"]): return "menu_question"
 if any(x in t for x in ["hours","open","close","location"]): return "business_info"
 if any(x in t for x in ["complaint","refund","wrong","late"]): return "support"
 return "general"
def fallback(i):
 return {"reservation":"I can help with a reservation. Please provide guest name, phone, party size, date, and time.","menu_question":"I can answer menu questions after the approved menu is connected. I will not invent menu details.","business_info":"Business hours and location should come from the restaurant approved data source.","support":"I can capture this issue and escalate it to a staff member.","general":"I can help automate reservations, customer questions, follow-ups, and restaurant workflows."}[i]
@app.get("/")
def root(): return {"message":"ServeAI API","docs":"/docs"}
@app.get("/api/health")
def health(): return {"status":"ok","ai_mode":"openai" if os.getenv("OPENAI_API_KEY") else "safe-demo"}
@app.post("/api/chat")
def chat(p:CIn):
 st=time.perf_counter();i=intent(p.message);reply=fallback(i);source="safe-demo"
 if os.getenv("OPENAI_API_KEY") and OpenAI:
  try:
   c=OpenAI(api_key=os.getenv("OPENAI_API_KEY"));r=c.responses.create(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),input=[{"role":"system","content":"You are a concise restaurant operations assistant. Do not invent menu, hours, prices, policies, or availability. If data is missing, say it must be connected."},{"role":"user","content":p.message}],timeout=12);reply=(r.output_text or reply).strip();source="openai"
  except Exception: pass
 return {"reply":reply,"intent":i,"source":source,"latency_ms":int((time.perf_counter()-st)*1000)}
@app.post("/api/reservations")
def create(p:RIn):
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",p.date): raise HTTPException(422,"Date must be YYYY-MM-DD")
 with Session(engine) as s:
  r=Reservation(**p.model_dump());s.add(r);s.commit();s.refresh(r);return {"id":r.id,"guest_name":r.guest_name,"party_size":r.party_size,"date":r.date,"time":r.time,"status":r.status}
@app.get("/api/reservations")
def reservations():
 with Session(engine) as s:
  rows=s.scalars(select(Reservation).order_by(Reservation.id.desc()).limit(20)).all();return [{"id":r.id,"guest_name":r.guest_name,"party_size":r.party_size,"date":r.date,"time":r.time,"status":r.status} for r in rows]
@app.get("/api/ops")
def ops():
 with Session(engine) as s: count=len(s.scalars(select(Reservation)).all())
 return {"reservations_total":count,"automation_ideas":[{"title":"Reservation Agent","impact":"Handle booking requests and reduce missed calls.","status":"Working in MVP"},{"title":"Customer FAQ Agent","impact":"Answer approved FAQs and escalate unknowns.","status":"Needs menu/FAQ data"},{"title":"Manager Daily Brief","impact":"Summarize reservations, issues, and follow-ups.","status":"Needs POS/CRM integration"}]}
