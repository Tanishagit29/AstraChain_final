import os
import pytest
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.all_models import Product, Inventory, SalesHistory
from app.agents.data_agent import DataAgent
from app.agents.base_agent import BaseSupplyChainAgent
from app.services.pipeline_state import pipeline_state


def test_groq_api_key_missing_guard(monkeypatch):
    """Verify that missing GROQ_API_KEY returns clear error status instead of fallback."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("app.core.config.settings.GROQ_API_KEY", None)
    agent = DataAgent()

    res = agent.run("Ingest test dataset", context={})
    assert res["status"] == "ERROR"
    assert "GROQ_API_KEY is missing" in res["error"]


def test_data_agent_tools_execution(db_session: Session, tmp_path):
    """Test DataAgent individual tools: read_file, map_columns, validate, simulate_data (seed 42), bulk_insert."""
    # Create test CSV
    csv_file = tmp_path / "test_supply.csv"
    csv_file.write_text(
        "Item_ID,Item_Name,Category_Name,Price,Stock\n"
        "SKU-T101,Organic Fresh Milk,Dairy,₹65,120\n"
        "SKU-T102,Greek Yogurt,Dairy,₹110,45\n"
        "SKU-T103,Basmati Rice 5kg,Staples,₹450,300\n",
        encoding="utf-8"
    )
    filepath = str(csv_file)

    agent = DataAgent()

    # 1. read_file
    res_read = agent._tool_read_file(filepath=filepath)
    assert res_read["status"] == "success"
    assert res_read["total_rows"] == 3

    # 2. map_columns
    res_map = agent._tool_map_columns(filepath=filepath)
    assert res_map["status"] == "success"
    assert "sku" in res_map["mapped_columns"]
    assert "name" in res_map["mapped_columns"]

    # 3. validate
    res_val = agent._tool_validate(filepath=filepath)
    assert "quality_score" in res_val
    assert "missing_essential_fields" in res_val
    missing = res_val["missing_essential_fields"]

    # 4. simulate_data with fixed seed 42
    res_sim = agent._tool_simulate_data(filepath=filepath, missing_fields=missing, seed=42)
    assert res_sim["status"] == "success"
    assert res_sim["seed"] == 42
    assert len(res_sim["warnings"]) > 0
    assert any("[SIMULATED]" in w for w in res_sim["warnings"])

    # 5. bulk_insert
    res_insert = agent._tool_bulk_insert(db=db_session, filepath=filepath)
    assert res_insert["status"] == "success"
    assert res_insert["products_inserted"] == 3

    # Verify DB rows exist
    products = db_session.query(Product).all()
    assert len(products) == 3
    inventory = db_session.query(Inventory).all()
    assert len(inventory) == 3
