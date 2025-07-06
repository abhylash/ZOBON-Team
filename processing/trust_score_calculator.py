
import logging
import math
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SankalpScoreCalculator:
    def __init__(self):
        # Define weights for different components
        self.weights = {
            'sentiment': 0.4,      # 40% - How positive/negative the sentiment is
            'bias': 0.3,           # 30% - Bias penalty
            'authenticity': 0.2,   # 20% - Authenticity indicators
            'engagement': 0.1      # 10% - Engagement quality
        }
        
        # Bias penalties (0-1, where 1 is maximum penalty)
        self.bias_penalties = {
            "No Bias": 0.0,
            "Urban Bias": 0.3,
            "Rural Underrepresentation": 0.4,
            "Economic Bias": 0.35,
            "Gender Bias": 0.25,
            "Age Bias": 0.2,
            "Tech Literacy Bias": 0.3,
            "Regional Language Bias": 0.25
        }
    
    def compute_trust_score(self, text, sentiment, bias, metadata=None):
        """Compute the Sankalp Score (Trust Score)
        
        Args:
            text: The text content
            sentiment: Sentiment score (-1 to +1)
            bias: Bias type detected
            metadata: Additional metadata (likes, shares, etc.)
        
        Returns:
            float: Sankalp Score (0-100)
        """
        try:
            if not text:
                return 50.0  # Neutral score for empty text
            
            # 1. Sentiment Component (0-1)
            sentiment_component = self._calculate_sentiment_component(sentiment)
            
            # 2. Bias Component (0-1)
            bias_component = self._calculate_bias_component(bias)
            
            # 3. Authenticity Component (0-1)
            authenticity_component = self._calculate_authenticity_component(text, metadata)
            
            # 4. Engagement Component (0-1)
            engagement_component = self._calculate_engagement_component(metadata)
            
            # Calculate weighted score
            raw_score = (
                sentiment_component * self.weights['sentiment'] +
                bias_component * self.weights['bias'] +
                authenticity_component * self.weights['authenticity'] +
                engagement_component * self.weights['engagement']
            )
            
            # Convert to 0-100 scale and apply non-linear transformation
            sankalp_score = self._apply_sankalp_transformation(raw_score)
            
            logger.debug(f"Sankalp Score: {sankalp_score} | Sentiment: {sentiment} | Bias: {bias}")
            
            return round(sankalp_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating trust score: {e}")
            return 50.0  # Return neutral score on error
    
    def _calculate_sentiment_component(self, sentiment):
        """Calculate sentiment component (0-1)"""
        # Normalize sentiment from [-1, 1] to [0, 1]
        return (sentiment + 1) / 2
    
    def _calculate_bias_component(self, bias):
        """Calculate bias component (0-1)"""
        penalty = self.bias_penalties.get(bias, 0.3)
        return 1 - penalty
    
    def _calculate_authenticity_component(self, text, metadata):
        """Calculate authenticity component based on text characteristics"""
        if not text:
            return 0.5
        
        authenticity_score = 0.5  # Base score
        
        # Check text length (very short or very long texts are suspicious)
        text_length = len(text.split())
        if 10 <= text_length <= 200:
            authenticity_score += 0.2
        elif text_length < 5 or text_length > 500:
            authenticity_score -= 0.2
        
        # Check for spam indicators
        spam_indicators = ['!!!', '???', 'click here', 'buy now', 'limited time']
        spam_count = sum(1 for indicator in spam_indicators if indicator.lower() in text.lower())
        authenticity_score -= spam_count * 0.1
        
        # Check for balanced language (not too extreme)
        extreme_words = ['amazing', 'terrible', 'worst', 'best', 'perfect', 'horrible']
        extreme_count = sum(1 for word in extreme_words if word.lower() in text.lower())
        if extreme_count > 3:
            authenticity_score -= 0.1
        
        # Normalize to [0, 1]
        return max(0, min(1, authenticity_score))
    
    def _calculate_engagement_component(self, metadata):
        """Calculate engagement component based on metadata"""
        if not metadata:
            return 0.5
        
        engagement_score = 0.5
        
        # Consider likes/upvotes
        likes = metadata.get('likes', 0) or metadata.get('score', 0)
        if likes > 0:
            engagement_score += min(0.3, likes / 100)
        elif likes < -5:
            engagement_score -= 0.2
        
        # Consider comments/replies
        comments = metadata.get('num_comments', 0)
        if comments > 0:
            engagement_score += min(0.2, comments / 50)
        
        return max(0, min(1, engagement_score))
    
    def _apply_sankalp_transformation(self, raw_score):
        """Apply Sankalp-specific transformation to raw score"""
        # Apply sigmoid-like transformation for better distribution
        # This makes extreme scores less common and emphasizes the middle range
        transformed = 1 / (1 + math.exp(-6 * (raw_score - 0.5)))
        
        # Scale to 0-100
        return transformed * 100

# Global calculator instance
calculator = SankalpScoreCalculator()

def compute_trust_score(text, sentiment, bias, metadata=None):
    """Convenience function for computing trust score"""
    return calculator.compute_trust_score(text, sentiment, bias, metadata)

def get_score_interpretation(score):
    """Get interpretation of Sankalp Score"""
    if score >= 80:
        return "Excellent - Highly trustworthy and ethical"
    elif score >= 60:
        return "Good - Generally trustworthy with minor concerns"
    elif score >= 40:
        return "Fair - Moderate trust with some ethical concerns"
    elif score >= 20:
        return "Poor - Low trust with significant ethical issues"
    else:
        return "Critical - Severe ethical concerns detected"