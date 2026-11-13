from typing import Dict, Any

def predict_disease(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predicts potential disease outbreaks based on weather conditions.
    
    Args:
        weather_data (dict): Dictionary containing:
            - temperature (float): Temperature in Celsius
            - humidity (float): Humidity percentage (0-100)
            - rainfall (float): Rainfall in mm
            - air_quality (int): Air Quality Index (AQI)
            
    Returns:
        dict: {
            "disease": str,
            "risk": str,
            "recommendation": str
        }
    """
    temp = weather_data.get("temperature", 0)
    humidity = weather_data.get("humidity", 0)
    rainfall = weather_data.get("rainfall", 0)
    aqi = weather_data.get("air_quality", 0)

    # Default values
    disease = "No significant risk detected"
    risk = "Low"
    recommendation = "Continue routine health monitoring."

    # Prediction Logic based on rules
    
    # 1. High humidity + rainfall = Dengue
    if humidity > 60 and rainfall > 2:
        disease = "Dengue"
        risk = "High"
        recommendation = "Eliminate stagnant water and use mosquito repellents."
        
    # 2. High temperature = Heatstroke
    elif temp > 38:
        disease = "Heatstroke"
        risk = "High"
        recommendation = "Stay hydrated, avoid direct sunlight, and remain in cool environments."
    elif temp > 35:
        disease = "Heatstroke"
        risk = "Medium"
        recommendation = "Limit outdoor activity and drink plenty of water."

    # 3. Poor AQI = Asthma
    elif aqi > 150:
        disease = "Asthma / Respiratory Issues"
        risk = "High"
        recommendation = "Stay indoors and use air purifiers; wear masks if outside."
    elif aqi > 100:
        disease = "Asthma / Respiratory Issues"
        risk = "Medium"
        recommendation = "Sensitive groups should reduce prolonged outdoor exertion."

    # 4. Cold + humidity = Flu
    elif temp < 15 and humidity > 50:
        disease = "Influenza (Flu)"
        risk = "Medium"
        recommendation = "Practice good hygiene, stay warm, and consider flu vaccination."

    return {
        "disease": disease,
        "risk": risk,
        "recommendation": recommendation
    }
