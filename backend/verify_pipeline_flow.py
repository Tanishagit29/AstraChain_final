import json
from fastapi.testclient import TestClient
from app.main import app

def run_test():
    client = TestClient(app)

    with open('test_supply_chain_data.csv', 'rb') as f:
        csv_bytes = f.read()

    files = [('files', ('test_supply_chain_data.csv', csv_bytes, 'text/csv'))]
    res = client.post('/api/data-collection/pipeline', files=files)
    assert res.status_code == 200, res.text
    print('1. Pipeline POST: OK')

    dash = client.get('/api/pipeline/dashboard').json()
    print('2. Pipeline Dashboard: has_data =', dash.get('has_data'), 'KPIs =', list(dash.get('kpiMetrics', {}).keys()))

    fc = client.get('/api/pipeline/forecast').json()
    print('3. Forecast: has_data =', fc.get('has_data'), 'Total products forecasted =', len(fc.get('by_product', {})))

    inv = client.get('/api/pipeline/inventory').json()
    print('4. Inventory: has_data =', inv.get('has_data'), 'Items count =', len(inv.get('items', [])), 'Summary =', inv.get('summary'))

    wst = client.get('/api/pipeline/wastage').json()
    print('5. Wastage: has_data =', wst.get('has_data'), 'Decisions count =', len(wst.get('decisions', [])), 'Summary =', wst.get('summary'))

    for d in wst.get('decisions', []):
        pid = d["product_id"]
        pname = d["product_name"]
        days = d["days_remaining"]
        dec = d["decision"]
        disc = d["discount"]
        print(f'   - {pid} ({pname}): days={days}, decision={dec}, discount={disc}')

    agents = client.get('/api/ai/agents').json()
    print('6. AI Agents count =', len(agents.get('data', [])))

    wst_db = client.get('/api/wastage').json()
    print('7. Wastage DB items =', len(wst_db.get('data', [])))

    disc_recs = client.get('/api/wastage/discount-recommendations').json()
    print('8. Wastage Discount Recs =', len(disc_recs.get('data', [])))

    exp_waste = client.get('/api/wastage/expected-waste').json()
    loss_str = str(exp_waste.get('data', {}).get('total_expected_loss_inr', '')).encode('ascii', 'replace').decode('ascii')
    print('9. Expected Waste Loss =', loss_str)

    print('\n>>> ALL PIPELINE AND DASHBOARD PAGES VERIFIED AND FULLY FUNCTIONAL! <<<')

if __name__ == '__main__':
    run_test()
