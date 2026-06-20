from fastapi import APIRouter

from app.services.weather_service import get_weather_data


router = APIRouter()


@router.get("/api/weather")
def get_weather():
    return get_weather_data()
