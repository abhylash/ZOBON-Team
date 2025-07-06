
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZobonKafkaProducer:
    def __init__(self, bootstrap_servers=['localhost:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            acks='all'
        )
    
    def send_to_kafka(self, topic, data, key=None):
        """Send data to Kafka topic"""
        try:
            if isinstance(data, list):
                for item in data:
                    future = self.producer.send(topic, value=item, key=key)
                    future.add_callback(self._on_send_success)
                    future.add_errback(self._on_send_error)
            else:
                future = self.producer.send(topic, value=data, key=key)
                future.add_callback(self._on_send_success)
                future.add_errback(self._on_send_error)
            
            self.producer.flush()
            logger.info(f"Successfully sent data to topic: {topic}")
            
        except KafkaError as e:
            logger.error(f"Failed to send data to Kafka: {e}")
            
    def _on_send_success(self, record_metadata):
        logger.info(f"Message sent to {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
    
    def _on_send_error(self, excp):
        logger.error(f"Failed to send message: {excp}")
        
    def close(self):
        self.producer.close()

# Global producer instance
producer = ZobonKafkaProducer()

def send_to_kafka(topic, data, key=None):
    """Convenience function for sending data to Kafka"""
    producer.send_to_kafka(topic, data, key)