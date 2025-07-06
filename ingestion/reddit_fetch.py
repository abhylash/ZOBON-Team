import praw
import os
import json
import datetime
from dotenv import load_dotenv
import sys
import logging

# Load environment variables
load_dotenv()

# Path setup to access sibling modules
sys.path.append('..')

from storage.s3_uploader import upload_raw_data
from kafka_producer import send_to_kafka

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedditDataFetcher:
    def __init__(self):
        # Initialize PRAW with environment variables
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_SECRET"),
            user_agent=os.getenv("USER_AGENT"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD")
        )

    def fetch_reddit_posts(self, query="Tata EV", limit=20):
        """Fetch Reddit posts and comments for EV brands"""
        results = []
        subreddits = ["india", "electricvehicles", "teslamotors", "EVs", "indianbikes"]

        try:
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    for submission in subreddit.search(query, limit=limit // len(subreddits)):
                        post_data = {
                            "source": "reddit",
                            "platform": "reddit_post",
                            "brand": self._extract_brand(query),
                            "text": f"{submission.title} {submission.selftext}",
                            "timestamp": str(datetime.datetime.utcfromtimestamp(submission.created_utc)),
                            "url": submission.url,
                            "score": submission.score,
                            "num_comments": submission.num_comments
                        }
                        results.append(post_data)

                        # Fetch top-level comments
                        submission.comments.replace_more(limit=0)
                        for comment in submission.comments.list()[:10]:
                            if len(comment.body) > 10:
                                comment_data = {
                                    "source": "reddit",
                                    "platform": "reddit_comment",
                                    "brand": self._extract_brand(query),
                                    "text": comment.body,
                                    "timestamp": str(datetime.datetime.utcfromtimestamp(comment.created_utc)),
                                    "score": comment.score,
                                    "parent_post": submission.title
                                }
                                results.append(comment_data)

                except Exception as e:
                    logger.error(f"Error fetching from subreddit {subreddit_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in Reddit data fetching: {e}")

        logger.info(f"Fetched {len(results)} Reddit items for query: {query}")
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
    fetcher = RedditDataFetcher()

    ev_brands = ["Tata EV", "Ola Electric", "Ather Energy", "Mahindra Electric"]

    for brand in ev_brands:
        try:
            posts = fetcher.fetch_reddit_posts(brand, limit=30)

            if posts:
                upload_raw_data(posts, platform="reddit", brand=brand)
                send_to_kafka("reddit_topic", posts)
                logger.info(f"Processed {len(posts)} posts for {brand}")

        except Exception as e:
            logger.error(f"Error processing {brand}: {e}")


if __name__ == '__main__':
    main()
