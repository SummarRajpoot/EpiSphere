from datetime import datetime, timedelta
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Region
from schemas import DashboardResponse, RegionCreate, RegionOut, DashboardStats, CityChart, ChartPoint

router = APIRouter(prefix="/api/regions", tags=["regions"])

def calculate_risk(patients: int, disease: str | None, pop_density: float | None, hosp_capacity: float | None, vax_rate: float | None) -> str:
    risk_score = 0
    if patients > 500: risk_score += 50
    elif patients > 200: risk_score += 30
    else: risk_score += 10
    
    if pop_density and pop_density > 10000: risk_score += 20
    if hosp_capacity is not None:
        if hosp_capacity < 30: risk_score += 30
        elif hosp_capacity > 80: risk_score -= 10
    if vax_rate is not None:
        if vax_rate < 40: risk_score += 20
        elif vax_rate > 70: risk_score -= 20
        
    d = (disease or "").lower()
    if d in ["covid-19", "influenza"]: risk_score += 15
    elif d in ["dengue", "malaria"]: risk_score += 10
    
    if risk_score > 70: return "High"
    if risk_score > 40: return "Medium"
    return "Low"

def generate_recommendations(risk: str, disease: str | None, hosp_capacity: float | None, vax_rate: float | None) -> List[str]:
    recs = []
    if risk == "High":
        recs.extend(["Critical Alert: Declare local health emergency.", "Restrict public gatherings and enforce preventive measures."])
    elif risk == "Medium":
        recs.append("Increase public awareness campaigns.")
    
    if hosp_capacity is not None and hosp_capacity < 40:
        recs.append("Prepare overflow facilities and mobilize additional staff.")
    if vax_rate is not None and vax_rate < 50:
        recs.append("Launch immediate vaccination drive in the affected area.")
    
    if not recs:
        recs.append("Routine surveillance and monitoring.")
    return recs

def _last_7_day_names() -> List[str]:
    today = datetime.now()
    return [(today - timedelta(days=6 - i)).strftime("%a") for i in range(7)]

@router.get("", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region))
    regions = result.scalars().all()
    
    total_cases = sum(r.active_cases for r in regions)
    total_patients = sum(r.patients for r in regions)
    high_risk_count = sum(1 for r in regions if r.risk == "High")
    
    day_names = _last_7_day_names()
    top_regions = sorted(regions, key=lambda r: r.active_cases, reverse=True)[:3]
    top_chart = []
    for r in top_regions:
        history = json.loads(r.history) if r.history else [0]*7
        top_chart.append(CityChart(
            city=r.city,
            data=[ChartPoint(day=day_names[i], value=history[i]) for i in range(min(7, len(history)))]
        ))
        
    return DashboardResponse(
        regions=[RegionOut.model_validate(r) for r in regions],
        totals=DashboardStats(
            totalCases=total_cases,
            totalPatients=total_patients,
            activeRegions=len(regions),
            highRisk=high_risk_count
        ),
        topChart=top_chart
    )

@router.post("", response_model=RegionOut)
async def create_or_update_region(region_in: RegionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).where(Region.city.ilike(region_in.city)))
    region = result.scalars().first()
    
    risk = calculate_risk(region_in.patients, region_in.disease, region_in.population_density, region_in.hospital_capacity, region_in.vaccination_rate)
    recs = generate_recommendations(risk, region_in.disease, region_in.hospital_capacity, region_in.vaccination_rate)
    
    if region:
        # Update
        old_cases = region.active_cases
        region.active_trend = f"{'+' if region_in.active_cases >= old_cases else ''}{((region_in.active_cases - old_cases)/old_cases*100):.1f}%" if old_cases > 0 else "+0%"
        
        old_patients = region.patients
        region.patients_trend = f"{'+' if region_in.patients >= old_patients else ''}{((region_in.patients - old_patients)/old_patients*100):.1f}%" if old_patients > 0 else "+0%"
        
        history = json.loads(region.history) if region.history else [0]*7
        history.pop(0)
        history.append(region_in.active_cases)
        region.history = json.dumps(history)
        
        region.active_cases = region_in.active_cases
        region.patients = region_in.patients
        region.risk = risk
        region.recommendations = json.dumps(recs)
        region.disease = region_in.disease
        region.hospital_capacity = region_in.hospital_capacity
        region.vaccination_rate = region_in.vaccination_rate
    else:
        # Create
        history = [0]*6 + [region_in.active_cases]
        region = Region(
            city=region_in.city,
            active_cases=region_in.active_cases,
            patients=region_in.patients,
            risk=risk,
            recommendations=json.dumps(recs),
            history=json.dumps(history),
            disease=region_in.disease,
            population_density=region_in.population_density,
            hospital_capacity=region_in.hospital_capacity,
            vaccination_rate=region_in.vaccination_rate,
            last_week_cases=region_in.active_cases
        )
        db.add(region)
        
    await db.commit()
    await db.refresh(region)
    return RegionOut.model_validate(region)

@router.put("/{region_id}", response_model=RegionOut)
async def update_region(region_id: int, region_in: RegionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).where(Region.id == region_id))
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    old_cases = region.active_cases
    old_patients = region.patients
    risk = calculate_risk(
        region_in.patients,
        region_in.disease,
        region_in.population_density,
        region_in.hospital_capacity,
        region_in.vaccination_rate,
    )
    recs = generate_recommendations(
        risk, region_in.disease, region_in.hospital_capacity, region_in.vaccination_rate
    )

    region.active_trend = (
        f"{'+' if region_in.active_cases >= old_cases else ''}"
        f"{((region_in.active_cases - old_cases) / old_cases * 100):.1f}%"
        if old_cases > 0
        else "+0%"
    )
    region.patients_trend = (
        f"{'+' if region_in.patients >= old_patients else ''}"
        f"{((region_in.patients - old_patients) / old_patients * 100):.1f}%"
        if old_patients > 0
        else "+0%"
    )

    history = json.loads(region.history) if region.history else [0] * 7
    history.pop(0)
    history.append(region_in.active_cases)
    region.history = json.dumps(history)

    region.city = region_in.city
    region.active_cases = region_in.active_cases
    region.patients = region_in.patients
    region.risk = risk
    region.recommendations = json.dumps(recs)
    region.disease = region_in.disease
    region.population_density = region_in.population_density
    region.hospital_capacity = region_in.hospital_capacity
    region.vaccination_rate = region_in.vaccination_rate
    region.last_week_cases = old_cases

    await db.commit()
    await db.refresh(region)
    return RegionOut.model_validate(region)

@router.delete("/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_regions(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Region))
    await db.commit()

@router.delete("/{region_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_region(region_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).where(Region.id == region_id))
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    await db.delete(region)
    await db.commit()
