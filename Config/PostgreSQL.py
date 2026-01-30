import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2 import OperationalError, ProgrammingError, pool
from dotenv import load_dotenv
import datetime
import logging

# --- 1. Set up basic logging to stdout ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

class PostgresClient:
    _pool = None
    def __init__(self):
        self.conn = None
        self._connect()

    @classmethod
    def _get_pool(cls):
        """Create or get a connection pool"""
        if cls._pool is None:
            try:
                logger.info(f"Create a connection pool")
                cls._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=os.getenv("POSTGRES_URL"),
                    port=os.getenv("POSTGRES_PORT"),
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    dbname=os.getenv("POSTGRES_DB_NAME")    
                )
                logger.info("✓ PostgreSQL connection pool created")
            except Exception as e:
                logger.info(f"Error found in creating or getting from PG pool")
                raise
        return cls._pool

    def _connect(self):
        """Internal method to handle the database connection and logging."""
        """Updated to connect from pool rather than a single connection """
        try:
            logger.info("Attempting to connect to PostgreSQL database using connection pool.")
            pool = self._get_pool()
            self.conn = pool.getconn()
            self.conn.autocommit = True
            logger.info("Successfully connected to PostgreSQL database.")
        except OperationalError as e:
            # This handles connection-related errors
            logger.error("Failed to connect to PostgreSQL database.")
            logger.exception(e)
            raise RuntimeError("Database connection failed") from e
        except Exception as e:
            logger.exception("An unexpected error occurred during database connection.")
            raise RuntimeError("Database connection failed") from e
    

    def _test_connection(self):
        """ Helper function to test the connection and reconnect if necessary."""
        if self.conn and not self.conn.closed:
            try:
                with self.conn.cursor() as curr:
                    curr.execute('SELECT 1')
                return True
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                logger.warning("Database connection is stale/broken, attempting to reconnect")
                self._connect()
                return False
        elif not self.conn or self.conn.closed:
            logger.warning("Datebase connection is closed, attepting to connect")
            self._connect()
            return False
        return True


    @contextmanager
    def _get_cursor_transaction(self, cursor_factory=None):
        if not self._test_connection():
            logger.warning("Unable to re-connect to database")
            
        if not self.conn or self.conn.closed:
            logger.warning("Datebase connection is closed.")
            self._connect()
        self.conn.autocommit = False
        curr = self.conn.cursor(cursor_factory=cursor_factory)
        try:
            yield curr
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            logger.exception("Transaction rolled back due to errors")
            raise
        finally:
            curr.close()
            if self.conn and not self.conn.closed:
                self.conn.autocommit = True
    
    def _get_cursor(self, cursor_factory=None):
        """Internal helper to get a cursor and handle potential connection issues."""
        if not self._test_connection():
            logger.warning("Unable to re-connect to database")
        if not self.conn or self.conn.closed:
            logger.warning("Database connection is closed. Attempting to reconnect...")
            self._connect()
        return self.conn.cursor(cursor_factory=cursor_factory)

    def fetch_one(self, query, params=None):
        try:
            with self._get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                logger.debug(f"Executed query: {query} with params: {params}")
                return cursor.fetchone()
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e
        
    def fetch_all(self, query, params=None):
        try:
            with self._get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                logger.debug(f"Executed query: {query} with params: {params}")
                return cursor.fetchall()
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e

    def execute(self, query, params=None):
        try:
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                logger.info(f"Executed command: {query} with params: {params}")
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute command: {query}")
            logger.exception(e)
            raise RuntimeError("Database command failed") from e
    
    def execute_res(self, query, params=None):
        try:
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                logger.info(f"Executed command: {query} with params: {params}")
                affected = cursor.rowcount
                return affected
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute command: {query}")
            logger.exception(e)
            raise RuntimeError("Database command failed") from e
                
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed.")