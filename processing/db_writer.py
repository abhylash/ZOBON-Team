import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.pool
from dotenv import load_dotenv
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection_pool = None
        self._create_connection_pool()
        self._create_tables()

    def _create_connection_pool(self):
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "zobon_db"),
                user=os.getenv("POSTGRES_USER", "zobon_user"),
                password=os.getenv("POSTGRES_PASSWORD", "zobon_pass")
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating database connection pool: {e}")
            raise

    def _create_tables(self):
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS campaign_scores (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            platform VARCHAR(50),
            brand VARCHAR(100) NOT NULL,
            text TEXT NOT NULL,
            sentiment FLOAT NOT NULL,
            bias VARCHAR(100) NOT NULL,
            trust_score FLOAT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bias_alerts (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(100) NOT NULL,
            bias_type VARCHAR(100) NOT NULL,
            trust_score FLOAT NOT NULL,
            text_sample TEXT,
            alert_level VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS brand_performance (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(100) NOT NULL,
            date DATE NOT NULL,
            avg_trust_score FLOAT NOT NULL,
            total_mentions INTEGER NOT NULL,
            positive_sentiment_pct FLOAT NOT NULL,
            negative_sentiment_pct FLOAT NOT NULL,
            bias_violations INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(brand, date)
        );

        CREATE INDEX IF NOT EXISTS idx_brand_timestamp ON campaign_scores(brand, timestamp);
        CREATE INDEX IF NOT EXISTS idx_trust_score ON campaign_scores(trust_score);
        CREATE INDEX IF NOT EXISTS idx_created_at ON campaign_scores(created_at);
        """

        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(create_tables_sql)
            conn.commit()
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def insert_score(self, record):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            query = """
            INSERT INTO campaign_scores 
            (source, platform, brand, text, sentiment, bias, trust_score, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """

            data = (
                record.get('source'),
                record.get('platform'),
                record.get('brand'),
                record.get('text'),
                record.get('sentiment'),
                record.get('bias'),
                record.get('trust_score'),
                record.get('timestamp'),
                json.dumps(record.get('metadata', {}))
            )

            cursor.execute(query, data)
            record_id = cursor.fetchone()[0]
            conn.commit()
            logger.debug(f"Inserted record with ID: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Error inserting score record: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def insert_bias_alert(self, brand, bias_type, trust_score, text_sample, alert_level="HIGH"):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            query = """
            INSERT INTO bias_alerts 
            (brand, bias_type, trust_score, text_sample, alert_level, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """

            data = (brand, bias_type, trust_score, text_sample[:500], alert_level, datetime.utcnow())

            cursor.execute(query, data)
            alert_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Inserted bias alert with ID: {alert_id}")
            return alert_id

        except Exception as e:
            logger.error(f"Error inserting bias alert: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def get_brand_scores(self, brand, limit=100):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
            SELECT * FROM campaign_scores 
            WHERE brand = %s 
            ORDER BY timestamp DESC 
            LIMIT %s;
            """

            cursor.execute(query, (brand, limit))
            results = cursor.fetchall()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error fetching brand scores: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def get_recent_alerts(self, limit=50):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
            SELECT * FROM bias_alerts 
            WHERE resolved = FALSE 
            ORDER BY created_at DESC 
            LIMIT %s;
            """

            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error fetching recent alerts: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def update_brand_performance(self, brand, date, performance_data):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            query = """
            INSERT INTO brand_performance 
            (brand, date, avg_trust_score, total_mentions, positive_sentiment_pct, 
             negative_sentiment_pct, bias_violations)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (brand, date) 
            DO UPDATE SET
                avg_trust_score = EXCLUDED.avg_trust_score,
                total_mentions = EXCLUDED.total_mentions,
                positive_sentiment_pct = EXCLUDED.positive_sentiment_pct,
                negative_sentiment_pct = EXCLUDED.negative_sentiment_pct,
                bias_violations = EXCLUDED.bias_violations,
                updated_at = CURRENT_TIMESTAMP;
            """

            data = (
                brand, date,
                performance_data['avg_trust_score'],
                performance_data['total_mentions'],
                performance_data['positive_sentiment_pct'],
                performance_data['negative_sentiment_pct'],
                performance_data['bias_violations']
            )

            cursor.execute(query, data)
            conn.commit()
            logger.info(f"Updated performance data for {brand} on {date}")

        except Exception as e:
            logger.error(f"Error updating brand performance: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)

# Global instance
db_manager = DatabaseManager()

# Convenience methods
def insert_score(record): return db_manager.insert_score(record)

def insert_bias_alert(brand, bias_type, trust_score, text_sample, alert_level="HIGH"):
    return db_manager.insert_bias_alert(brand, bias_type, trust_score, text_sample, alert_level)

def get_recent_alerts(limit=50):
    return db_manager.get_recent_alerts(limit)

def get_brand_scores(brand, limit=100):
    return db_manager.get_brand_scores(brand, limit)

def update_brand_performance(brand, date, performance_data):
    return db_manager.update_brand_performance(brand, date, performance_data)

# Make connection_pool accessible
connection_pool = db_manager.connection_pool
