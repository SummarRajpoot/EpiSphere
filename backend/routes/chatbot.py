import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from groq import Groq
from database import get_db
from models import Region

# Setup logging
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

def get_groq_client() -> Groq:
    """
    Lazily create the Groq client so missing API key
    does not crash the whole backend at startup.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    return Groq(api_key=api_key)

class ChatRequest(BaseModel):
    message: str
    city: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str

SYSTEM_PROMPT = """
You are OutbreakIQ Assistant, an AI specialized ONLY in disease outbreak surveillance for Pakistan.

You have access to this real-time data context:
- Monitored cities: Karachi, Lahore, Islamabad, Peshawar, Quetta, Multan
- Tracked diseases: Dengue, Cholera, Typhoid, Malaria, COVID-19, Hepatitis, Tuberculosis
- Current outbreak data will be provided in each message

You MUST ONLY answer questions about:
1. Disease outbreaks and case counts in Pakistani cities
2. Hospital locations and treatment availability
3. Disease symptoms, prevention, and treatment
4. Risk levels and alerts for specific regions
5. Public health recommendations for Pakistan

If user asks ANYTHING outside this scope (general chat, coding, politics, entertainment, etc.),
respond with: "I'm OutbreakIQ Assistant. I can only help with disease surveillance, outbreak data, and hospital information for Pakistan. Please ask me about disease outbreaks, risk zones, or hospital availability."

Always be concise, factual, and professional. Respond in the same language the user writes in (Urdu or English).
"""

def get_severity(cases: int) -> str:
    if cases > 500: return "Critical"
    if cases > 200: return "Warning"
    if cases > 100: return "Watch"
    return "Normal"

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI Chatbot specialized in Pakistan disease surveillance."""
    try:
        client = get_groq_client()
    except HTTPException:
        logger.error("Chatbot Error: GROQ_API_KEY is missing from environment")
        raise

    # Fetch current data context from DB
    try:
        result = await db.execute(select(Region))
        regions = result.scalars().all()
        
        context_parts = []
        for r in regions:
            severity = get_severity(r.active_cases)
            context_parts.append(f"{r.city}: {r.active_cases} cases ({severity})")
        
        data_context = "Current outbreak data: " + ", ".join(context_parts)
        
        # Build prompt with data context
        user_message_with_context = f"{data_context}\n\nUser Question: {request.message}"
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message_with_context}
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            return ChatResponse(reply=completion.choices[0].message.content)
        except Exception as groq_err:
            logger.error(f"GROQ API CALL FAILED: {str(groq_err)}")
            raise HTTPException(status_code=502, detail=f"AI Service currently unavailable: {str(groq_err)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chatbot General Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal assistant error")

