
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        
        # Add EV-specific lexicon
        self.ev_lexicon = {
            'sustainable': 2.0,
            'eco-friendly': 2.0,
            'green': 1.5,
            'clean': 1.5,
            'efficient': 1.5,
            'innovative': 1.5,
            'charging': 0.5,
            'range': 0.0,
            'expensive': -1.5,
            'slow': -1.0,
            'limited': -1.0,
            'inconvenient': -1.5,
            'unreliable': -2.0,
            'overhyped': -1.5
        }
        
        # Update VADER lexicon with EV terms
        for word, score in self.ev_lexicon.items():
            self.analyzer.lexicon[word] = score
    
    def preprocess_text(self, text):
        """Clean and preprocess text for sentiment analysis"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove HTML tags
        text = re.sub(r'<.*?>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def get_sentiment_score(self, text):
        """Calculate sentiment score for given text"""
        try:
            if not text:
                return 0.0
                
            cleaned_text = self.preprocess_text(text)
            
            if not cleaned_text:
                return 0.0
                
            # Get VADER scores
            scores = self.analyzer.polarity_scores(cleaned_text)
            
            # Return compound score (-1 to +1)
            compound_score = scores['compound']
            
            logger.debug(f"Text: '{cleaned_text[:50]}...' | Sentiment: {compound_score}")
            
            return round(compound_score, 4)
            
        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
            return 0.0
    
    def get_detailed_sentiment(self, text):
        """Get detailed sentiment breakdown"""
        try:
            cleaned_text = self.preprocess_text(text)
            scores = self.analyzer.polarity_scores(cleaned_text)
            
            return {
                'compound': round(scores['compound'], 4),
                'positive': round(scores['pos'], 4),
                'negative': round(scores['neg'], 4),
                'neutral': round(scores['neu'], 4),
                'sentiment_label': self._get_sentiment_label(scores['compound'])
            }
            
        except Exception as e:
            logger.error(f"Error in detailed sentiment analysis: {e}")
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'sentiment_label': 'neutral'
            }
    
    def _get_sentiment_label(self, compound_score):
        """Convert compound score to sentiment label"""
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'

# Global analyzer instance
analyzer = SentimentAnalyzer()

def get_sentiment_score(text):
    """Convenience function for getting sentiment score"""
    return analyzer.get_sentiment_score(text)

def get_detailed_sentiment(text):
    """Convenience function for getting detailed sentiment"""
    return analyzer.get_detailed_sentiment(text)