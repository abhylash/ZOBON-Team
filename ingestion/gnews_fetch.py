
import os
import json
import datetime
import requests
from dotenv import load_dotenv
import sys
sys.path.append('..')
from storage.s3_uploader import upload_raw_data
from kafka_producer import send_to_kafka
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class GNewsDataFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        self.base_url = "https://gnews.io/api/v4"
    
    def fetch_news(self, query="Ather EV", max_results=10):
        """Fetch news articles about EV brands"""
        results = []
        
        try:
            search_url = f"{self.base_url}/search"
            params = {
                "q": query,
                "lang": "en",
                "country": "in",
                "max": max_results,
                "apikey": self.api_key,
                "sortby": "publishedAt"
            }
            
            response = requests.get(search_url, params=params)
            data = response.json()
            
            if response.status_code != 200:
                logger.error(f"API Error: {data.get('message', 'Unknown error')}")
                return results
            
            for article in data.get("articles", []):
                article_data = {
                    "source": "news",
                    "platform": "gnews",
                    "brand": self._extract_brand(query),
                    "text": f"{article.get('title', '')} {article.get('description', '')}",
                    "timestamp": article.get("publishedAt", datetime.datetime.utcnow().isoformat()),
                    "url": article.get("url", ""),
                    "source_name": article.get("source", {}).get("name", ""),
                    "image": article.get("image", "")
                }
                results.append(article_data)
                
        except Exception as e:
            logger.error(f"Error fetching news data: {e}")
            
        logger.info(f"Fetched {len(results)} news articles for query: {query}")
        return results
    
    def _extract_brand(self, query):
        """Extract brand name from query"""
        brands = {
            "tata": "Tata Motors",
            "ola": "Ola Electric", 
            "ather": "Ather Energy",
            "mahindra": "Mahindra Electric",
            "tesla": "Tesla",
            "bajaj": "Bajaj Auto"
        }
        
        query_lower = query.lower()
        for brand_key, brand_name in brands.items():
            if brand_key in query_lower:
                return brand_name
        return query.split()[0] if query else "Unknown"

def main():
    """Main execution function"""
    fetcher = GNewsDataFetcher()
    
    # EV brand news queries
    news_queries = [
        "Tata EV sales India",
        "Ola Electric IPO news",
        "Ather Energy funding",
        "Mahindra electric vehicle launch",
        "Indian EV market growth"
    ]
    
    for query in news_queries:
        try:
            news_data = fetcher.fetch_news(query, max_results=15)
            
            if news_data:
                # Upload raw data to S3
                upload_raw_data(news_data, platform="news", brand=query)
                
                # Send to Kafka for real-time processing
                send_to_kafka("gnews_topic", news_data)
                
                logger.info(f"Processed {len(news_data)} articles for query: {query}")
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")

if __name__ == '__main__':
    main()