"""
Festival Calendar & Category Demand-Impact Engine
==================================================
A lightweight, dependency-free reference calendar of major Indian retail
festivals used to power "festival-wise demand forecasting".

For each festival we track:
  - Its (approximate, publicly known) date for a handful of years.
  - A per-category demand multiplier representing the typical uplift a
    retail category experiences in the days surrounding that festival
    (e.g. Electronics & Clothing spike hard around Diwali, Beverages &
    Snacks spike around New Year, etc).
  - A demand "window" (days before / after the festival date) over which
    the uplift is considered active, tapering in on approach and tapering
    out afterwards.

This module is pure Python (no DB / framework dependencies) so it can be
imported by both the forecasting models and the API layer.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union

DateLike = Union[str, date, datetime]

# Default uplift applied to any category not explicitly listed for a festival.
DEFAULT_MULTIPLIER = 1.1


def _to_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# Festival reference data
# ---------------------------------------------------------------------------
# Dates are approximate for lunar/lunisolar festivals (Diwali, Holi, Eid,
# Dussehra, Ganesh Chaturthi, Raksha Bandhan) — accurate enough for demand
# planning purposes. Fixed-date national holidays are exact.
FESTIVALS: List[Dict] = [
    {
        "name": "Republic Day",
        "dates": {2024: "2024-01-26", 2025: "2025-01-26", 2026: "2026-01-26", 2027: "2027-01-26"},
        "window_before": 3,
        "window_after": 0,
        "category_multipliers": {
            "Electronics": 1.25, "Clothing": 1.15, "Household": 1.1, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Holi",
        "dates": {2024: "2024-03-25", 2025: "2025-03-14", 2026: "2026-03-04", 2027: "2027-03-22"},
        "window_before": 5,
        "window_after": 1,
        "category_multipliers": {
            "Household": 1.6, "Snacks": 1.45, "Bakery": 1.4, "Beverages": 1.35,
            "Personal Care": 1.3, "Clothing": 1.2, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Eid al-Fitr",
        "dates": {2024: "2024-04-11", 2025: "2025-03-31", 2026: "2026-03-20", 2027: "2027-03-09"},
        "window_before": 7,
        "window_after": 1,
        "category_multipliers": {
            "Clothing": 1.65, "Clothing Accessories": 1.5, "Bakery": 1.6, "Footwear": 1.35,
            "Personal Care": 1.3, "Snacks": 1.4, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Independence Day",
        "dates": {2024: "2024-08-15", 2025: "2025-08-15", 2026: "2026-08-15", 2027: "2027-08-15"},
        "window_before": 3,
        "window_after": 0,
        "category_multipliers": {
            "Electronics": 1.3, "Household": 1.15, "Clothing": 1.1, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Raksha Bandhan",
        "dates": {2024: "2024-08-19", 2025: "2025-08-09", 2026: "2026-08-28", 2027: "2027-08-17"},
        "window_before": 6,
        "window_after": 0,
        "category_multipliers": {
            "Clothing Accessories": 1.55, "Bakery": 1.45, "Clothing": 1.3, "Snacks": 1.25,
            "Personal Care": 1.2, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Ganesh Chaturthi",
        "dates": {2024: "2024-09-07", 2025: "2025-08-27", 2026: "2026-09-14", 2027: "2027-09-04"},
        "window_before": 5,
        "window_after": 2,
        "category_multipliers": {
            "Bakery": 1.7, "Fruits & Vegetables": 1.45, "Snacks": 1.4, "Household": 1.3,
            "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Gandhi Jayanti",
        "dates": {2024: "2024-10-02", 2025: "2025-10-02", 2026: "2026-10-02", 2027: "2027-10-02"},
        "window_before": 2,
        "window_after": 0,
        "category_multipliers": {"default": DEFAULT_MULTIPLIER},
    },
    {
        "name": "Dussehra",
        "dates": {2024: "2024-10-12", 2025: "2025-10-02", 2026: "2026-10-20", 2027: "2027-10-10"},
        "window_before": 5,
        "window_after": 1,
        "category_multipliers": {
            "Electronics": 1.4, "Clothing": 1.35, "Footwear": 1.3, "Bakery": 1.3,
            "Household": 1.2, "default": DEFAULT_MULTIPLIER,
        },
    },
    {
        "name": "Diwali",
        "dates": {2024: "2024-11-01", 2025: "2025-10-20", 2026: "2026-11-08", 2027: "2027-10-29"},
        "window_before": 10,
        "window_after": 1,
        "category_multipliers": {
            "Electronics": 1.9, "Clothing": 1.7, "Clothing Accessories": 1.6, "Bakery": 2.1,
            "Snacks": 1.8, "Household": 1.55, "Personal Care": 1.4, "Footwear": 1.35,
            "Beverages": 1.3, "Books": 1.2, "default": 1.15,
        },
    },
    {
        "name": "Christmas",
        "dates": {2024: "2024-12-25", 2025: "2025-12-25", 2026: "2026-12-25", 2027: "2027-12-25"},
        "window_before": 8,
        "window_after": 1,
        "category_multipliers": {
            "Bakery": 1.75, "Electronics": 1.45, "Clothing": 1.35, "Snacks": 1.4,
            "Beverages": 1.3, "Books": 1.25, "default": 1.15,
        },
    },
    {
        "name": "New Year",
        "dates": {2024: "2024-01-01", 2025: "2025-01-01", 2026: "2026-01-01", 2027: "2027-01-01"},
        "window_before": 4,
        "window_after": 0,
        "category_multipliers": {
            "Beverages": 1.6, "Snacks": 1.45, "Bakery": 1.4, "Clothing": 1.2, "default": DEFAULT_MULTIPLIER,
        },
    },
]


def _festival_window(festival: Dict, year: int):
    """Return (festival_date, window_start, window_end) for a festival in a given year."""
    date_str = festival["dates"].get(year)
    if not date_str:
        return None
    f_date = _to_date(date_str)
    start = f_date - timedelta(days=festival.get("window_before", 5))
    end = f_date + timedelta(days=festival.get("window_after", 0))
    return f_date, start, end


def get_calendar(years: Optional[List[int]] = None) -> List[Dict]:
    """Return a flat, sorted list of {festival, date, category_multipliers} for the given years."""
    if not years:
        current_year = datetime.now().year
        years = [current_year, current_year + 1]

    entries = []
    for festival in FESTIVALS:
        for year in years:
            date_str = festival["dates"].get(year)
            if date_str:
                entries.append({
                    "festival": festival["name"],
                    "date": date_str,
                    "category_multipliers": {k: v for k, v in festival["category_multipliers"].items() if k != "default"},
                    "default_multiplier": festival["category_multipliers"].get("default", DEFAULT_MULTIPLIER),
                    "window_before_days": festival.get("window_before", 5),
                    "window_after_days": festival.get("window_after", 0),
                })
    entries.sort(key=lambda e: e["date"])
    return entries


def find_active_festival(target_date: DateLike, category: Optional[str] = None):
    """
    If `target_date` falls inside any festival's demand window, return
    (festival_name, multiplier, days_to_peak) for the given category.
    Otherwise return None. When multiple festivals overlap, the one with
    the highest multiplier for the category wins.
    """
    t_date = _to_date(target_date)
    best = None

    for festival in FESTIVALS:
        window = _festival_window(festival, t_date.year)
        if not window:
            continue
        f_date, start, end = window
        if start <= t_date <= end:
            mult = festival["category_multipliers"].get(category, festival["category_multipliers"].get("default", DEFAULT_MULTIPLIER))

            # Taper the multiplier based on proximity to the festival's peak day —
            # demand ramps up approaching the festival and eases off right after.
            span = max(1, (f_date - start).days if t_date <= f_date else (end - f_date).days)
            distance = abs((t_date - f_date).days)
            proximity = max(0.35, 1.0 - (distance / max(span, 1)) * 0.65)
            effective_mult = 1.0 + (mult - 1.0) * proximity

            candidate = (festival["name"], round(effective_mult, 3), (f_date - t_date).days)
            if best is None or candidate[1] > best[1]:
                best = candidate

    return best


def get_multiplier_for_date(target_date: DateLike, category: Optional[str] = None) -> float:
    """Convenience wrapper returning just the multiplier (1.0 if no active festival)."""
    active = find_active_festival(target_date, category)
    return active[1] if active else 1.0


def get_upcoming_festivals(from_date: DateLike, category: Optional[str] = None, within_days: int = 60) -> List[Dict]:
    """
    Return festivals whose peak date falls within `within_days` of `from_date`,
    each annotated with the expected multiplier / uplift % for `category`.
    """
    f_from = _to_date(from_date)
    horizon_end = f_from + timedelta(days=within_days)
    results = []

    for festival in FESTIVALS:
        for year in (f_from.year, f_from.year + 1):
            date_str = festival["dates"].get(year)
            if not date_str:
                continue
            f_date = _to_date(date_str)
            if f_from <= f_date <= horizon_end:
                mult = festival["category_multipliers"].get(category, festival["category_multipliers"].get("default", DEFAULT_MULTIPLIER))
                results.append({
                    "festival": festival["name"],
                    "date": f_date.isoformat(),
                    "days_away": (f_date - f_from).days,
                    "category": category or "General",
                    "expected_multiplier": round(mult, 3),
                    "expected_uplift_pct": round((mult - 1.0) * 100, 1),
                    "window_before_days": festival.get("window_before", 5),
                    "window_after_days": festival.get("window_after", 0),
                })

    results.sort(key=lambda r: r["days_away"])
    return results


def get_festival_by_name(name: str, target_year: Optional[int] = None) -> Optional[Dict]:
    """Retrieve festival metadata dictionary by name."""
    norm_name = name.strip().lower()
    for festival in FESTIVALS:
        if festival["name"].lower() == norm_name:
            year = target_year or datetime.now().year
            date_str = festival["dates"].get(year) or festival["dates"].get(year + 1)
            if not date_str:
                date_str = list(festival["dates"].values())[0]
            f_date = _to_date(date_str)
            days_away = (f_date - datetime.now().date()).days
            return {
                "name": festival["name"],
                "date": date_str,
                "days_away": days_away,
                "window_before": festival.get("window_before", 5),
                "window_after": festival.get("window_after", 0),
                "category_multipliers": festival["category_multipliers"],
            }
    return None


def get_category_multiplier_for_festival(festival_name: str, category: str) -> float:
    """Return the multiplier for a specific category during a named festival."""
    fest = get_festival_by_name(festival_name)
    if not fest:
        return DEFAULT_MULTIPLIER
    mults = fest["category_multipliers"]
    return mults.get(category, mults.get("default", DEFAULT_MULTIPLIER))

