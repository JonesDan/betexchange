
from utils_db import query_sqlite, init_db, delete_sample_files, upsert_sqlite, sqlite_tables
market_filter_str = ''

# selection_exposure_data = query_sqlite(f"""
#                         WITH numbered AS (
#                                     SELECT
#                                         runs,
#                                         profit,
#                                         runs - ROW_NUMBER() OVER (PARTITION BY profit ORDER BY runs) AS grp
#                                     FROM selection_exposure_overs
#                                     ),
#                                     grouped AS (
#                                     SELECT
#                                         MIN(runs) AS start_run,
#                                         MAX(runs) AS end_run,
#                                         profit
#                                     FROM numbered
#                                     GROUP BY profit, grp
#                                     ),
#                                     max_run AS (
#                                     SELECT MAX(runs) AS max_run FROM your_table
#                                     ),
#                                     formatted AS (
#                                     SELECT
#                                         CASE 
#                                         WHEN start_run = end_run AND end_run = (SELECT max_run FROM max_run)
#                                             THEN CAST(end_run AS TEXT) || '+'
#                                         WHEN start_run = end_run
#                                             THEN CAST(start_run AS TEXT)
#                                         WHEN end_run = (SELECT max_run FROM max_run)
#                                             THEN CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT) || '+'
#                                         ELSE
#                                             CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT)
#                                         END AS runs,
#                                         profit
#                                     FROM grouped
#                                     )
#                                     SELECT * FROM formatted;
#                                 """)


selection_exp_overs = query_sqlite(f"""
                        WITH numbered AS (
                                    SELECT
                                        runs,
                                        profit,
                                        runs - ROW_NUMBER() OVER (PARTITION BY profit ORDER BY runs) AS grp
                                    FROM selection_exposure_overs
                                    ),
                                    grouped AS (
                                    SELECT
                                        MIN(runs) AS start_run,
                                        MAX(runs) AS end_run,
                                        profit
                                    FROM numbered
                                    GROUP BY profit, grp
                                    ),
                                    max_run AS (
                                    SELECT MAX(runs) AS max_run FROM selection_exposure_overs
                                    ),
                                    formatted AS (
                                    SELECT
                                        CASE 
                                        WHEN start_run = end_run AND end_run = (SELECT max_run FROM max_run)
                                            THEN CAST(end_run AS TEXT) || '+'
                                        WHEN start_run = end_run
                                            THEN CAST(start_run AS TEXT)
                                        WHEN end_run = (SELECT max_run FROM max_run)
                                            THEN CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT) || '+'
                                        ELSE
                                            CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT)
                                        END AS runs,
                                        profit
                                    FROM grouped
                                    )
                                    SELECT * FROM formatted;
                                """)

# selection_exp_overs = query_sqlite(f"""
#                                     SELECT
#                                         runs,
#                                         profit,
#                                         runs - ROW_NUMBER() OVER (PARTITION BY profit ORDER BY runs) AS grp
#                                     FROM selection_exposure_overs
#                                 """)

for data in selection_exp_overs:
    print(data)
    # print('')
    # upsert_sqlite('selection_exposure', data)