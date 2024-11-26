# database.py

import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH, INTERVAL_SECONDS
from logger import logger

# Timer context manager for measuring operation durations
import time
from contextlib import contextmanager

@contextmanager
def timer(operation):
    start_time = time.perf_counter()
    yield
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{operation} took {elapsed_time:.2f} seconds")

@contextmanager
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        logger.info("Successfully connected to the database.")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        conn.close()
        logger.info("Database connection closed.")

def fetch_recent_full_texts(conn, interval_seconds=INTERVAL_SECONDS):
    """
    Fetches recent full texts from the allText table within the specified interval.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        interval_seconds (int, optional): The time interval in seconds to look back. Defaults to INTERVAL_SECONDS.

    Returns:
        list of tuples: Retrieved records containing frame_id, full_text, and langid.
    """
    try:
        cursor = conn.cursor()

        # Convert interval from seconds to days for julianday comparison
        max_diff_days = interval_seconds / 86400.0  # 86400 seconds in a day

        logger.debug(f"Interval seconds: {interval_seconds}")
        logger.debug(f"Maximum Julian day difference: {max_diff_days}")

        query = """
        SELECT
            at.frameId AS frame_id,
            at.text AS full_text,
            at.lid AS langid
        FROM
            allText at
        JOIN
            frames f ON at.frameId = f.id
        WHERE
            julianday('now') - julianday(f.timestamp) <= ?
            AND julianday('now') - julianday(f.timestamp) >= 0
        ORDER BY
            f.timestamp DESC;
        """

        logger.debug("Executing the SQL query to fetch recent full texts.")

        with timer("Database query"):
            cursor.execute(query, (max_diff_days,))
            results = cursor.fetchall()

        logger.info(f"Found {len(results)} new entries.")
        return results

    except sqlite3.Error as e:
        logger.error(f"Database error during fetch: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during fetch: {e}")
        raise
    