def test_get_festival_calendar(client):
    response = client.get("/api/forecast/festivals/calendar")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    names = [f["festival"] for f in body["data"]]
    assert "Diwali" in names
    assert "Holi" in names
    diwali = next(f for f in body["data"] if f["festival"] == "Diwali")
    assert diwali["category_multipliers"]["Electronics"] > 1.0


def test_get_festival_calendar_specific_year(client):
    response = client.get("/api/forecast/festivals/calendar?year=2026")
    assert response.status_code == 200
    body = response.json()
    for entry in body["data"]:
        assert entry["date"].startswith("2026")


def test_get_upcoming_festivals(client):
    response = client.get("/api/forecast/festivals/upcoming?category=Electronics&within_days=365")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) > 0
    for item in body["data"]:
        assert item["days_away"] >= 0
        assert item["expected_multiplier"] >= 1.0


def test_product_festival_forecast(client):
    # Ensure at least one product exists via the default forecast pipeline
    client.get("/api/forecast")

    response = client.get("/api/forecast/MK-001-F/festival-forecast?horizon_days=60")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert data["horizon_days"] == 60
    assert len(data["daily_forecasts"]) == len(data["festival_adjusted_forecasts"])
    assert data["festival_adjusted_total_demand"] >= data["baseline_total_demand"]
    assert data["extra_units_from_festivals"] >= 0
    # Every festival-adjusted day should be >= the corresponding baseline day
    for base_day, adj_day in zip(data["daily_forecasts"], data["festival_adjusted_forecasts"]):
        assert adj_day["forecast"] >= base_day["forecast"]


def test_festival_item_demand(client):
    response = client.get("/api/forecast/festivals/item-demand?festival_name=Diwali&horizon_days=60&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert data["festival_name"] == "Diwali"
    assert len(data["items"]) > 0
    assert len(data["items"]) <= 10
    top_item = data["items"][0]
    assert top_item["festival_period_sales"] >= top_item["baseline_period_sales"]
    assert top_item["festival_multiplier"] >= 1.0


def test_festival_item_demand_varies_per_festival(client):
    res_diwali = client.get("/api/forecast/festivals/item-demand?festival_name=Diwali").json()["data"]
    res_holi = client.get("/api/forecast/festivals/item-demand?festival_name=Holi").json()["data"]
    res_eid = client.get("/api/forecast/festivals/item-demand?festival_name=Eid%20al-Fitr").json()["data"]
    res_christmas = client.get("/api/forecast/festivals/item-demand?festival_name=Christmas").json()["data"]

    diwali_top_product = res_diwali["items"][0]["product_name"]
    holi_top_product = res_holi["items"][0]["product_name"]
    eid_top_product = res_eid["items"][0]["product_name"]
    christmas_top_product = res_christmas["items"][0]["product_name"]

    # Products should vary according to different festivals
    assert diwali_top_product != holi_top_product
    assert holi_top_product != eid_top_product
    assert eid_top_product != christmas_top_product


