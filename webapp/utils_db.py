import sqlite3
import os
from datetime import datetime
import json
import traceback
import pickle

sqlite_tables = {
    'market_catalogue' : [
        {'name': 'key' , 'type': 'PRIMARY KEY'},
        {'name': 'market_name' , 'type': 'TEXT'},
        {'name': 'market_id' , 'type': 'TEXT'},
        {'name': 'start_time' , 'type': 'TEXT'},
        {'name': 'selection_name' , 'type': 'TEXT'},
        {'name': 'selection_id' , 'type': 'INTEGER'},
        {'name': 'event' , 'type': 'TEXT'},
        {'name': 'total_matched' , 'type': 'REAL'},
    ],
    'orders' : [
        {'name': 'bet_id' , 'type': 'PRIMARY KEY'},
        {'name': 'market_id' , 'type': 'TEXT'},
        {'name': 'selection_id' , 'type': 'INTEGER'},
        {'name': 'placed_date' , 'type': 'TEXT'},
        {'name': 'matched_date' , 'type': 'TEXT'},
        {'name': 'cancelled_date' , 'type': 'TEXT'},
        {'name': 'side' , 'type': 'TEXT'},
        {'name': 'status' , 'type': 'TEXT'},
        {'name': 'price' , 'type': 'REAL'},
        {'name': 'size' , 'type': 'REAL'},
        {'name': 'average_price_matched' , 'type': 'REAL'},
        {'name': 'size_matched' , 'type': 'REAL'},
        {'name': 'size_remaining' , 'type': 'REAL'},
        {'name': 'size_lapsed' , 'type': 'REAL'},
        {'name': 'size_cancelled' , 'type': 'REAL'},
        {'name': 'size_voided' , 'type': 'REAL'},
    ],
    'selection_exposure' : [
        {'name': 'key' , 'type': 'PRIMARY KEY'},
        {'name': 'market_id' , 'type': 'TEXT'},
        {'name': 'market_name' , 'type': 'TEXT'},
        {'name': 'selection_id' , 'type': 'INTEGER'},
        {'name': 'exposure' , 'type': 'REAL'},
    ],
    'selection_exposure_overs' : [
        {'name': 'key' , 'type': 'PRIMARY KEY'},
        {'name': 'market_id' , 'type': 'TEXT'},
        {'name': 'market_name' , 'type': 'TEXT'},
        {'name': 'selection_id' , 'type': 'INTEGER'},
        {'name': 'runs' , 'type': 'INTEGER'},
        {'name': 'profit' , 'type': 'REAL'},
    ],
    'price' : [
        {'name': 'key' , 'type': 'PRIMARY KEY'},
        {'name': 'market_id' , 'type': 'TEXT'},
        {'name': 'selection_id' , 'type': 'INTEGER'},
        {'name': 'publish_time' , 'type': 'TEXT'},
        {'name': 'side' , 'type': 'TEXT'},
        {'name': 'price' , 'type': 'REAL'},
        {'name': 'size' , 'type': 'REAL'},
        {'name': 'level' , 'type': 'INTEGER'},
    ],
    'selected_markets' : [
        {'name': 'market_id' , 'type': 'PRIMARY KEY'},
    ],
}

def calc_order_exposure(market_id='ALL'):

    market_filter_str = "" if market_id == 'ALL' else f"AND m.market_id = '{market_id}'"
    selection_exposure_data = query_sqlite(f"""
                WITH cte_orders AS (
                    SELECT
                            m.market_id || '-' || m.selection_id AS key,
                            m.market_id AS market_id,
                            m.market_name AS market_name,
                            m.selection_id AS selection_id,
                            SUM(CASE WHEN side = 'BACK' THEN o.average_price_matched * o.size_matched ELSE 0 END) AS back_winnings,
                            SUM(CASE WHEN side = 'BACK' THEN (o.average_price_matched * o.size_matched) - o.size_matched ELSE 0 END) AS back_profit,
                            SUM(CASE WHEN side = 'BACK' THEN o.size_matched ELSE 0 END) AS back_size,
                            SUM(CASE WHEN side = 'LAY' THEN o.average_price_matched * o.size_matched ELSE 0 END) AS lay_winnings,
                            SUM(CASE WHEN side = 'LAY' THEN (o.average_price_matched * o.size_matched) - o.size_matched ELSE 0 END) AS lay_liability,
                            SUM(CASE WHEN side = 'LAY' THEN o.size_matched ELSE 0 END) AS lay_profit
                        FROM market_catalogue m
                        LEFT JOIN orders o ON o.market_id = m.market_id AND o.selection_id = m.selection_id
                        WHERE market_name NOT LIKE '%OVERS LINE%' {market_filter_str}
                        GROUP BY key, m.market_id, m.selection_id
                    ),
                    cte_calcs AS (
                        SELECT
                        *,
                        SUM(back_winnings) OVER (PARTITION BY market_id) AS back_winnings_market,
                        SUM(back_profit) OVER (PARTITION BY market_id) AS back_profit_market,
                        SUM(back_size) OVER (PARTITION BY market_id) AS back_size_market,
                        SUM(lay_winnings) OVER (PARTITION BY market_id) AS lay_winnings_market,
                        SUM(lay_liability) OVER (PARTITION BY market_id) AS lay_liability_market,
                        SUM(lay_profit) OVER (PARTITION BY market_id) AS lay_profit_market
                        FROM
                        cte_orders
                    )
                    SELECT
                        key,
                        market_id,
                        market_name,
                        selection_id,
                        COALESCE(back_winnings, 0) - COALESCE(back_size_market, 0) - COALESCE(lay_liability, 0) + COALESCE(lay_profit_market, 0) - COALESCE(lay_profit, 0) AS exposure
                    FROM cte_calcs
                    """)
    
    for results in selection_exposure_data:
        upsert_sqlite('selection_exposure', results)
    
    return selection_exposure_data


def calc_order_exposure_overs(market_id='ALL'):

    market_filter_str = "" if market_id == 'ALL' else f"WHERE market_id = '{market_id}'"
    market_filter_str2 = "" if market_id == 'ALL' else f"AND m.market_id = '{market_id}'"
    
    selection_exposure_data = query_sqlite(f"""
                    WITH RECURSIVE runs_total(n) AS (
                        SELECT 0
                        UNION ALL
                        SELECT n + 1 FROM runs_total WHERE n + 1 <= 
                            (SELECT MAX(price) + 1 FROM orders {market_filter_str})
                    )
                    SELECT
                        m.market_id || '-' || m.selection_id || '-' || rt.n AS key,
                        m.market_id,
                        m.market_name AS market_name,
                        m.selection_id,
                        rt.n AS runs,
                        SUM(CASE WHEN (rt.n > o.average_price_matched AND o.side = 'LAY')
                            OR (rt.n < o.average_price_matched AND o.side = 'BACK') THEN o.size_matched
                            ELSE -o.size_matched END) AS profit
                    FROM runs_total rt
                    CROSS JOIN orders o
                    JOIN market_catalogue m
                        ON o.market_id = m.market_id AND o.selection_id = m.selection_id
                    WHERE m.market_name LIKE '%OVERS LINE%'
                        AND o.status = 'EXECUTION_COMPLETE' 
                        {market_filter_str2}
                    GROUP BY 1, 2, 3, 4
                    ;
                    """)
    
    for results in selection_exposure_data:
        upsert_sqlite('selection_exposure_overs', results)
    
    return selection_exposure_data
    


# Initialize the database (run once at start)
def init_db():
    try:
        with sqlite3.connect('/data/mydata.db') as conn:
            cursor = conn.cursor()
            for table in sqlite_tables:
                sqlstring = ', '.join([f"{tbl['name']} {tbl['type']}" for tbl in sqlite_tables[table]])
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                cursor.execute(f'CREATE TABLE {table} ({sqlstring})')
            conn.commit()
        
        return "No SQL errors creating tables"
    except Exception as e:
        return f"Error with creating tables {e}"
    
def init_selected_markets():
    filename = '/data/selected_markets.pkl'
    with open(filename, 'wb') as f:
        pickle.dump([], f)


def upsert_sqlite(table, data):
    columns = ', '.join([col['name'] for col in sqlite_tables[table] if col['name'] in data])
    values = [data[col['name']]for col in sqlite_tables[table] if col['name'] in data]
    values_placeholder = ', '.join(['?' for col in sqlite_tables[table] if col['name'] in data])

    create_sample_files(table, data)
    with sqlite3.connect('/data/mydata.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f'REPLACE INTO {table} ({columns}) VALUES ({values_placeholder})', values)
        conn.commit()
    

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def query_sqlite(query):
    conn = sqlite3.connect('/data/mydata.db')
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()

    return results
    

def delete_sample_files():
    try:
        for filename in os.listdir('sample'):
            file_path = os.path.join('sample', filename)
            if os.path.isfile(file_path):  # ensures it's a file, not a folder
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                    pass
        
        return f"Deleted sample files"
    except Exception as e:
        return f"Error deleting sample files: {e}"

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def safe_dict(data):
    def make_safe(value):
        try:
            json.dumps(value, default=datetime_serializer)
            return value
        except (TypeError, ValueError):
            return str(value)  # or None, or skip logic

    return {k: make_safe(v) for k, v in data.items()}

def create_sample_files(filename, data):
    try:
        filepath = f'sample/{filename}.json'
        if not os.path.exists(filepath):
            with open(filepath, 'w') as json_file:
                json.dump(safe_dict(data), json_file, indent=4, default=datetime_serializer)
            print(f"File created and data written to: {filepath}")
        return f"File created and data written to: {filepath}"
    
    except Exception as e:
        return f"Error creating sample file: {filename}: {e}"
