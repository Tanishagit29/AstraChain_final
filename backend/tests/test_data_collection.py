import io
import pytest

def test_data_collection_lifecycle(client):
    # 1. Prepare raw CSV data containing:
    # - Duplicates (MK-001 is duplicate)
    # - Missing values (YG-500 current_stock is null)
    # - Negative stock values (AP-200 is -50)
    # - Unstandardized name spacings
    csv_content = (
        "sku,name,category,current_stock,forecast_demand,warehouse,unit_cost\n"
        "MK-001,Fresh Milk 1L,Dairy,500,600,Mumbai Central,₹50\n"
        "RC-505,Basmati Rice 5kg,Staples,2000,1800,Pune North,₹420\n"
        "YG-500, Yogurt 500g ,Dairy,,150,Thane East,₹65\n"
        "MK-001,Fresh Milk 1L,Dairy,500,600,Mumbai Central,₹50\n"
        "AP-200,Apple 1kg,Produce,-50,100,Nashik Hub,180\n"
    )

    # 2. Upload the raw file
    files = {"files": ("test_ingestion.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/data-collection/upload", files=files)
    
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "session_id" in upload_data
    assert "quality_report" in upload_data
    assert "eda_summary" in upload_data
    
    session_id = upload_data["session_id"]
    report = upload_data["quality_report"]
    
    # Verify duplicates and negative stocks were detected
    assert report["duplicates"] == 1
    assert "current_stock" in report["missing_values"]
    assert "current_stock" in report["negative_inventories"]
    assert len(upload_data["preview_rows"]) == 5

    # 3. Clean the raw data
    # We will pass imputation_strategy='median' (imputes using median of [500, 2000, -50] which is 500)
    # remove_duplicates=True
    # standardize_fields=True
    clean_params = {
        "session_id": session_id,
        "imputation_strategy": "median",
        "remove_duplicates": True,
        "remove_empty_rows": True,
        "remove_empty_cols": True,
        "outlier_indices_to_remove": "[]",
        "standardize_fields": True
    }
    
    clean_res = client.post("/api/data-collection/clean", data=clean_params)
    assert clean_res.status_code == 200
    clean_data = clean_res.json()
    
    # 5 rows - 1 duplicate = 4 rows
    assert clean_data["total_rows_cleaned"] == 4
    
    # Verify imputation and standardize values (e.g. trim name padding)
    preview = clean_data["preview_rows"]
    
    # Find Yogurt and check its imputed stock
    yogurt = next(r for r in preview if r["sku"] == "YG-500")
    assert yogurt["current_stock"] == 500  # Imputed median value
    assert yogurt["name"] == "Yogurt 500G" # Standardized and title-cased
    
    # 4. Inject cleaned data into the database
    inject_res = client.post(
        "/api/data-collection/inject", 
        data={"session_id": session_id, "target_model": "inventory"}
    )
    assert inject_res.status_code == 200
    assert inject_res.json()["status"] == "success"

    # Verify that database records are updated correctly
    get_res = client.get("/api/inventory?page=1&limit=10")
    assert get_res.status_code == 200
    inventory_items = get_res.json()["data"]["items"]
    
    # Verify that the test SKU elements are present in active database
    skus = [item["id"] for item in inventory_items]
    assert "MK-001" in skus
    assert "RC-505" in skus
    assert "YG-500" in skus
    assert "AP-200" in skus
