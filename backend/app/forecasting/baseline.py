import math
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.forecasting.base import BaseForecastingModel


class BaselineMovingAverageModel(BaseForecastingModel):
    """
    Weighted Exponential Moving Average & Linear Trend Forecasting Engine.
    Computes baseline demand forecasts with confidence intervals based on standard deviation.
    """
    def predict(self, historical_sales: List[Dict[str, Any]], horizon_days: int = 7) -> List[Dict[str, Any]]:
        if not historical_sales:
            base_val = 100
            std_dev = 15.0
            trend_slope = 0.5
        else:
            quantities = [s["quantity"] for s in historical_sales]
            count = len(quantities)
            
            # Simple Moving Average & EMA
            alpha = 0.2
            ema = quantities[0]
            for q in quantities[1:]:
                ema = alpha * q + (1 - alpha) * ema
            base_val = ema

            # Standard Deviation for Confidence Intervals
            mean = sum(quantities) / max(count, 1)
            variance = sum((q - mean) ** 2 for q in quantities) / max(count, 1)
            std_dev = math.sqrt(variance) if variance > 0 else mean * 0.15

            # Linear Trend Slope (recent vs older)
            if count >= 14:
                recent_half = sum(quantities[-7:]) / 7.0
                older_half = sum(quantities[-14:-7]) / 7.0
                trend_slope = (recent_half - older_half) / 7.0
            else:
                trend_slope = 0.0

        forecast_points = []
        start_date = datetime.now()

        for d in range(1, horizon_days + 1):
            date_str = (start_date + timedelta(days=d)).strftime("%b %d")
            
            # Add trend + mild day-of-week seasonality simulation
            seasonality = 1.1 if d % 7 in [5, 6] else 0.98
            projected = max(10, int((base_val + (trend_slope * d)) * seasonality))
            
            conf_margin = int(std_dev * (1.0 + (0.05 * math.sqrt(d))))
            upper = projected + conf_margin
            lower = max(0, projected - conf_margin)

            forecast_points.append({
                "day": date_str,
                "forecast": projected,
                "confidenceUpper": upper,
                "confidenceLower": lower
            })

        return forecast_points
