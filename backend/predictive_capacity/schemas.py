from typing import Optional

from pydantic import BaseModel


class SaturationForecast(BaseModel):
    current_saturation: Optional[float]
    forecast: float


class Prediction(BaseModel):
    data_scaled: list[float]
    data_dates: list[str]
    forecast: list[float]
    forecast_dates: list[str]


class Dashboard(BaseModel):
    metric_name: str
    host_name: str
    host_id: str
    service_id: str
    service_name: str
    days_to_full: Optional[int]
    current_saturation: Optional[float]
    saturation_3_months: SaturationForecast
    saturation_6_months: SaturationForecast
    saturation_12_months: SaturationForecast
    uuid: str
    confidence_level: int


class MetricBase(Dashboard, Prediction):
    pass


class ResponseFindSetMetrics(BaseModel):
    platform_uuid: str
    host_id: str
    service_id: str
    metric: str
