
from utils_db import query_sqlite, init_db, delete_sample_files, upsert_sqlite, sqlite_tables
market_id = '1.242816694'
data = {'bet_id': '386311948893', 'average_price_matched': 1.63, 'bsp_liability': 0.0, 'handicap': 0.0, 'market_id': '1.242278972', 'matched_date': '2025-04-23T14H-59M-04S', 'order_type': 'LIMIT', 'persistence_type': 'LAPSE', 'placed_date': '2025-04-23T14H-59M-04S', 'regulator_auth_code': None, 'regulator_code': 'GIBRALTAR REGULATOR', 'selection_id': 55190, 'side': 'BACK', 'size_cancelled': 0.0, 'size_lapsed': 0.0, 'size_matched': 1.0, 'size_remaining': 0.0, 'size_voided': 0.0, 'status': 'EXECUTION_COMPLETE', 'customer_strategy_ref': None, 'customer_order_ref': None, 'lapsed_date': None, 'lapse_status_reason_code': None, 'cancelled_date': None, 'current_item_description': None, 'price': 1.63, 'size': 1.0}
upsert_sqlite('orders',data)
table = 'orders'

columns = ', '.join([col['name'] for col in sqlite_tables[table] if col['name'] in data])
values2 = ', '.join(['"' + data[col['name']] + '"' if isinstance(data[col['name']], str) else str(data[col['name']]) for col in sqlite_tables[table] if col['name'] in data])

print(columns)
print(values2)