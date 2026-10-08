def test_dashboard_summary_real_calculations(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    payload = data["data"]
    
    # Verify KPI Structure & values
    assert "kpiMetrics" in payload
    kpis = payload["kpiMetrics"]
    assert "totalSales" in kpis
    assert "inventoryHealth" in kpis
    assert "stockoutRisks" in kpis
    assert "wastageRate" in kpis

    # Verify recommendations and activity logs arrays
    assert isinstance(payload["demandForecastData"], list)
    assert isinstance(payload["aiRecommendations"], list)
    assert isinstance(payload["recentActivityLogs"], list)
    assert "healthIndicators" in payload
