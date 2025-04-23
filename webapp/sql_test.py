
from utils_db import query_sqlite, init_db, delete_sample_files
prices = query_sqlite(f"""
                                               SELECT 
                                p.market_id AS market_id,
                                m.market_name AS market_name,
                                p.selection_id AS selection_id,
                                m.selection_name AS selection_name,
                                p.side AS side,
                                MAX(p.publish_time) AS publish_time,
                                GROUP_CONCAT(p.price) AS priceList, 
                                GROUP_CONCAT(p.size) AS sizeList,
                                SUM(s.exposure) AS exposure
                            FROM price p
                            JOIN market_catalogue m
                                ON p.market_id = m.market_id AND p.selection_id = m.selection_id
                            LEFT JOIN selection_exposure s
                                ON m.market_id = s.market_id  AND m.selection_id = s.selection_id
                            WHERE p.market_id = '1.242779502'
                            GROUP BY p.market_id, m.market_name, p.selection_id, m.selection_name, p.side
                            ORDER BY p.selection_id, p.level
                    """)

print(prices)

                    # JOIN market_catalogue m
                    #     ON p.market_id = m.market_id AND p.selection_id = m.selection_id
                    # LEFT JOIN selection_exposure s
                    #     ON m.market_id = s.market_id  AND m.selection_id = s.selection_id
                    # GROUP BY p.market_id, m.market_name, p.selection_id, m.selection_name, p.side