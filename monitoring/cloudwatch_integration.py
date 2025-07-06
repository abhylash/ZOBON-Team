# 📁 monitoring/cloudwatch_integration.py
"""
CloudWatch integration module for ZOBON Trust Score Monitoring System
Handles logging, metrics, and monitoring integration with AWS CloudWatch
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class CloudWatchLogger:
    """CloudWatch integration for ZOBON monitoring"""
    
    def __init__(self):
        """Initialize CloudWatch clients"""
        try:
            # Initialize AWS clients
            self.logs_client = boto3.client(
                'logs',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "ap-south-1")
            )
            
            self.cloudwatch_client = boto3.client(
                'cloudwatch',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "ap-south-1")
            )
            
            # Configuration
            self.log_group_name = os.getenv("CLOUDWATCH_LOG_GROUP", "/zobon/alerts")
            self.log_stream_name = f"zobon-stream-{datetime.now().strftime('%Y-%m-%d')}"
            self.namespace = "ZOBON/TrustScore"
            
            # Ensure log group and stream exist
            self._ensure_log_infrastructure()
            
            logger.info("CloudWatch integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CloudWatch integration: {e}")
            self.logs_client = None
            self.cloudwatch_client = None
    
    def _ensure_log_infrastructure(self):
        """Ensure CloudWatch log group and stream exist"""
        try:
            # Create log group if it doesn't exist
            try:
                self.logs_client.create_log_group(logGroupName=self.log_group_name)
                logger.info(f"Created CloudWatch log group: {self.log_group_name}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                    raise
            
            # Create log stream if it doesn't exist
            try:
                self.logs_client.create_log_stream(
                    logGroupName=self.log_group_name,
                    logStreamName=self.log_stream_name
                )
                logger.info(f"Created CloudWatch log stream: {self.log_stream_name}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                    raise
                    
        except Exception as e:
            logger.error(f"Error ensuring log infrastructure: {e}")
    
    def log_alert(self, source: str, brand: str, trust_score: float, bias: str, 
                  alert_level: str = "MEDIUM", additional_data: Optional[Dict] = None):
        """
        Log alert to CloudWatch with structured data
        
        Args:
            source: Data source (reddit, youtube, gnews)
            brand: Brand name
            trust_score: Trust score value
            bias: Bias type detected
            alert_level: Alert severity level
            additional_data: Additional context data
        """
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Prepare log message
            log_data = {
                "timestamp": timestamp.isoformat(),
                "event_type": "bias_alert",
                "source": source,
                "brand": brand,
                "trust_score": trust_score,
                "bias": bias,
                "alert_level": alert_level,
                "additional_data": additional_data or {}
            }
            
            # Log to local file as fallback
            local_message = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ALERT: {brand} campaign (source: {source}) scored {trust_score} with bias: {bias} (Level: {alert_level})"
            print(local_message)
            
            # Log to CloudWatch if available
            if self.logs_client:
                self._send_to_cloudwatch_logs(log_data)
            
            # Send metrics to CloudWatch
            if self.cloudwatch_client:
                self._send_metrics(source, brand, trust_score, bias, alert_level)
                
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
    
    def _send_to_cloudwatch_logs(self, log_data: Dict[str, Any]):
        """Send log data to CloudWatch Logs"""
        try:
            log_message = json.dumps(log_data)
            timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            response = self.logs_client.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=[
                    {
                        'timestamp': timestamp_ms,
                        'message': log_message
                    }
                ]
            )
            
            logger.debug(f"Sent log to CloudWatch: {response}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidSequenceTokenException':
                # Handle sequence token issue by creating new stream
                self._create_new_log_stream()
                self._send_to_cloudwatch_logs(log_data)
            else:
                logger.error(f"CloudWatch Logs error: {e}")
        except Exception as e:
            logger.error(f"Error sending to CloudWatch Logs: {e}")
    
    def _send_metrics(self, source: str, brand: str, trust_score: float, 
                     bias: str, alert_level: str):
        """Send metrics to CloudWatch"""
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Prepare metric data
            metric_data = [
                {
                    'MetricName': 'TrustScore',
                    'Dimensions': [
                        {'Name': 'Source', 'Value': source},
                        {'Name': 'Brand', 'Value': brand}
                    ],
                    'Value': trust_score,
                    'Unit': 'None',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'AlertCount',
                    'Dimensions': [
                        {'Name': 'AlertLevel', 'Value': alert_level},
                        {'Name': 'BiasType', 'Value': bias}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                }
            ]
            
            # Add bias-specific metrics
            if bias != "No Bias":
                metric_data.append({
                    'MetricName': 'BiasDetected',
                    'Dimensions': [
                        {'Name': 'Source', 'Value': source},
                        {'Name': 'BiasType', 'Value': bias}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                })
            
            # Send metrics
            self.cloudwatch_client.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
            logger.debug(f"Sent metrics to CloudWatch for {brand}")
            
        except Exception as e:
            logger.error(f"Error sending metrics to CloudWatch: {e}")
    
    def _create_new_log_stream(self):
        """Create new log stream with current timestamp"""
        try:
            self.log_stream_name = f"zobon-stream-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            self.logs_client.create_log_stream(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name
            )
            logger.info(f"Created new log stream: {self.log_stream_name}")
        except Exception as e:
            logger.error(f"Error creating new log stream: {e}")
    
    def log_processing_metrics(self, batch_size: int, processing_time: float, 
                             error_count: int = 0):
        """
        Log processing performance metrics
        
        Args:
            batch_size: Number of records processed
            processing_time: Time taken to process batch
            error_count: Number of errors encountered
        """
        try:
            if not self.cloudwatch_client:
                return
                
            timestamp = datetime.now(timezone.utc)
            
            metric_data = [
                {
                    'MetricName': 'BatchSize',
                    'Value': batch_size,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'ProcessingTime',
                    'Value': processing_time,
                    'Unit': 'Seconds',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'ErrorCount',
                    'Value': error_count,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                }
            ]
            
            if batch_size > 0:
                metric_data.append({
                    'MetricName': 'ErrorRate',
                    'Value': (error_count / batch_size) * 100,
                    'Unit': 'Percent',
                    'Timestamp': timestamp
                })
            
            self.cloudwatch_client.put_metric_data(
                Namespace=f"{self.namespace}/Processing",
                MetricData=metric_data
            )
            
            logger.debug(f"Sent processing metrics: batch_size={batch_size}, processing_time={processing_time}")
            
        except Exception as e:
            logger.error(f"Error logging processing metrics: {e}")
    
    def create_alarm(self, alarm_name: str, metric_name: str, threshold: float, 
                    comparison_operator: str = "LessThanThreshold"):
        """
        Create CloudWatch alarm for monitoring
        
        Args:
            alarm_name: Name of the alarm
            metric_name: Metric to monitor
            threshold: Threshold value
            comparison_operator: Comparison operator for threshold
        """
        try:
            if not self.cloudwatch_client:
                logger.warning("CloudWatch client not available for creating alarm")
                return
                
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator=comparison_operator,
                EvaluationPeriods=2,
                MetricName=metric_name,
                Namespace=self.namespace,
                Period=300,  # 5 minutes
                Statistic='Average',
                Threshold=threshold,
                ActionsEnabled=True,
                AlarmDescription=f'ZOBON monitoring alarm for {metric_name}',
                Unit='None'
            )
            
            logger.info(f"Created CloudWatch alarm: {alarm_name}")
            
        except Exception as e:
            logger.error(f"Error creating CloudWatch alarm: {e}")

# Global instance
cloudwatch_logger = CloudWatchLogger()

def log_alert(source: str, brand: str, trust_score: float, bias: str, 
              alert_level: str = "MEDIUM", additional_data: Optional[Dict] = None):
    """
    Convenience function for logging alerts
    
    Args:
        source: Data source
        brand: Brand name
        trust_score: Trust score value
        bias: Bias type
        alert_level: Alert level
        additional_data: Additional context
    """
    cloudwatch_logger.log_alert(source, brand, trust_score, bias, alert_level, additional_data)

def log_processing_metrics(batch_size: int, processing_time: float, error_count: int = 0):
    """
    Convenience function for logging processing metrics
    
    Args:
        batch_size: Batch size processed
        processing_time: Processing time in seconds
        error_count: Number of errors
    """
    cloudwatch_logger.log_processing_metrics(batch_size, processing_time, error_count)