from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class BaseForecastingModel(ABC):
    """
    Abstract forecasting model strategy interface.
    Implementations (Baseline, Prophet, XGBoost, LSTM) will implement predict().
    """
    @abstractmethod
    def predict(self, historical_sales: List[Dict[str, Any]], horizon_days: int) -> List[Dict[str, Any]]:
        pass
