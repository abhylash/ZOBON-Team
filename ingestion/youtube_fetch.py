
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

class YouTubeDataFetcher:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def fetch_youtube_comments(self, query="Ola Electric ad", max_videos=5, max_comments=20):
        """Fetch YouTube comments for EV brand campaigns"""
        results = []
        
        try:
            # Search for videos
            search_url = f"{self.base_url}/search"
            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "key": self.api_key,
                "maxResults": max_videos,
                "regionCode": "IN",
                "relevanceLanguage": "en"
            }
            
            search_response = requests.get(search_url, params=search_params)
            search_data = search_response.json()
            
            if "items" not in search_data:
                logger.error(f"No videos found for query: {query}")
                return results
            
            # Process each video
            for item in search_data.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_description = item["snippet"]["description"]
                
                # Add video metadata
                video_data = {
                    "source": "youtube",
                    "platform": "youtube_video",
                    "brand": self._extract_brand(query),
                    "text": f"{video_title} {video_description}",
                    "timestamp": item["snippet"]["publishedAt"],
                    "video_id": video_id,
                    "channel": item["snippet"]["channelTitle"]
                }
                results.append(video_data)
                
                # Fetch comments for this video
                comments_url = f"{self.base_url}/commentThreads"
                comments_params = {
                    "part": "snippet",
                    "videoId": video_id,
                    "key": self.api_key,
                    "maxResults": max_comments,
                    "order": "relevance"
                }
                
                try:
                    comments_response = requests.get(comments_url, params=comments_params)
                    comments_data = comments_response.json()
                    
                    for comment_item in comments_data.get("items", []):
                        comment_snippet = comment_item["snippet"]["topLevelComment"]["snippet"]
                        
                        comment_data = {
                            "source": "youtube",
                            "platform": "youtube_comment",
                            "brand": self._extract_brand(query),
                            "text": comment_snippet["textDisplay"],
                            "timestamp": comment_snippet["publishedAt"],
                            "likes": comment_snippet.get("likeCount", 0),
                            "video_id": video_id,
                            "video_title": video_title,
                            "author": comment_snippet["authorDisplayName"]
                        }
                        results.append(comment_data)
                        
                except Exception as e:
                    logger.warning(f"Could not fetch comments for video {video_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching YouTube data: {e}")
            
        logger.info(f"Fetched {len(results)} YouTube items for query: {query}")
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
    fetcher = YouTubeDataFetcher()
    
    # EV brand campaign queries
    campaign_queries = [
        "Tata Nexon EV ad",
        "Ola Electric scooter commercial", 
        "Ather 450X review",
        "Mahindra eKUV100 launch",
        "Indian EV comparison"
    ]
    
    for query in campaign_queries:
        try:
            comments = fetcher.fetch_youtube_comments(query, max_videos=3, max_comments=15)
            
            if comments:
                # Upload raw data to S3
                upload_raw_data(comments, platform="youtube", brand=query)
                
                # Send to Kafka for real-time processing
                send_to_kafka("youtube_topic", comments)
                
                logger.info(f"Processed {len(comments)} items for query: {query}")
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")

if __name__ == '__main__':
    main()