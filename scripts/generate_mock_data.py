#!/usr/bin/env python3
"""
Mock Data Generator for ZOBON Trust Score Monitoring System
Generates realistic test data for development and testing purposes
"""

import json
import random
import sys
import os
from datetime import datetime, timedelta
from faker import Faker
import uuid

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.db_writer import db_manager
from processing.sentiment_model import get_sentiment_score
from processing.bias_detector import detect_bias
from processing.trust_score_calculator import compute_trust_score

fake = Faker()

class MockDataGenerator:
    def __init__(self):
        self.brands = [
            "Tesla", "BYD", "Tata Motors", "Mahindra", "Ola Electric", 
            "Ather Energy", "Hero Electric", "TVS Motor", "Bajaj Auto"
        ]
        
        self.platforms = ["Reddit", "YouTube", "Google News", "Twitter", "Instagram"]
        
        self.ev_topics = [
            "charging infrastructure", "battery technology", "electric vehicles",
            "sustainable transport", "green energy", "EV adoption", "government subsidies",
            "range anxiety", "charging time", "maintenance costs"
        ]
        
        self.bias_types = [
            "No Bias", "Urban Bias", "Rural Underrepresentation", "Economic Bias",
            "Gender Bias", "Age Bias", "Tech Literacy Bias", "Regional Language Bias"
        ]
        
        # Sample text templates for different sentiments
        self.positive_templates = [
            "Absolutely love my {brand} electric vehicle! The {feature} is amazing and the charging is so convenient.",
            "Just drove 300km on a single charge with my {brand}. Technology has come so far!",
            "The government incentives for {brand} EVs are really helping middle-class families like ours.",
            "Great to see {brand} expanding charging stations in rural areas. Finally reaching everyone!",
            "My {brand} EV saves me ₹15,000 monthly on fuel costs. Best decision ever!"
        ]
        
        self.negative_templates = [
            "Still waiting for {brand} service center in our small town. City folks get everything first.",
            "₹25 lakhs for a {brand} EV? Only rich people can afford this green technology.",
            "Charging infrastructure is terrible outside major cities. {brand} needs to do better.",
            "My {brand} EV broke down and nearest service center is 200km away. Pathetic!",
            "All these EV ads show young urban professionals. What about rural farmers like us?"
        ]
        
        self.neutral_templates = [
            "Considering buying a {brand} EV. Can anyone share their experience with {feature}?",
            "Government announced new EV policy. How will this affect {brand} pricing?",
            "Saw a {brand} charging station being installed near my office. Good progress.",
            "Test drove {brand} EV today. Still comparing with other options.",
            "My neighbor bought a {brand} EV. Interested to know about long-term costs."
        ]
        
        self.features = [
            "battery life", "charging speed", "autopilot", "infotainment system",
            "build quality", "service network", "resale value", "safety features"
        ]

    def generate_text_content(self, brand, sentiment_target=None):
        """Generate realistic text content for given brand and sentiment"""
        if sentiment_target is None:
            sentiment_target = random.choice(['positive', 'negative', 'neutral'])
        
        if sentiment_target == 'positive':
            template = random.choice(self.positive_templates)
        elif sentiment_target == 'negative':
            template = random.choice(self.negative_templates)
        else:
            template = random.choice(self.neutral_templates)
        
        feature = random.choice(self.features)
        text = template.format(brand=brand, feature=feature)
        
        # Add some randomness
        if random.random() < 0.3:
            topic = random.choice(self.ev_topics)
            text += f" Also interested in {topic}."
        
        return text

    def generate_mock_record(self, brand=None, platform=None, hours_ago=None):
        """Generate a single mock record"""
        if not brand:
            brand = random.choice(self.brands)
        
        if not platform:
            platform = random.choice(self.platforms)
        
        if hours_ago is None:
            hours_ago = random.randint(0, 24 * 7)  # Last 7 days
        
        timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
        
        # Generate content based on bias probability
        bias_prob = random.random()
        if bias_prob < 0.7:  # 70% no bias
            target_sentiment = random.choice(['positive', 'neutral', 'negative'])
        else:  # 30% with bias
            target_sentiment = 'negative'  # Biased content tends to be negative
        
        text = self.generate_text_content(brand, target_sentiment)
        
        # Calculate scores
        sentiment = get_sentiment_score(text)
        bias = detect_bias(text)
        
        # Generate metadata
        metadata = {
            'url': fake.url(),
            'author': fake.user_name(),
            'likes': random.randint(-10, 100) if platform != 'Google News' else 0,
            'score': random.randint(-5, 50) if platform == 'Reddit' else None,
            'views': random.randint(100, 10000) if platform == 'YouTube' else None,
            'num_comments': random.randint(0, 50),
            'source_id': str(uuid.uuid4())
        }
        
        trust_score = compute_trust_score(text, sentiment, bias, metadata)
        
        record = {
            'source': 'mock_data',
            'platform': platform,
            'brand': brand,
            'text': text,
            'sentiment': sentiment,
            'bias': bias,
            'trust_score': trust_score,
            'timestamp': timestamp,
            'metadata': metadata
        }
        
        return record

    def generate_batch(self, count=100, brand=None, platform=None):
        """Generate a batch of mock records"""
        records = []
        for _ in range(count):
            record = self.generate_mock_record(brand=brand, platform=platform)
            records.append(record)
        
        return records

    def insert_mock_data(self, count=100, brand=None, platform=None):
        """Generate and insert mock data into database"""
        print(f"Generating {count} mock records...")
        
        records = self.generate_batch(count, brand, platform)
        
        inserted_count = 0
        alerts_generated = 0
        
        for record in records:
            try:
                record_id = db_manager.insert_score(record)
                if record_id:
                    inserted_count += 1
                    
                    # Generate alerts for low trust scores
                    if record['trust_score'] < 30:
                        alert_id = db_manager.insert_bias_alert(
                            record['brand'],
                            f"Low Trust Score: {record['trust_score']}",
                            record['trust_score'],
                            record['text'][:500],
                            "HIGH" if record['trust_score'] < 20 else "MEDIUM"
                        )
                        if alert_id:
                            alerts_generated += 1
                    
                    # Generate bias alerts
                    if record['bias'] != 'No Bias':
                        alert_id = db_manager.insert_bias_alert(
                            record['brand'],
                            record['bias'],
                            record['trust_score'],
                            record['text'][:500],
                            "HIGH"
                        )
                        if alert_id:
                            alerts_generated += 1
                            
            except Exception as e:
                print(f"Error inserting record: {e}")
                continue
        
        print(f"Successfully inserted {inserted_count} records")
        print(f"Generated {alerts_generated} alerts")
        
        return inserted_count, alerts_generated

    def generate_performance_summary(self, days=30):
        """Generate brand performance summaries for the last N days"""
        print(f"Generating performance summaries for last {days} days...")
        
        for brand in self.brands:
            for day_offset in range(days):
                date = datetime.utcnow().date() - timedelta(days=day_offset)
                
                # Generate day's performance data
                total_mentions = random.randint(10, 100)
                avg_trust_score = random.uniform(30, 85)
                positive_pct = random.uniform(0.2, 0.7)
                negative_pct = random.uniform(0.1, 0.4)
                bias_violations = random.randint(0, 10)
                
                performance_data = {
                    'avg_trust_score': avg_trust_score,
                    'total_mentions': total_mentions,
                    'positive_sentiment_pct': positive_pct,
                    'negative_sentiment_pct': negative_pct,
                    'bias_violations': bias_violations
                }
                
                try:
                    db_manager.update_brand_performance(brand, date, performance_data)
                except Exception as e:
                    print(f"Error updating performance for {brand} on {date}: {e}")
        
        print(f"Performance summaries generated for {len(self.brands)} brands")

    def export_to_json(self, count=100, filename="mock_data.json"):
        """Export mock data to JSON file"""
        records = self.generate_batch(count)
        
        # Convert datetime objects to strings for JSON serialization
        for record in records:
            if isinstance(record['timestamp'], datetime):
                record['timestamp'] = record['timestamp'].isoformat()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {count} mock records to {filename}")

def main():
    """Main function with CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate mock data for ZOBON system')
    parser.add_argument('--count', type=int, default=100, help='Number of records to generate')
    parser.add_argument('--brand', type=str, help='Specific brand to generate data for')
    parser.add_argument('--platform', type=str, help='Specific platform to generate data for')
    parser.add_argument('--export', type=str, help='Export to JSON file instead of database')
    parser.add_argument('--performance', action='store_true', help='Generate performance summaries')
    parser.add_argument('--days', type=int, default=30, help='Days of performance data to generate')
    
    args = parser.parse_args()
    
    generator = MockDataGenerator()
    
    try:
        if args.export:
            generator.export_to_json(args.count, args.export)
        else:
            inserted, alerts = generator.insert_mock_data(
                count=args.count,
                brand=args.brand,
                platform=args.platform
            )
            print(f"\nSummary:")
            print(f"- Inserted records: {inserted}")
            print(f"- Generated alerts: {alerts}")
        
        if args.performance:
            generator.generate_performance_summary(args.days)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()