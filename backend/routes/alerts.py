from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Region

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory storage for acknowledged alerts: {city_name: timestamp}
acknowledged_alerts: Dict[str, datetime] = {}

def get_severity_info(cases: int):
    if cases > 500:
        return "critical", "red", "Critical outbreak detected"
    elif cases > 200:
        return "warning", "orange", "Warning: High case count"
    elif cases > 100:
        return "watch", "yellow", "Surveillance watch active"
    else:
        return "normal", "green", "Cases within normal range"

@router.get("/")
async def get_alerts(db: AsyncSession = Depends(get_db)):
    """Generates automatic alerts based on region case counts."""
    result = await db.execute(select(Region))
    regions = result.scalars().all()
    
    alerts = []
    for region in regions:
        severity, color, base_msg = get_severity_info(region.active_cases)
        
        alerts.append({
            "id": region.id,
            "city": region.city,
            "severity": severity,
            "color": color,
            "message": f"{base_msg} in {region.city} - {region.active_cases} active cases",
            "active_cases": region.active_cases,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": region.city in acknowledged_alerts
        })
    
    # Sort by severity priority: critical > warning > watch > normal
    priority = {"critical": 0, "warning": 1, "watch": 2, "normal": 3}
    return sorted(alerts, key=lambda x: priority[x["severity"]])

@router.post("/acknowledge/{city}")
async def acknowledge_alert(city: str):
    """Marks an alert as acknowledged for a specific city."""
    acknowledged_alerts[city] = datetime.now()
    return {"status": "success", "city": city}

@router.get("/summary")
async def get_alerts_summary(db: AsyncSession = Depends(get_db)):
    """Returns a count of alerts by severity and the overall highest severity."""
    result = await db.execute(select(Region))
    regions = result.scalars().all()
    
    summary = {"critical": 0, "warning": 0, "watch": 0, "normal": 0}
    highest_severity = "normal"
    priority = {"critical": 3, "warning": 2, "watch": 1, "normal": 0}
    
    for region in regions:
        severity, _, _ = get_severity_info(region.active_cases)
        summary[severity] += 1
        
        if priority[severity] > priority[highest_severity]:
            highest_severity = severity
            
    return {
        "counts": summary,
        "highest_severity": highest_severity,
        "total_active_alerts": summary["critical"] + summary["warning"]
    }
