import json
import sys
import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf, current_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.db_writer import insert_score, insert_bias_alert
from processing.sentiment_model import get_sentiment_score
from processing.bias_detector import detect_bias
from processing.trust_score_calculator import compute_trust_score
from monitoring.alert_config import TRUST_SCORE_THRESHOLD, ALERTABLE_BIAS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UDF wrapper functions outside class (Fix for SparkContext serialization error)
def sentiment_wrapper(text):
    try:
        return get_sentiment_score(text) if text else 0.0
    except Exception as e:
        logger.error(f"Error in sentiment UDF: {e}")
        return 0.0

def bias_wrapper(text):
    try:
        return detect_bias(text) if text else "No Bias"
    except Exception as e:
        logger.error(f"Error in bias UDF: {e}")
        return "No Bias"

def trust_wrapper(text, sentiment=None, bias=None):
    try:
        if not text:
            return 50.0
        sentiment_val = sentiment if sentiment is not None else get_sentiment_score(text)
        bias_val = bias if bias else detect_bias(text)
        return compute_trust_score(text, sentiment_val, bias_val)
    except Exception as e:
        logger.error(f"Error in trust score UDF: {e}")
        return 50.0

# Define UDFs globally
sentiment_udf = udf(sentiment_wrapper, DoubleType())
bias_udf = udf(bias_wrapper, StringType())
trust_udf = udf(trust_wrapper, DoubleType())

class ZobonStreamProcessor:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("ZOBON-Stream-Processor") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        self.schema = StructType() \
            .add("source", StringType()) \
            .add("platform", StringType()) \
            .add("brand", StringType()) \
            .add("text", StringType()) \
            .add("timestamp", StringType()) \
            .add("url", StringType()) \
            .add("score", StringType()) \
            .add("likes", StringType()) \
            .add("author", StringType())

    def read_from_kafka(self, topic):
        return self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()

    def process_stream(self, topic):
        try:
            kafka_df = self.read_from_kafka(topic)

            json_df = kafka_df.selectExpr("CAST(value AS STRING)") \
                .select(from_json(col("value"), self.schema).alias("data")) \
                .select("data.*")

            processed_df = json_df \
                .withColumn("sentiment", sentiment_udf(col("text"))) \
                .withColumn("bias", bias_udf(col("text"))) \
                .withColumn("trust_score", trust_udf(col("text"))) \
                .withColumn("processed_at", current_timestamp())

            query = processed_df.writeStream \
                .foreachBatch(self._write_batch_to_db) \
                .outputMode("append") \
                .option("checkpointLocation", f"/tmp/zobon_checkpoint_{topic}") \
                .trigger(processingTime='30 seconds') \
                .start()

            logger.info(f"Started processing stream for topic: {topic}")
            return query

        except Exception as e:
            logger.error(f"Error processing stream for topic {topic}: {e}")
            return None

    def _write_batch_to_db(self, df, epoch_id):
        try:
            records = df.toJSON().collect()
            logger.info(f"Processing batch {epoch_id} with {len(records)} records")

            for record_json in records:
                try:
                    record = json.loads(record_json)
                    db_record = {
                        'source': record.get('source'),
                        'platform': record.get('platform'),
                        'brand': record.get('brand'),
                        'text': record.get('text'),
                        'sentiment': record.get('sentiment'),
                        'bias': record.get('bias'),
                        'trust_score': record.get('trust_score'),
                        'timestamp': record.get('timestamp'),
                        'metadata': {
                            'url': record.get('url'),
                            'score': record.get('score'),
                            'likes': record.get('likes'),
                            'author': record.get('author'),
                            'processed_at': record.get('processed_at')
                        }
                    }

                    record_id = insert_score(db_record)

                    if record_id:
                        self._check_and_send_alerts(record)

                except Exception as e:
                    logger.error(f"Error processing individual record: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")

    def _check_and_send_alerts(self, record):
        try:
            trust_score = record.get('trust_score', 50)
            bias = record.get('bias', 'No Bias')
            brand = record.get('brand', 'Unknown')
            text = record.get('text', '')

            if trust_score < TRUST_SCORE_THRESHOLD:
                alert_level = "CRITICAL" if trust_score < 20 else "HIGH"
                insert_bias_alert(brand, f"Low Trust Score: {trust_score}", trust_score, text, alert_level)
                self._send_realtime_alert(record, f"Trust score dropped to {trust_score}")

            if bias in ALERTABLE_BIAS:
                insert_bias_alert(brand, bias, trust_score, text, "HIGH")
                self._send_realtime_alert(record, f"Bias detected: {bias}")

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _send_realtime_alert(self, record, message):
        try:
            from monitoring.sns_alert import send_alert_sms
            from monitoring.cloudwatch_integration import log_alert

            brand = record.get('brand', 'Unknown')
            trust_score = record.get('trust_score', 0)
            bias = record.get('bias', 'Unknown')

            alert_message = f"🚨 ZOBON Alert: {message} for {brand} campaign"
            log_alert(record.get('source'), brand, trust_score, bias)
            send_alert_sms(alert_message)

            logger.info(f"Sent real-time alert: {alert_message}")

        except Exception as e:
            logger.error(f"Error sending real-time alert: {e}")

    def start_all_streams(self):
        topics = ["reddit_topic", "youtube_topic", "gnews_topic"]
        queries = []

        for topic in topics:
            query = self.process_stream(topic)
            if query:
                queries.append(query)

        if queries:
            logger.info(f"Started {len(queries)} streaming queries")
            for query in queries:
                query.awaitTermination()
        else:
            logger.error("No streaming queries started successfully")

def main():
    processor = ZobonStreamProcessor()
    try:
        logger.info("Starting ZOBON Stream Processor...")
        processor.start_all_streams()
    except KeyboardInterrupt:
        logger.info("Stream processor interrupted by user")
    except Exception as e:
        logger.error(f"Error in stream processor: {e}")
    finally:
        processor.spark.stop()

if __name__ == "__main__":
    main()
