
import re
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BiasDetector:
    def __init__(self):
        # Define bias categories and keywords
        self.bias_patterns = {
            "Urban Bias": [
                "delhi", "mumbai", "bangalore", "chennai", "hyderabad", 
                "pune", "kolkata", "metro", "city", "urban", "tier-1"
            ],
            "Rural Underrepresentation": [
                "village", "rural", "bihar", "odisha", "jharkhand", 
                "tier-2", "tier-3", "small town", "countryside"
            ],
            "Economic Bias": [
                "rich", "wealthy", "premium", "luxury", "elite", 
                "upper class", "expensive", "unaffordable"
            ],
            "Gender Bias": [
                "male driver", "men", "guys", "boys", "masculine",
                "female driver", "women", "girls", "ladies", "feminine"
            ],
            "Age Bias": [
                "young", "youth", "millennial", "gen-z", "old", 
                "elderly", "senior", "aged", "boomer"
            ],
            "Tech Literacy Bias": [
                "tech-savvy", "digital", "app", "smartphone", 
                "illiterate", "backward", "traditional"
            ],
            "Regional Language Bias": [
                "english", "hindi", "tamil", "bengali", "marathi",
                "local language", "vernacular", "regional"
            ]
        }
        
        # Define severity weights
        self.bias_severity = {
            "Urban Bias": 0.7,
            "Rural Underrepresentation": 0.9,
            "Economic Bias": 0.8,
            "Gender Bias": 0.6,
            "Age Bias": 0.5,
            "Tech Literacy Bias": 0.7,
            "Regional Language Bias": 0.6
        }
    
    def detect_bias(self, text):
        """Detect bias in given text"""
        if not text or not isinstance(text, str):
            return {"bias_type": "No Bias", "confidence": 0.0, "details": []}
        
        text_lower = text.lower()
        detected_biases = defaultdict(list)
        
        try:
            # Check for each bias pattern
            for bias_type, keywords in self.bias_patterns.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        detected_biases[bias_type].append(keyword)
            
            if not detected_biases:
                return {"bias_type": "No Bias", "confidence": 0.0, "details": []}
            
            # Calculate confidence and determine primary bias
            bias_scores = {}
            for bias_type, keywords in detected_biases.items():
                # Calculate confidence based on keyword frequency and severity
                keyword_count = len(keywords)
                severity = self.bias_severity.get(bias_type, 0.5)
                confidence = min(keyword_count * severity * 0.3, 1.0)
                bias_scores[bias_type] = confidence
            
            # Get the bias with highest confidence
            primary_bias = max(bias_scores.keys(), key=lambda x: bias_scores[x])
            max_confidence = bias_scores[primary_bias]
            
            # Prepare detailed results
            details = []
            for bias_type, keywords in detected_biases.items():
                details.append({
                    "bias_type": bias_type,
                    "keywords_found": keywords,
                    "confidence": bias_scores[bias_type]
                })
            
            logger.debug(f"Detected bias: {primary_bias} (confidence: {max_confidence})")
            
            return {
                "bias_type": primary_bias,
                "confidence": round(max_confidence, 4),
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Error in bias detection: {e}")
            return {"bias_type": "No Bias", "confidence": 0.0, "details": []}
    
    def get_bias_score(self, text):
        """Get numerical bias score (0-1, where 1 is most biased)"""
        bias_result = self.detect_bias(text)
        return bias_result["confidence"]
    
    def is_biased(self, text, threshold=0.3):
        """Check if text contains significant bias"""
        bias_result = self.detect_bias(text)
        return bias_result["confidence"] > threshold
    
    def get_recommendations(self, bias_type):
        """Get recommendations to reduce specific bias"""
        recommendations = {
            "Urban Bias": [
                "Include rural and tier-2/3 city perspectives",
                "Mention infrastructure challenges in smaller towns",
                "Consider diverse geographical contexts"
            ],
            "Rural Underrepresentation": [
                "Highlight rural EV adoption benefits",
                "Address rural-specific concerns",
                "Include rural success stories"
            ],
            "Economic Bias": [
                "Discuss affordable EV options",
                "Mention government subsidies and incentives",
                "Include cost-benefit analysis for middle class"
            ],
            "Gender Bias": [
                "Use gender-neutral language",
                "Include perspectives from all genders",
                "Avoid stereotypical assumptions"
            ],
            "Age Bias": [
                "Consider multi-generational perspectives",
                "Avoid age-specific assumptions",
                "Include diverse age group experiences"
            ],
            "Tech Literacy Bias": [
                "Simplify technical explanations",
                "Consider non-tech-savvy users",
                "Provide multiple interaction options"
            ],
            "Regional Language Bias": [
                "Support multiple languages",
                "Consider local communication preferences",
                "Include regional cultural contexts"
            ]
        }
        
        return recommendations.get(bias_type, ["No specific recommendations available"])

# Global detector instance
detector = BiasDetector()

def detect_bias(text):
    """Convenience function for bias detection"""
    result = detector.detect_bias(text)
    return result["bias_type"]

def get_bias_details(text):
    """Convenience function for detailed bias analysis"""
    return detector.detect_bias(text)

def get_bias_score(text):
    """Convenience function for bias score"""
    return detector.get_bias_score(text)