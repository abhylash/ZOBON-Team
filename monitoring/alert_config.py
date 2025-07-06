# 📁 monitoring/alert_config.py
"""
Alert configuration module for ZOBON Trust Score Monitoring System
Defines thresholds, bias categories, and alert levels for real-time monitoring
"""

import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class BiasCategory(Enum):
    """Bias detection categories"""
    URBAN_BIAS = "Urban Bias"
    UNDERREPRESENTED_REGION = "Underrepresented Region"
    ELITIST_MESSAGING = "Elitist Messaging"
    DEMOGRAPHIC_BIAS = "Demographic Bias"
    ECONOMIC_BIAS = "Economic Bias"
    CULTURAL_BIAS = "Cultural Bias"
    NO_BIAS = "No Bias"

# Trust Score Thresholds
TRUST_SCORE_THRESHOLD = 50
CRITICAL_TRUST_THRESHOLD = 20
LOW_TRUST_THRESHOLD = 30

# Alertable Bias Types
ALERTABLE_BIAS = [
    BiasCategory.URBAN_BIAS.value,
    BiasCategory.UNDERREPRESENTED_REGION.value,
    BiasCategory.ELITIST_MESSAGING.value,
    BiasCategory.DEMOGRAPHIC_BIAS.value,
    BiasCategory.ECONOMIC_BIAS.value,
    BiasCategory.CULTURAL_BIAS.value
]

# Alert Configuration
ALERT_CONFIG = {
    'trust_score': {
        'critical': 20,
        'high': 30,
        'medium': 40,
        'low': 50
    },
    'sentiment': {
        'very_negative': -0.8,
        'negative': -0.5,
        'neutral': 0.0,
        'positive': 0.5,
        'very_positive': 0.8
    },
    'processing': {
        'batch_size_threshold': 1000,
        'processing_time_threshold': 300,  # seconds
        'error_rate_threshold': 0.05  # 5%
    }
}

# Brand-specific thresholds (can be customized per brand)
BRAND_SPECIFIC_THRESHOLDS = {
    'default': {
        'trust_score_threshold': TRUST_SCORE_THRESHOLD,
        'bias_sensitivity': 'medium',
        'alert_frequency': 'immediate'
    }
}

# Alert channels configuration
ALERT_CHANNELS = {
    'sms': {
        'enabled': True,
        'for_levels': [AlertLevel.HIGH.value, AlertLevel.CRITICAL.value]
    },
    'email': {
        'enabled': True,
        'for_levels': [AlertLevel.MEDIUM.value, AlertLevel.HIGH.value, AlertLevel.CRITICAL.value]
    },
    'slack': {
        'enabled': False,
        'for_levels': [AlertLevel.HIGH.value, AlertLevel.CRITICAL.value]
    },
    'dashboard': {
        'enabled': True,
        'for_levels': [level.value for level in AlertLevel]
    }
}

# Rate limiting for alerts (to prevent spam)
ALERT_RATE_LIMITS = {
    'per_brand_per_hour': 10,
    'per_bias_type_per_hour': 5,
    'critical_alerts_per_hour': 20
}

def get_alert_level_for_trust_score(trust_score: float) -> str:
    """
    Determine alert level based on trust score
    
    Args:
        trust_score: Trust score value (0-100)
        
    Returns:
        Alert level string
    """
    try:
        if trust_score < ALERT_CONFIG['trust_score']['critical']:
            return AlertLevel.CRITICAL.value
        elif trust_score < ALERT_CONFIG['trust_score']['high']:
            return AlertLevel.HIGH.value
        elif trust_score < ALERT_CONFIG['trust_score']['medium']:
            return AlertLevel.MEDIUM.value
        elif trust_score < ALERT_CONFIG['trust_score']['low']:
            return AlertLevel.LOW.value
        else:
            return None
    except Exception as e:
        logger.error(f"Error determining alert level for trust score {trust_score}: {e}")
        return AlertLevel.MEDIUM.value

def get_alert_level_for_bias(bias_type: str) -> str:
    """
    Determine alert level based on bias type
    
    Args:
        bias_type: Type of bias detected
        
    Returns:
        Alert level string
    """
    try:
        if bias_type in [BiasCategory.ELITIST_MESSAGING.value, BiasCategory.DEMOGRAPHIC_BIAS.value]:
            return AlertLevel.HIGH.value
        elif bias_type in ALERTABLE_BIAS:
            return AlertLevel.MEDIUM.value
        else:
            return AlertLevel.LOW.value
    except Exception as e:
        logger.error(f"Error determining alert level for bias {bias_type}: {e}")
        return AlertLevel.MEDIUM.value

def should_send_alert(alert_level: str, channel: str) -> bool:
    """
    Check if alert should be sent to specific channel based on level
    
    Args:
        alert_level: Alert severity level
        channel: Alert channel name
        
    Returns:
        Boolean indicating if alert should be sent
    """
    try:
        channel_config = ALERT_CHANNELS.get(channel, {})
        if not channel_config.get('enabled', False):
            return False
        
        return alert_level in channel_config.get('for_levels', [])
    except Exception as e:
        logger.error(f"Error checking alert channel {channel} for level {alert_level}: {e}")
        return False

def get_brand_threshold(brand: str, metric: str) -> Optional[float]:
    """
    Get brand-specific threshold for a metric
    
    Args:
        brand: Brand name
        metric: Metric name (trust_score_threshold, etc.)
        
    Returns:
        Threshold value or None if not found
    """
    try:
        brand_config = BRAND_SPECIFIC_THRESHOLDS.get(brand, BRAND_SPECIFIC_THRESHOLDS['default'])
        return brand_config.get(metric)
    except Exception as e:
        logger.error(f"Error getting brand threshold for {brand}, {metric}: {e}")
        return None

def validate_config() -> bool:
    """
    Validate alert configuration on startup
    
    Returns:
        Boolean indicating if configuration is valid
    """
    try:
        # Check if required thresholds are set
        required_thresholds = ['TRUST_SCORE_THRESHOLD', 'CRITICAL_TRUST_THRESHOLD']
        for threshold in required_thresholds:
            if globals().get(threshold) is None:
                logger.error(f"Required threshold {threshold} not configured")
                return False
        
        # Validate alert channels
        for channel, config in ALERT_CHANNELS.items():
            if not isinstance(config.get('enabled'), bool):
                logger.error(f"Invalid enabled setting for channel {channel}")
                return False
        
        logger.info("Alert configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating alert configuration: {e}")
        return False

# Initialize validation on import
if not validate_config():
    logger.warning("Alert configuration validation failed - some features may not work correctly")