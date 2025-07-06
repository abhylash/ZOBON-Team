#!/usr/bin/env python3
"""
Model Evaluation Script for ZOBON Trust Score Monitoring System
Evaluates sentiment analysis, bias detection, and trust score calculation accuracy
"""

import json
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.sentiment_model import get_sentiment_score, get_detailed_sentiment
from processing.bias_detector import detect_bias, get_bias_details
from processing.trust_score_calculator import compute_trust_score
from processing.db_writer import db_manager

class ModelEvaluator:
    def __init__(self):
        self.test_data = []
        self.results = {}
        
        # Ground truth test cases for sentiment analysis
        self.sentiment_test_cases = [
            # Positive cases
            {"text": "Tesla Model 3 is absolutely amazing! Best car I've ever owned.", "expected": "positive"},
            {"text": "Love the government incentives for EVs. Great policy decision!", "expected": "positive"},
            {"text": "Charging infrastructure has improved significantly in our city.", "expected": "positive"},
            {"text": "My electric scooter saves me so much money on fuel.", "expected": "positive"},
            
            # Negative cases
            {"text": "EV prices are ridiculously high. Only rich people can afford them.", "expected": "negative"},
            {"text": "Charging takes forever and there are no stations in rural areas.", "expected": "negative"},
            {"text": "My EV broke down and service center is 300km away. Terrible!", "expected": "negative"},
            {"text": "These electric vehicles are just a marketing gimmick.", "expected": "negative"},
            
            # Neutral cases
            {"text": "Considering buying an electric vehicle. Any recommendations?", "expected": "neutral"},
            {"text": "Government announced new EV policy. Details are not clear yet.", "expected": "neutral"},
            {"text": "Saw a charging station being installed near my office.", "expected": "neutral"},
            {"text": "My friend bought an EV. Still evaluating if it's worth it.", "expected": "neutral"}
        ]
        
        # Ground truth test cases for bias detection
        self.bias_test_cases = [
            # Urban Bias
            {"text": "All these EVs are great for city folks, but what about us in villages?", "expected": "Urban Bias"},
            {"text": "Metro cities get all the charging stations while rural areas are ignored.", "expected": "Urban Bias"},
            
            # Economic Bias
            {"text": "₹30 lakhs for an EV? Only rich people can think of green future.", "expected": "Economic Bias"},
            {"text": "These luxury EVs are not for common man like us.", "expected": "Economic Bias"},
            
            # Tech Literacy Bias
            {"text": "All these apps and digital features are too complicated for elderly people.", "expected": "Tech Literacy Bias"},
            {"text": "Young tech-savvy people find EVs easy, but what about others?", "expected": "Tech Literacy Bias"},
            
            # No Bias
            {"text": "EVs are becoming more affordable and accessible to everyone.", "expected": "No Bias"},
            {"text": "The technology is improving and benefiting all segments of society.", "expected": "No Bias"}
        ]
        
        # Trust score validation cases
        self.trust_score_cases = [
            # High trust (positive sentiment, no bias)
            {"text": "Great EV with excellent features for everyone.", "expected_range": (70, 100)},
            
            # Low trust (negative sentiment, high bias)
            {"text": "Overpriced EVs only for rich urban elite, useless for poor rural folks.", "expected_range": (0, 40)},
            
            # Medium trust (neutral sentiment, some bias)
            {"text": "EVs are okay but mainly suitable for city dwellers.", "expected_range": (40, 70)}
        ]

    def evaluate_sentiment_model(self):
        """Evaluate sentiment analysis model performance"""
        print("Evaluating Sentiment Analysis Model...")
        
        predictions = []
        actuals = []
        
        for case in self.sentiment_test_cases:
            sentiment_score = get_sentiment_score(case["text"])
            
            # Convert score to label
            if sentiment_score > 0.05:
                predicted = "positive"
            elif sentiment_score < -0.05:
                predicted = "negative"
            else:
                predicted = "neutral"
            
            predictions.append(predicted)
            actuals.append(case["expected"])
            
            print(f"Text: {case['text'][:50]}...")
            print(f"Expected: {case['expected']}, Predicted: {predicted}, Score: {sentiment_score:.3f}")
            print("-" * 80)
        
        # Calculate metrics
        accuracy = accuracy_score(actuals, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(actuals, predictions, average='weighted')
        
        self.results['sentiment'] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': confusion_matrix(actuals, predictions).tolist(),
            'labels': sorted(list(set(actuals)))
        }
        
        print(f"\nSentiment Analysis Results:")
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"F1-Score: {f1:.3f}")

    def evaluate_bias_detection(self):
        """Evaluate bias detection model performance"""
        print("\nEvaluating Bias Detection Model...")
        
        predictions = []
        actuals = []
        
        for case in self.bias_test_cases:
            predicted_bias = detect_bias(case["text"])
            
            predictions.append(predicted_bias)
            actuals.append(case["expected"])
            
            print(f"Text: {case['text'][:50]}...")
            print(f"Expected: {case['expected']}, Predicted: {predicted_bias}")
            print("-" * 80)
        
        # Calculate metrics
        accuracy = accuracy_score(actuals, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(actuals, predictions, average='weighted')
        
        self.results['bias'] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': confusion_matrix(actuals, predictions).tolist(),
            'labels': sorted(list(set(actuals)))
        }
        
        print(f"\nBias Detection Results:")
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"F1-Score: {f1:.3f}")

    def evaluate_trust_score(self):
        """Evaluate trust score calculation"""
        print("\nEvaluating Trust Score Calculation...")
        
        correct_predictions = 0
        total_predictions = len(self.trust_score_cases)
        
        for case in self.trust_score_cases:
            text = case["text"]
            expected_range = case["expected_range"]
            
            # Get individual components
            sentiment = get_sentiment_score(text)
            bias = detect_bias(text)
            trust_score = compute_trust_score(text, sentiment, bias)
            
            # Check if score is within expected range
            in_range = expected_range[0] <= trust_score <= expected_range[1]
            if in_range:
                correct_predictions += 1
            
            print(f"Text: {text[:50]}...")
            print(f"Sentiment: {sentiment:.3f}, Bias: {bias}")
            print(f"Trust Score: {trust_score:.2f}, Expected Range: {expected_range}")
            print(f"✓ Correct" if in_range else "✗ Incorrect")
            print("-" * 80)
        
        accuracy = correct_predictions / total_predictions
        
        self.results['trust_score'] = {
            'range_accuracy': accuracy,
            'correct_predictions': correct_predictions,
            'total_predictions': total_predictions
        }
        
        print(f"\nTrust Score Results:")
        print(f"Range Accuracy: {accuracy:.3f}")
        print(f"Correct Predictions: {correct_predictions}/{total_predictions}")

    def evaluate_with_database_data(self, sample_size=100):
        """Evaluate models using real database data"""
        print(f"\nEvaluating with {sample_size} database records...")
        
        try:
            # Get sample data from database
            conn = db_manager.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT text, sentiment, bias, trust_score, brand, platform
                FROM campaign_scores 
                ORDER BY RANDOM()
                LIMIT %s
            """, (sample_size,))
            
            records = cursor.fetchall()
            
            if not records:
                print("No data found in database for evaluation")
                return
            
            sentiment_mse = []
            trust_score_mse = []
            bias_accuracy = []
            
            for record in records:
                original_text = record[0]
                original_sentiment = record[1]
                original_bias = record[2]
                original_trust = record[3]
                
                # Re-calculate with current models
                new_sentiment = get_sentiment_score(original_text)
                new_bias = detect_bias(original_text)
                new_trust = compute_trust_score(original_text, new_sentiment, new_bias)
                
                # Calculate differences
                sentiment_mse.append((original_sentiment - new_sentiment) ** 2)
                trust_score_mse.append((original_trust - new_trust) ** 2)
                bias_accuracy.append(1 if original_bias == new_bias else 0)
            
            # Calculate metrics
            sentiment_rmse = np.sqrt(np.mean(sentiment_mse))
            trust_rmse = np.sqrt(np.mean(trust_score_mse))
            bias_acc = np.mean(bias_accuracy)
            
            self.results['database_validation'] = {
                'sentiment_rmse': sentiment_rmse,
                'trust_score_rmse': trust_rmse,
                'bias_accuracy': bias_acc,
                'sample_size': len(records)
            }
            
            print(f"Database Validation Results:")
            print(f"Sentiment RMSE: {sentiment_rmse:.4f}")
            print(f"Trust Score RMSE: {trust_rmse:.4f}")
            print(f"Bias Consistency: {bias_acc:.3f}")
            
        except Exception as e:
            print(f"Error evaluating with database data: {e}")
        finally:
            if conn:
                db_manager.connection_pool.putconn(conn)

    def plot_confusion_matrices(self):
        """Plot confusion matrices for classification tasks"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Sentiment confusion matrix
        if 'sentiment' in self.results:
            cm_sentiment = np.array(self.results['sentiment']['confusion_matrix'])
            labels_sentiment = self.results['sentiment']['labels']
            
            sns.heatmap(cm_sentiment, annot=True, fmt='d', cmap='Blues',
                       xticklabels=labels_sentiment, yticklabels=labels_sentiment,
                       ax=axes[0])
            axes[0].set_title('Sentiment Analysis Confusion Matrix')
            axes[0].set_xlabel('Predicted')
            axes[0].set_ylabel('Actual')
        
        # Bias confusion matrix
        if 'bias' in self.results:
            cm_bias = np.array(self.results['bias']['confusion_matrix'])
            labels_bias = self.results['bias']['labels']
            
            sns.heatmap(cm_bias, annot=True, fmt='d', cmap='Reds',
                       xticklabels=labels_bias, yticklabels=labels_bias,
                       ax=axes[1])
            axes[1].set_title('Bias Detection Confusion Matrix')
            axes[1].set_xlabel('Predicted')
            axes[1].set_ylabel('Actual')
        
        plt.tight_layout()
        plt.savefig('model_evaluation_results.png', dpi=300, bbox_inches='tight')
        plt.show()

    def generate_evaluation_report(self):
        """Generate comprehensive evaluation report"""
        report = {
            'evaluation_timestamp': datetime.utcnow().isoformat(),
            'models_evaluated': list(self.results.keys()),
            'results': self.results,
            'summary': {
                'sentiment_model': {
                    'status': 'Good' if self.results.get('sentiment', {}).get('accuracy', 0) > 0.7 else 'Needs Improvement',
                    'accuracy': self.results.get('sentiment', {}).get('accuracy', 0)
                },
                'bias_model': {
                    'status': 'Good' if self.results.get('bias', {}).get('accuracy', 0) > 0.7 else 'Needs Improvement',
                    'accuracy': self.results.get('bias', {}).get('accuracy', 0)
                },
                'trust_score': {
                    'status': 'Good' if self.results.get('trust_score', {}).get('range_accuracy', 0) > 0.7 else 'Needs Improvement',
                    'accuracy': self.results.get('trust_score', {}).get('range_accuracy', 0)
                }
            }
        }
        
        # Save report
        with open('evaluation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\nEvaluation Report Summary:")
        print("=" * 50)
        for model, details in report['summary'].items():
            print(f"{model.upper()}: {details['status']} (Accuracy: {details['accuracy']:.3f})")
        
        print(f"\nDetailed report saved to: evaluation_report.json")
        
        return report

    def run_full_evaluation(self, db_sample_size=100, generate_plots=True):
        """Run complete model evaluation"""
        print("Starting ZOBON Model Evaluation")
        print("=" * 50)
        
        # Run all evaluations
        self.evaluate_sentiment_model()
        self.evaluate_bias_detection()
        self.evaluate_trust_score()
        self.evaluate_with_database_data(db_sample_size)
        
        # Generate visualizations
        if generate_plots:
            try:
                self.plot_confusion_matrices()
            except Exception as e:
                print(f"Error generating plots: {e}")
        
        # Generate final report
        report = self.generate_evaluation_report()
        
        return report

def main():
    """Main function with CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate ZOBON models')
    parser.add_argument('--sentiment', action='store_true', help='Evaluate sentiment model only')
    parser.add_argument('--bias', action='store_true', help='Evaluate bias detection only')
    parser.add_argument('--trust', action='store_true', help='Evaluate trust score only')
    parser.add_argument('--db-sample', type=int, default=100, help='Database sample size for validation')
    parser.add_argument('--no-plots', action='store_true', help='Skip generating plots')
    parser.add_argument('--output', type=str, default='evaluation_report.json', help='Output report filename')
    
    args = parser.parse_args()
    
    evaluator = ModelEvaluator()
    
    try:
        if args.sentiment:
            evaluator.evaluate_sentiment_model()
        elif args.bias:
            evaluator.evaluate_bias_detection()
        elif args.trust:
            evaluator.evaluate_trust_score()
        else:
            # Run full evaluation
            report = evaluator.run_full_evaluation(
                db_sample_size=args.db_sample,
                generate_plots=not args.no_plots
            )
            
            print(f"\nEvaluation completed successfully!")
            print(f"Report saved to: {args.output}")
            
    except KeyboardInterrupt:
        print("\nEvaluation cancelled by user")
    except Exception as e:
        print(f"Error during evaluation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()