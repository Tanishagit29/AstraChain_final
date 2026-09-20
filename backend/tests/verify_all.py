import sys
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(client, method, path, json_body=None, headers=None):
    try:
        if method == "GET":
            res = client.get(f"{BASE_URL}{path}", headers=headers)
        elif method == "POST":
            res = client.post(f"{BASE_URL}{path}", json=json_body, headers=headers)
        elif method == "OPTIONS":
            res = client.options(f"{BASE_URL}{path}", headers=headers)
        else:
            return False, f"Unsupported method {method}"

        if res.status_code in [200, 201]:
            data = res.json()
            if isinstance(data, dict) and data.get("success") is True:
                return True, f"HTTP {res.status_code} - OK (Envelope success: true)"
            elif "status" in data:
                return True, f"HTTP {res.status_code} - OK ({data})"
            else:
                return True, f"HTTP {res.status_code} - OK"
        else:
            return False, f"HTTP {res.status_code} - Response: {res.text}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def run_verification():
    print("=" * 70)
    print("TRANSITOPS BACKEND COMPREHENSIVE VERIFICATION AUDIT")
    print("=" * 70)
    
    results = []

    with httpx.Client(timeout=10.0) as client:
        # 1. Health Check
        ok, msg = test_endpoint(client, "GET", "/")
        results.append(("1. Health Check GET /", ok, msg))

        # 2. CORS Preflight Check
        cors_headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type"
        }
        res_cors = client.options(f"{BASE_URL}/api/dashboard", headers=cors_headers)
        cors_ok = res_cors.headers.get("access-control-allow-origin") in ["http://localhost:5173", "*"]
        results.append(("2. CORS Preflight (http://localhost:5173)", cors_ok, f"Access-Control-Allow-Origin: {res_cors.headers.get('access-control-allow-origin')}"))

        # 3. JWT Auth Flow Verification
        test_email = "verifier_test@transitops.ai"
        test_pwd = "VerificationPassword2026!"

        # Register
        reg_ok, reg_msg = test_endpoint(client, "POST", "/api/auth/register", {
            "email": test_email,
            "password": test_pwd,
            "full_name": "System Verifier",
            "role": "QA_LEAD"
        })
        results.append(("3.1 Auth - Register User", reg_ok, reg_msg))

        # Login
        login_res = client.post(f"{BASE_URL}/api/auth/login", json={"email": test_email, "password": test_pwd})
        login_data = login_res.json() if login_res.status_code == 200 else {}
        access_token = login_data.get("data", {}).get("access_token")
        refresh_token = login_data.get("data", {}).get("refresh_token")
        login_ok = bool(access_token and refresh_token)
        results.append(("3.2 Auth - Login & Receive Tokens", login_ok, f"Received Access Token: {bool(access_token)}"))

        # Protected Route
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_ok, me_msg = test_endpoint(client, "GET", "/api/auth/me", headers=auth_headers)
        results.append(("3.3 Auth - Access Protected Route (/api/auth/me)", me_ok, me_msg))

        # Refresh Token
        ref_ok, ref_msg = test_endpoint(client, "POST", "/api/auth/refresh", {"refresh_token": refresh_token})
        results.append(("3.4 Auth - Refresh Access Token", ref_ok, ref_msg))

        # 4. API Modules Verification
        endpoints = [
            ("4.1 Dashboard", "GET", "/api/dashboard", None),
            ("4.2 Forecast - List", "GET", "/api/forecast", None),
            ("4.3 Forecast - Product", "GET", "/api/forecast/MK-001-F", None),
            ("4.4 Forecast - Generate", "POST", "/api/forecast/generate", {"horizon_days": 14}),
            ("4.5 Inventory - List", "GET", "/api/inventory", None),
            ("4.6 Inventory - Detail", "GET", "/api/inventory/MK-001-F", None),
            ("4.7 Inventory - Stockout Risk", "GET", "/api/inventory/stockout-risk", None),
            ("4.8 Inventory - Overstock Risk", "GET", "/api/inventory/overstock-risk", None),
            ("4.9 Inventory - Reorder Recs", "GET", "/api/inventory/reorder-recommendations", None),
            ("4.10 Suppliers - List", "GET", "/api/suppliers", None),
            ("4.11 Suppliers - Detail", "GET", "/api/suppliers/SUP-01", None),
            ("4.12 Suppliers - Reliability", "GET", "/api/suppliers/reliability", None),
            ("4.13 Suppliers - Lead Time", "GET", "/api/suppliers/lead-time", None),
            ("4.14 Suppliers - Risk", "GET", "/api/suppliers/risk", None),
            ("4.15 Routes - List", "GET", "/api/routes", None),
            ("4.16 Routes - Detail", "GET", "/api/routes/RT-8841", None),
            ("4.17 Routes - Optimize", "POST", "/api/routes/optimize", {"truck_id": "MH-04-JK-4821", "destination": "Pune Logistics Hub"}),
            ("4.18 Wastage - List", "GET", "/api/wastage", None),
            ("4.19 Wastage - Near Expiry", "GET", "/api/wastage/near-expiry", None),
            ("4.20 Wastage - Discount Recs", "GET", "/api/wastage/discount-recommendations", None),
            ("4.21 Wastage - Expected Loss", "GET", "/api/wastage/expected-waste", None),
            ("4.22 AI - Chat", "POST", "/api/ai/chat", {"message": "Check Fresh Milk stockout risk"}),
            ("4.23 AI - Recommendations", "GET", "/api/ai/recommendations", None),
            ("4.24 AI - Agents Telemetry", "GET", "/api/ai/agents", None),
            ("4.25 Automation - Rules", "GET", "/api/automation/rules", None),
            ("4.26 Automation - Approve", "POST", "/api/automation/approve", {"rule_id": "AUT-101", "action": "APPROVE"}),
            ("4.27 Automation - Reject", "POST", "/api/automation/reject", {"rule_id": "AUT-101", "action": "REJECT"}),
            ("4.28 Automation - History", "GET", "/api/automation/history", None),
            ("4.29 Reports - List", "GET", "/api/reports", None),
            ("4.30 Reports - Weekly", "GET", "/api/reports/weekly", None),
            ("4.31 Reports - Monthly", "GET", "/api/reports/monthly", None),
            ("4.32 Reports - Export", "POST", "/api/reports/export", {"title": "Q4 Audit", "report_type": "Audit"}),
        ]

        for title, method, path, body in endpoints:
            ok, msg = test_endpoint(client, method, path, body)
            results.append((title, ok, msg))

    print("\nVERIFICATION SUMMARY:")
    passed_count = sum(1 for _, ok, _ in results if ok)
    total_count = len(results)
    
    for title, ok, msg in results:
        status_str = "[ PASS ]" if ok else "[ FAIL ]"
        print(f"{status_str} {title}: {msg}")

    print("=" * 70)
    print(f"FINAL RESULT: {passed_count}/{total_count} PASSED ({(passed_count/total_count)*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
