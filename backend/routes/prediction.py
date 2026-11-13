from fastapi import APIRouter, HTTPException, Query
from ai.disease_predictor import predict_disease

router = APIRouter(prefix="/api/predict", tags=["prediction"])

@router.get("")
async def get_disease_prediction(
    city: str = Query(..., description="The name of the city"),
    temperature: float = Query(..., description="Temperature in Celsius"),
    humidity: float = Query(..., description="Humidity percentage"),
    rainfall: float = Query(0.0, description="Rainfall in mm"),
    aqi: int = Query(50, description="Air Quality Index")
):
    """
    Predicts potential disease outbreaks based on environmental data provided as query parameters.
    """
    try:
        weather_data = {
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall,
            "air_quality": aqi
        }
        
        # Get prediction from AI module
        prediction = predict_disease(weather_data)
        
        # Add city to the response
        return {
            "city": city,
            "prediction": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
