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

import math
import warnings
from typing import Tuple

import numpy as np
import optuna
import pandas as pd
from aeon.performance_metrics.forecasting import (
    mean_absolute_scaled_error as error_metric,
)
from lightgbm import LGBMRegressor
from loguru import logger
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

optuna.logging.set_verbosity(optuna.logging.WARNING)

seed = 0
np.random.seed(seed)


class MutliGBMTunedDetrended(BaseEstimator, RegressorMixin):
    def __init__(self, n_trials=400, timeout=300, n_splits=5):
        self.n_trials = n_trials
        self.timeout = timeout
        self.n_splits = n_splits

    def fit(self, X, y):
        def objective(trial: optuna.Trial) -> float:
            tscv = TimeSeriesSplit(n_splits=self.n_splits, test_size=int(0.1 * len(X)))

            gbm_type = trial.suggest_categorical("gbm_type", ["lgbm", "gbr", "hgbr"])

            if gbm_type == "lgbm":
                param = {
                    "objective": trial.suggest_categorical(
                        "objective",
                        ["quantile"],
                    ),
                    "alpha": trial.suggest_float("alpha", 0.01, 0.99),
                    "learning_rate": trial.suggest_float("learning_rate", 0.0001, 1),
                    "n_estimators": trial.suggest_int("n_estimators", 50, 3000),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 100.0),
                    "random_state": seed,
                    "verbose": -1,
                }

                gbm = LGBMRegressor(**param)

            elif gbm_type == "gbr":
                param = {
                    "loss": trial.suggest_categorical("loss", ["quantile"]),
                    "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.5),
                    "n_estimators": trial.suggest_int("n_estimators", 50, 1000),
                    "alpha": trial.suggest_float("alpha", 0.01, 0.99),
                    "random_state": seed,
                }

                gbm = GradientBoostingRegressor(**param)

            else:
                param = {
                    "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.5),
                    "max_iter": trial.suggest_int("max_iter", 50, 1000),
                    "quantile": trial.suggest_float("quantile", 0.01, 0.99),
                    "loss": trial.suggest_categorical("loss", ["quantile"]),
                    "random_state": seed,
                }

                gbm = HistGradientBoostingRegressor(**param)

            degree = trial.suggest_int("poly_degree", 0, 1)

            if degree > 0:
                trend_model = trial.suggest_categorical(
                    "trend_model",
                    [
                        # "ridge",
                        "huber"
                    ],
                )

                if trend_model == "ridge":
                    trend_forecaster = make_pipeline(
                        PolynomialFeatures(degree),
                        Ridge(alpha=trial.suggest_float("ridge_alpha", 0.0001, 1000.0)),
                    )
                else:
                    trend_forecaster = make_pipeline(
                        PolynomialFeatures(degree),
                        HuberRegressor(
                            epsilon=trial.suggest_float("huber_eps", 1, 1000.0)
                        ),
                    )

                damped = trial.suggest_float("damped", -1.0, 1.0, step=0.01)

                mae_scores = []
                for k, (train_index, valid_index) in enumerate(tscv.split(X)):
                    train_x, valid_x = X[train_index], X[valid_index]
                    train_y, valid_y = y[train_index], y[valid_index]

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        trend_forecaster.fit(train_x[:, 0].reshape(-1, 1), train_y)

                    gbm.fit(
                        train_x,
                        train_y
                        - damped
                        * np.array(
                            trend_forecaster.predict(train_x[:, 0].reshape(-1, 1))
                        ),
                    )

                    preds = np.array(gbm.predict(valid_x))
                    mae = error_metric(
                        valid_y,
                        preds
                        + damped
                        * np.array(
                            trend_forecaster.predict(valid_x[:, 0].reshape(-1, 1))
                        ),
                        y_train=train_y,
                    )
                    mae_scores.append(mae)

                    trial.report(float(np.mean(mae_scores)), k)
                    if trial.should_prune():
                        raise optuna.TrialPruned()

                mean_mae: float = float(np.mean(mae_scores))

                trial.set_user_attr("std_mae", np.std(mae_scores))

                return mean_mae
            else:
                mae_scores = []
                for k, (train_index, valid_index) in enumerate(tscv.split(X)):
                    train_x, valid_x = X[train_index], X[valid_index]
                    train_y, valid_y = y[train_index], y[valid_index]

                    gbm.fit(train_x, train_y)
                    preds = gbm.predict(valid_x)

                    mae = error_metric(
                        valid_y,
                        preds,
                        y_train=train_y,
                    )
                    mae_scores.append(mae)

                    trial.report(float(np.mean(mae_scores)), k)
                    if trial.should_prune():
                        raise optuna.TrialPruned()

                mean_mae = float(np.mean(mae_scores))

                trial.set_user_attr("std_mae", np.std(mae_scores))

                return mean_mae

        self.study = optuna.create_study(
            direction="minimize",
            study_name="forecast_dream",
            sampler=optuna.samplers.TPESampler(seed=seed),
            pruner=optuna.pruners.SuccessiveHalvingPruner(),
        )
        self.study.optimize(objective, n_trials=self.n_trials, timeout=self.timeout)

        self.best_params = self.study.best_params

        if self.best_params["poly_degree"] > 0:
            self.damped = self.best_params["damped"]
            if self.best_params["trend_model"] == "ridge":
                self.trend_forecaster = make_pipeline(
                    PolynomialFeatures(degree=self.best_params["poly_degree"]),
                    Ridge(alpha=self.best_params["ridge_alpha"]),
                )
            else:
                self.trend_forecaster = make_pipeline(
                    PolynomialFeatures(degree=self.best_params["poly_degree"]),
                    HuberRegressor(epsilon=self.best_params["huber_eps"]),
                )

            self.trend_forecaster.fit(X[:, 0].reshape(-1, 1), y)

        if self.best_params["gbm_type"] == "lgbm":
            gbm_params = {
                "random_state": seed,
                "verbose": -1,
                **{
                    k: v
                    for k, v in self.best_params.items()
                    if k
                    not in [
                        "damped",
                        "trend_model",
                        "poly_degree",
                        "ridge_alpha",
                        "svr_C",
                        "huber_eps",
                        "gbm_type",
                    ]
                },
            }

            self.best_gbm = LGBMRegressor(**gbm_params)
            self.best_gbm_low = LGBMRegressor(
                **{k: (v if k != "alpha" else 0.01) for k, v in gbm_params.items()}  # type: ignore
            )
            self.best_gbm_high = LGBMRegressor(
                **{k: (v if k != "alpha" else 0.99) for k, v in gbm_params.items()}  # type: ignore
            )

        elif self.best_params["gbm_type"] == "gbr":
            gbm_params = {
                "random_state": seed,
                **{
                    k: v
                    for k, v in self.best_params.items()
                    if k
                    not in [
                        "damped",
                        "trend_model",
                        "poly_degree",
                        "ridge_alpha",
                        "svr_C",
                        "huber_eps",
                        "gbm_type",
                    ]
                },
            }
            self.best_gbm = GradientBoostingRegressor(**gbm_params)
            self.best_gbm_low = GradientBoostingRegressor(
                **{k: (v if k != "alpha" else 0.01) for k, v in gbm_params.items()}  # type: ignore
            )
            self.best_gbm_high = GradientBoostingRegressor(
                **{k: (v if k != "alpha" else 0.99) for k, v in gbm_params.items()}  # type: ignore
            )

        else:
            gbm_params = {
                "random_state": seed,
                **{
                    k: v
                    for k, v in self.best_params.items()
                    if k
                    not in [
                        "damped",
                        "trend_model",
                        "poly_degree",
                        "ridge_alpha",
                        "svr_C",
                        "huber_eps",
                        "gbm_type",
                    ]
                },
            }

            self.best_gbm = HistGradientBoostingRegressor(**gbm_params)
            self.best_gbm_low = HistGradientBoostingRegressor(
                **{k: (v if k != "quantile" else 0.01) for k, v in gbm_params.items()}  # type: ignore
            )
            self.best_gbm_high = HistGradientBoostingRegressor(
                **{k: (v if k != "quantile" else 0.99) for k, v in gbm_params.items()}  # type: ignore
            )

        if self.best_params["poly_degree"] > 0:
            self.best_gbm.fit(
                X,
                y - self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1)),
            )
            self.best_gbm_low.fit(
                X,
                y - self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1)),
            )
            self.best_gbm_high.fit(
                X,
                y - self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1)),
            )
        else:
            self.best_gbm.fit(X, y)
            self.best_gbm_low.fit(X, y)
            self.best_gbm_high.fit(X, y)

        # confidence level

        conf_feature = math.log(
            1
            + math.log(1 + self.study.best_trial.values[0])
            * math.log(1 + self.study.best_trial.user_attrs["std_mae"])
        )

        self.confidence_level = (
            2
            if conf_feature < 0.37
            else (1 if ((conf_feature >= 0.37) and (conf_feature < 3)) else 0)
        )

        logger.debug(f"number of trials:{len(self.study.get_trials())}")
        logger.debug("best model params: {dict}", dict=self.study.best_params)

        return self

    def predict(self, X):
        if self.best_params["poly_degree"] > 0:
            y_pred = self.best_gbm.predict(
                X
            ) + self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1))
        else:
            y_pred = self.best_gbm.predict(X)

        return y_pred

    def predict_low(self, X):
        if self.best_params["poly_degree"] > 0:
            y_pred = self.best_gbm_low.predict(
                X
            ) + self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1))
        else:
            y_pred = self.best_gbm_low.predict(X)

        return y_pred

    def predict_high(self, X):
        if self.best_params["poly_degree"] > 0:
            y_pred = self.best_gbm_high.predict(
                X
            ) + self.damped * self.trend_forecaster.predict(X[:, 0].reshape(-1, 1))
        else:
            y_pred = self.best_gbm_high.predict(X)

        return y_pred


def auto_ml(
    data: pd.DataFrame,
    n_splits=5,
    timeout=300,
) -> Tuple[
    MutliGBMTunedDetrended,
    int,
]:
    """
    Function that automatically selects the best model for a given time series

    Parameters
    ----------
    x: np.ndarray
        time series

    Returns
    -------
    reg: MutliGBMTunedDetrended
        model that best fits the time series
    confidence_level: [0,1,2]
        2 are best models, 0 are the worst
    """

    y = data.iloc[:, 0].to_numpy()
    X = data.iloc[:, 1:].to_numpy()

    gbm_det = MutliGBMTunedDetrended(n_trials=1000, timeout=timeout, n_splits=n_splits)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gbm_det.fit(X, y)

    confidence_level: int = gbm_det.confidence_level

    return gbm_det, confidence_level
