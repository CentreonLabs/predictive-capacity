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

from __future__ import annotations

from abc import abstractmethod
from typing import Callable, Optional

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.preprocessing import MinMaxScaler  # type: ignore

from predictive_capacity import (
    HORIZON_PREDICTION_HOURS,
    ML_TRAINING_TIMEOUT,
    __version__,
)
from predictive_capacity.forecast.models import auto_ml
from predictive_capacity.schemas import MetricBase, SaturationForecast
from predictive_capacity.warp10.fetch_metric import fetch_metric
from predictive_capacity.warp10.get_label_name import get_label_name
from predictive_capacity.warp10.get_metric_saturation import get_metric_saturation


class MetricCommon:
    data: pd.DataFrame = pd.DataFrame(
        index=pd.DatetimeIndex([]), columns=["0"], dtype="float64"
    )
    features: list[str]
    interpolate: Callable[[], MetricCommon]

    def preprocess(
        self,
        features: Optional[list[str]] = None,
        scaler: Optional[MinMaxScaler] = None,
    ):
        """
        Function that preprocesses the data.
        """
        self.interpolate().add_temporal_features().scale(scaler).remove_features(
            features
        )
        return self

    def add_temporal_features(self):
        """
        Function that adds temporal features to the DataFrame.
        """
        assert isinstance(
            self.data.index, pd.DatetimeIndex
        ), "Index should be a DatetimeIndex."
        # self.data["month"] = self.data.index.month
        self.data["timestamp"] = self.data.index.astype(np.int64) // 10**9
        self.data["day"] = self.data.index.day
        self.data["hour"] = self.data.index.hour
        self.data["minute"] = self.data.index.minute
        self.data["dayofweek"] = self.data.index.dayofweek
        self.data["weekend"] = self.data["dayofweek"].isin([5, 6]).astype(int)
        return self

    @abstractmethod
    def remove_features(self, features: list[str]):
        pass

    @abstractmethod
    def scale(self, scaler: MinMaxScaler):
        pass


class MetricTraining(MetricCommon):
    def __init__(self, token, metric, labels):
        self.data = pd.DataFrame(
            fetch_metric(token, metric, labels).loc[:, metric]  # ignore type
        ).sort_index()
        assert metric == self.data.columns[0]
        assert isinstance(self.data.index, pd.DatetimeIndex)
        self.maximum_allowed = get_metric_saturation(token, metric, labels)
        self.current_saturation = self.data[metric].values[-1] / self.maximum_allowed

    def remove_features(self, features: list[str]):
        unique_counts = self.data.iloc[:, 1:].nunique()
        columns_to_drop = unique_counts[unique_counts == 1].index
        self.data = self.data.drop(columns=columns_to_drop)
        self.features = self.data.columns[1:].tolist()
        return self

    def scale(self, *args, **kwargs):
        """
        Scale the metric and all of its features.

        The metric is scaled to [0 - 1] using a MinMaxScaler.
        The features are scaled using a QuantileTransformer.
        """
        # Fit the metric
        self.metric_scaler = MinMaxScaler(feature_range=(0, 1))
        # The `fit` and `transform` methods expect a 2D array, so we reshape the data to
        # `(n, 1)`.
        self.metric_scaler.fit(np.array([0, self.maximum_allowed]).reshape(-1, 1))
        self.data.iloc[:, 0] = self.metric_scaler.transform(
            np.array(self.data.iloc[:, 0].values).reshape(-1, 1)
        )

        # Fit the features
        self.time_scaler = MinMaxScaler(feature_range=(0, 1))
        # No reshape because we send a matrix as input (multiple columns)
        self.data[self.data.columns[1:]] = self.time_scaler.fit_transform(
            self.data[self.data.columns[1:]]
        )
        return self

    def interpolate(self, frequency: str = "H"):
        """
        Interpolate data to a given frequency.
        """
        self.data = (
            self.data.resample(frequency)
            .mean(numeric_only=True)
            .interpolate(method="linear")
        )
        return self


class MetricForecasting(MetricCommon):
    def __init__(self, start: pd.Timestamp, horizon=HORIZON_PREDICTION_HOURS):
        self.data = pd.DataFrame(
            [],
            index=pd.date_range(start=start, periods=horizon, freq="H"),
        )

    def remove_features(self, features: list[str]):
        self.data = self.data[features]
        return self

    def scale(self, scaler: MinMaxScaler):
        assert isinstance(self.data, pd.DataFrame)
        self.data = pd.DataFrame(scaler.transform(self.data), columns=self.data.columns)
        return self

    def interpolate(self, *args, **kwargs):
        return self


class Metric:
    current_saturation: Optional[float] = None
    days_until_full: Optional[float] = None
    forecast_values: pd.Series = pd.Series(index=pd.DatetimeIndex([]), dtype="float64")

    def __init__(
        self,
        metric: str,
        host_id: str,
        service_id: str,
        platform_uuid: str,
        token: str,
    ):
        # Description of the metric
        self.metric = metric
        self.host_id = host_id
        self.service_id = service_id
        self.platform_uuid = platform_uuid
        self.labels = {
            "host_id": host_id,
            "service_id": service_id,
            "platform_uuid": platform_uuid,
        }
        self.token = token
        self.host_name, self.service_name = get_label_name(token, metric, self.labels)
        self.confidence_level = 0
        self.training_metric = MetricTraining(token, metric, self.labels)

    def forecast(
        self,
        horizon: int = HORIZON_PREDICTION_HOURS,
        timeout: int = ML_TRAINING_TIMEOUT,
    ):
        # Properties based on metric values
        self.current_saturation = self.training_metric.current_saturation
        assert isinstance(self.training_metric.data.index, pd.DatetimeIndex)
        self.last_timestamp = self.training_metric.data.index[-1]

        assert isinstance(self.last_timestamp, pd.Timestamp)
        logger.info(
            f"Building forecast for {self.service_name}@{self.host_name}:{self.metric}"
        )  # noqa: E501
        logger.debug(f"Last metric timestamp: {self.last_timestamp}")

        if len(self.training_metric.data) < 10:
            logger.warning("Not enough data to forecast")
            return self

        # Forecasting properties
        self.forecast_metric = MetricForecasting(
            start=self.last_timestamp + pd.Timedelta("1 H"), horizon=horizon
        )
        self.forecast_dates = self.forecast_metric.data.index

        logger.info(f"first forecast date: {self.forecast_dates[0]}")

        self.training_metric.preprocess()

        features = self.training_metric.features
        scaler = self.training_metric.time_scaler
        reg, self.confidence_level = auto_ml(self.training_metric.data, timeout=timeout)

        self.forecast_metric.preprocess(features, scaler)

        self.forecast_values = pd.Series(
            np.array(reg.predict(self.forecast_metric.data.to_numpy())),
            index=self.forecast_dates,
        )

        logger.debug(f"Confidence level: {self.confidence_level}")
        logger.debug(
            "First forecast values: \n{data}", data=self.forecast_values.head()
        )

        self.saturation_3_months = float(self.forecast_values.iloc[(24 * 31 * 3)])
        self.saturation_6_months = float(self.forecast_values.iloc[(24 * 31 * 6)])
        self.saturation_12_months = float(self.forecast_values.iloc[-1])

        logger.info(f"forecast made with version: {__version__}")

        return self

    def calculate_days_until_full(self):
        """
        Function that gets the number of days until the metric is full according to the
        forecast and the maximum allowed value.
        """
        if len(self.forecast_values) == 0:
            return self
        assert isinstance(self.forecast_values.index, pd.DatetimeIndex)
        last_value_saturation = self.training_metric.data.iloc[-1, 0]
        assert isinstance(last_value_saturation, float)
        if last_value_saturation >= 0.99:
            self.forecast_values = pd.Series(
                index=pd.DatetimeIndex([]), dtype="float64"
            )
            self.hours_until_full = 0
        elif any(self.forecast_values > 1):
            forecast_saturated = self.forecast_values[
                (self.forecast_values > 1) | (self.forecast_values < 0)
            ]
            assert isinstance(forecast_saturated, pd.Series)
            first_point_saturation = forecast_saturated.index[0]
            assert isinstance(first_point_saturation, pd.Timestamp)
            first_point_forecast = self.forecast_values.index[0]
            assert isinstance(first_point_forecast, pd.Timestamp)
            self.hours_until_full = int(
                (first_point_saturation - first_point_forecast).total_seconds() / 3600
            )
            forecast_until_full = self.forecast_values[: self.hours_until_full]
            assert isinstance(forecast_until_full, pd.Series)
            self.forecast_values = forecast_until_full
        else:
            self.hours_until_full = len(self.forecast_values) + 1
        return self

    def to_dict(self, uuid: str) -> MetricBase:
        """
        Function that returns the object as a dict

        Parameters
        ----------
        uuid : str

        Returns
        -------
        MetricBase : MetricBase
        """
        assert isinstance(self.training_metric.data.index, pd.DatetimeIndex)
        assert isinstance(self.forecast_values.index, pd.DatetimeIndex)
        data_scaled = self.training_metric.data.iloc[:, 0].values.tolist()
        data_dates = self.training_metric.data.index.strftime(
            "%Y-%m-%d %H:%M:%S"
        ).tolist()
        forecast = self.forecast_values.values.tolist()
        forecast_dates = self.forecast_values.index.strftime(
            "%Y-%m-%d %H:%M:%S"
        ).tolist()

        return MetricBase(
            metric_name=self.metric,
            host_name=self.host_name,
            host_id=self.host_id,
            service_id=self.service_id,
            service_name=self.service_name,
            data_scaled=data_scaled,
            data_dates=data_dates,
            forecast=forecast,
            forecast_dates=forecast_dates,
            days_to_full=int(self.hours_until_full / 24),
            current_saturation=self.current_saturation,
            saturation_3_months=SaturationForecast(
                current_saturation=self.current_saturation,
                forecast=self.saturation_3_months,
            ),
            saturation_6_months=SaturationForecast(
                current_saturation=self.current_saturation,
                forecast=self.saturation_6_months,
            ),
            saturation_12_months=SaturationForecast(
                current_saturation=self.current_saturation,
                forecast=self.saturation_12_months,
            ),
            confidence_level=self.confidence_level,
            uuid=uuid,
        )
