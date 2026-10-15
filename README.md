# ServeAI Restaurant AI MVP

## Working features
- Responsive frontend
- AI Concierge chat
- Safe fallback mode without OpenAI
- Optional OpenAI integration
- Reservation creation and list
- Restaurant workflow recommendations
- FastAPI backend
- SQLite locally, PostgreSQL-ready

## Run backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Run frontend
```bash
cd frontend
python -m http.server 5500
```
Open http://127.0.0.1:5500

## Optional AI
Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL`.

## Missing production integrations
Real booking/POS/CRM/calendar/voice integrations need client credentials and provider details.
