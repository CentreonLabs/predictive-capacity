# Copyright (C) 2024  Centreon
# This file is part of Predictive Capacity.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
