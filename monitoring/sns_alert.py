# 📁 monitoring/sns_alert.py
"""
SNS Alert module for ZOBON Trust Score Monitoring System
Handles SMS, email, and multi-channel alert notifications via AWS SNS
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SNSAlertManager:
    """SNS-based alert management for ZOBON system"""
    
    def __init__(self):
        """Initialize SNS client and configuration"""
        try:
            # Initialize SNS client
            self.sns_client = boto3.client(
                "sns",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "ap-south-1")
            )
            
            # Configuration
            self.sms_topic_arn = os.getenv("SNS_TOPIC_ARN")
            self.email_topic_arn = os.getenv("SNS_EMAIL_TOPIC_ARN")
            self.slack_topic_arn = os.getenv("SNS_SLACK_TOPIC_ARN")
            
            # Rate limiting tracking
            self.alert_history = {}
            self.rate_limit_window = timedelta(hours=1)
            self.max_alerts_per_hour = 10
            
            # Validate configuration
            self._validate_configuration()
            
            logger.info("SNS Alert Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SNS Alert Manager: {e}")
            self.sns_client = None
    
    def _validate_configuration(self):
        """Validate SNS configuration"""
        if not self.sms_topic_arn:
            logger.warning("SNS_TOPIC_ARN not configured - SMS alerts will be disabled")
        
        if not self.sns_client:
            logger.error("SNS client initialization failed - alerts will be disabled")
    
    def _check_rate_limit(self, brand: str, alert_type: str) -> bool:
        """
        Check if alert is within rate limits
        
        Args:
            brand: Brand name
            alert_type: Type of alert
            
        Returns:
            Boolean indicating if alert should be sent
        """
        try:
            key = f"{brand}_{alert_type}"
            current_time = datetime.now()
            
            # Clean old entries
            self._clean_old_entries(current_time)
            
            # Count recent alerts for this key
            if key not in self.alert_history:
                self.alert_history[key] = []
            
            recent_alerts = [
                timestamp for timestamp in self.alert_history[key]
                if current_time - timestamp < self.rate_limit_window
            ]
            
            if len(recent_alerts) >= self.max_alerts_per_hour:
                logger.warning(f"Rate limit exceeded for {key}. Skipping alert.")
                return False
            
            # Add current alert to history
            self.alert_history[key].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow alert on error
    
    def _clean_old_entries(self, current_time: datetime):
        """Remove old entries from alert history"""
        try:
            cutoff_time = current_time - self.rate_limit_window
            
            for key in list(self.alert_history.keys()):
                self.alert_history[key] = [
                    timestamp for timestamp in self.alert_history[key]
                    if timestamp > cutoff_time
                ]
                
                # Remove empty entries
                if not self.alert_history[key]:
                    del self.alert_history[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning old alert entries: {e}")
    
    def send_alert_sms(self, message: str, brand: str = "Unknown", 
                      alert_level: str = "MEDIUM") -> bool:
        """
        Send SMS alert via SNS
        
        Args:
            message: Alert message
            brand: Brand name for rate limiting
            alert_level: Alert severity level
            
        Returns:
            Boolean indicating success
        """
        try:
            if not self.sns_client or not self.sms_topic_arn:
                logger.warning("SMS alerts not configured properly")
                return False
            
            # Check rate limiting
            if not self._check_rate_limit(brand, "sms"):
                return False
            
            # Format message with metadata
            formatted_message = self._format_sms_message(message, brand, alert_level)
            
            # Send SMS
            response = self.sns_client.publish(
                TopicArn=self.sms_topic_arn,
                Message=formatted_message,
                Subject="⚠️ ZOBON Trust Alert"
            )
            
            logger.info(f"SMS alert sent successfully: MessageId={response.get('MessageId')}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS SNS error sending SMS: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            return False
    
    def send_email_alert(self, message: str, brand: str, trust_score: float,
                        bias: str, additional_data: Optional[Dict] = None) -> bool:
        """
        Send detailed email alert
        
        Args:
            message: Alert message
            brand: Brand name
            trust_score: Trust score value
            bias: Bias type detected
            additional_data: Additional context data
            
        Returns:
            Boolean indicating success
        """
        try:
            if not self.sns_client or not self.email_topic_arn:
                logger.warning("Email alerts not configured properly")
                return False
            
            # Check rate limiting
            if not self._check_rate_limit(brand, "email"):
                return False
            
            # Format detailed email message
            email_message = self._format_email_message(
                message, brand, trust_score, bias, additional_data
            )
            
            # Send email
            response = self.sns_client.publish(
                TopicArn=self.email_topic_arn,
                Message=email_message,
                Subject=f"ZOBON Alert: {brand} - Trust Score {trust_score}"
            )
            
            logger.info(f"Email alert sent successfully: MessageId={response.get('MessageId')}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS SNS error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
    
    def send_slack_alert(self, message: str, brand: str, alert_level: str) -> bool:
        """
        Send Slack alert via SNS
        
        Args:
            message: Alert message
            brand: Brand name
            alert_level: Alert severity level
            
        Returns:
            Boolean indicating success
        """
        try:
            if not self.sns_client or not self.slack_topic_arn:
                logger.warning("Slack alerts not configured properly")
                return False
            
            # Check rate limiting
            if not self._check_rate_limit(brand, "slack"):
                return False
            
            # Format Slack message
            slack_message = self._format_slack_message(message, brand, alert_level)
            
            # Send to Slack topic
            response = self.sns_client.publish(
                TopicArn=self.slack_topic_arn,
                Message=slack_message
            )
            
            logger.info(f"Slack alert sent successfully: MessageId={response.get('MessageId')}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS SNS error sending Slack alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False
    
    def _format_sms_message(self, message: str, brand: str, alert_level: str) -> str:
        """Format SMS message for optimal delivery"""
        timestamp = datetime.now().strftime("%H:%M")
        severity_emoji = {
            "LOW": "🟡",
            "MEDIUM": "🟠", 
            "HIGH": "🔴",
            "CRITICAL": "🚨"
        }.get(alert_level, "⚠️")
        
        return f"{severity_emoji} ZOBON [{timestamp}]\n{message}\nBrand: {brand}\nLevel: {alert_level}"
    
    def _format_email_message(self, message: str, brand: str, trust_score: float,
                             bias: str, additional_data: Optional[Dict] = None) -> str:
        """Format detailed email message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        email_content = f"""
ZOBON Trust Score Alert

Alert Details:
=============
Timestamp: {timestamp}
Brand: {brand}
Message: {message}
Trust Score: {trust_score}
Bias Detected: {bias}

Alert Summary:
=============
"""
        
        if trust_score < 20:
            email_content += "⚠️ CRITICAL: Trust score is critically low\n"
        elif trust_score < 40:
            email_content += "🔴 HIGH: Trust score is significantly below threshold\n"
        else:
            email_content += "🟠 MEDIUM: Trust score requires attention\n"
        
        if additional_data:
            email_content += f"\nAdditional Context:\n"
            for key, value in additional_data.items():
                email_content += f"- {key}: {value}\n"
        
        email_content += f"""
Recommended Actions:
==================
1. Review the content that triggered this alert
2. Analyze bias patterns for this brand
3. Consider adjusting campaign messaging
4. Monitor trust score trends

For more details, check the ZOBON dashboard.
        """
        
        return email_content
    
    def _format_slack_message(self, message: str, brand: str, alert_level: str) -> str:
        """Format Slack message with rich formatting"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        severity_colors = {
            "LOW": "#ffeb3b",
            "MEDIUM": "#ff9800", 
            "HIGH": "#f44336",
            "CRITICAL": "#e91e63"
        }
        
        color = severity_colors.get(alert_level, "#757575")
        
        slack_payload = {
            "text": f"ZOBON Trust Score Alert - {brand}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Alert Message",
                            "value": message,
                            "short": False
                        },
                        {
                            "title": "Brand",
                            "value": brand,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert_level,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": timestamp,
                            "short": True
                        }
                    ],
                    "footer": "ZOBON Trust Monitoring System",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        return json.dumps(slack_payload)
    
    def send_multi_channel_alert(self, message: str, brand: str, trust_score: float,
                                bias: str, alert_level: str, 
                                channels: Optional[List[str]] = None,
                                additional_data: Optional[Dict] = None) -> Dict[str, bool]:
        """
        Send alert to multiple channels based on configuration
        
        Args:
            message: Alert message
            brand: Brand name
            trust_score: Trust score value
            bias: Bias type
            alert_level: Alert severity level
            channels: Specific channels to use (optional)
            additional_data: Additional context data
            
        Returns:
            Dictionary with channel success status
        """
        results = {}
        
        try:
            # Import alert config to check channel settings
            from .alert_config import should_send_alert
            
            # Default channels based on alert level
            if channels is None:
                channels = []
                if should_send_alert(alert_level, 'sms'):
                    channels.append('sms')
                if should_send_alert(alert_level, 'email'):
                    channels.append('email')
                if should_send_alert(alert_level, 'slack'):
                    channels.append('slack')
            
            # Send to each specified channel
            if 'sms' in channels:
                results['sms'] = self.send_alert_sms(message, brand, alert_level)
            
            if 'email' in channels:
                results['email'] = self.send_email_alert(
                    message, brand, trust_score, bias, additional_data
                )
            
            if 'slack' in channels:
                results['slack'] = self.send_slack_alert(message, brand, alert_level)
            
            # Log summary
            successful_channels = [ch for ch, success in results.items() if success]
            failed_channels = [ch for ch, success in results.items() if not success]
            
            if successful_channels:
                logger.info(f"Alert sent successfully to: {', '.join(successful_channels)}")
            if failed_channels:
                logger.warning(f"Alert failed for channels: {', '.join(failed_channels)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in multi-channel alert: {e}")
            return {channel: False for channel in (channels or [])}
    
    def send_digest_alert(self, alert_summary: Dict[str, Any]) -> bool:
        """
        Send daily/weekly digest of alerts
        
        Args:
            alert_summary: Summary data of alerts
            
        Returns:
            Boolean indicating success
        """
        try:
            if not self.email_topic_arn:
                logger.warning("Email topic not configured for digest alerts")
                return False
            
            # Format digest message
            digest_message = self._format_digest_message(alert_summary)
            
            # Send digest email
            response = self.sns_client.publish(
                TopicArn=self.email_topic_arn,
                Message=digest_message,
                Subject="ZOBON Daily Alert Digest"
            )
            
            logger.info(f"Digest alert sent: MessageId={response.get('MessageId')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending digest alert: {e}")
            return False
    
    def _format_digest_message(self, summary: Dict[str, Any]) -> str:
        """Format digest message with summary statistics"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        message = f"""
ZOBON Daily Alert Digest - {timestamp}

Alert Summary:
=============
Total Alerts: {summary.get('total_alerts', 0)}
Critical Alerts: {summary.get('critical_count', 0)}
High Priority: {summary.get('high_count', 0)}
Medium Priority: {summary.get('medium_count', 0)}

Top Brands by Alert Count:
========================
"""
        
        top_brands = summary.get('top_brands', [])
        for i, (brand, count) in enumerate(top_brands[:5], 1):
            message += f"{i}. {brand}: {count} alerts\n"
        
        message += f"""

Most Common Bias Types:
=====================
"""
        
        bias_types = summary.get('bias_types', [])
        for bias_type, count in bias_types[:5]:
            message += f"- {bias_type}: {count} occurrences\n"
        
        message += f"""

Average Trust Scores:
===================
Overall Average: {summary.get('avg_trust_score', 'N/A')}
Lowest Score: {summary.get('min_trust_score', 'N/A')}
Highest Score: {summary.get('max_trust_score', 'N/A')}

Recommendations:
==============
"""
        
        if summary.get('critical_count', 0) > 0:
            message += "- Immediate attention required for critical alerts\n"
        if summary.get('avg_trust_score', 100) < 40:
            message += "- Overall trust scores are concerning - review campaigns\n"
        if len(top_brands) > 0:
            message += f"- Focus monitoring efforts on {top_brands[0][0]} brand\n"
        
        message += "\nFor detailed analysis, check the ZOBON dashboard."
        
        return message
    
    def test_connectivity(self) -> Dict[str, bool]:
        """
        Test SNS connectivity and topic accessibility
        
        Returns:
            Dictionary with connectivity status for each topic
        """
        results = {}
        
        try:
            if not self.sns_client:
                return {"error": "SNS client not initialized"}
            
            # Test SMS topic
            if self.sms_topic_arn:
                try:
                    self.sns_client.get_topic_attributes(TopicArn=self.sms_topic_arn)
                    results['sms_topic'] = True
                except ClientError:
                    results['sms_topic'] = False
            
            # Test email topic
            if self.email_topic_arn:
                try:
                    self.sns_client.get_topic_attributes(TopicArn=self.email_topic_arn)
                    results['email_topic'] = True
                except ClientError:
                    results['email_topic'] = False
            
            # Test Slack topic
            if self.slack_topic_arn:
                try:
                    self.sns_client.get_topic_attributes(TopicArn=self.slack_topic_arn)
                    results['slack_topic'] = True
                except ClientError:
                    results['slack_topic'] = False
            
            logger.info(f"SNS connectivity test results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error testing SNS connectivity: {e}")
            return {"error": str(e)}

# Global instance
sns_alert_manager = SNSAlertManager()

def send_alert_sms(message: str, brand: str = "Unknown", alert_level: str = "MEDIUM") -> bool:
    """
    Convenience function for sending SMS alerts
    
    Args:
        message: Alert message
        brand: Brand name
        alert_level: Alert severity
        
    Returns:
        Boolean indicating success
    """
    return sns_alert_manager.send_alert_sms(message, brand, alert_level)

def send_multi_channel_alert(message: str, brand: str, trust_score: float,
                           bias: str, alert_level: str = "MEDIUM",
                           additional_data: Optional[Dict] = None) -> Dict[str, bool]:
    """
    Convenience function for multi-channel alerts
    
    Args:
        message: Alert message
        brand: Brand name
        trust_score: Trust score value
        bias: Bias type
        alert_level: Alert severity
        additional_data: Additional context
        
    Returns:
        Dictionary with channel success status
    """
    return sns_alert_manager.send_multi_channel_alert(
        message, brand, trust_score, bias, alert_level, 
        additional_data=additional_data
    )

def test_alert_system() -> Dict[str, bool]:
    """
    Test the alert system connectivity
    
    Returns:
        Dictionary with test results
    """
    return sns_alert_manager.test_connectivity()