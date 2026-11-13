# EpiSphere

Global Health Intelligence. Detect. Understand. Protect.

A global disease intelligence platform powered by data and AI.

## Structure

- `frontend/`: Next.js web app
- `backend/`: FastAPI backend

## Setup

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Create your own `.env` files in each folder; they are not committed.
