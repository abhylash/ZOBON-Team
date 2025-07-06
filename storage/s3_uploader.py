import boto3
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class S3DataUploader:
    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "ap-south-1")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            self._verify_bucket()
        except Exception as e:
            logger.error(f"Error initializing S3 client: {e}")
            self.s3_client = None
    
    def _verify_bucket(self):
        """Verify that the S3 bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' verified successfully")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"S3 bucket '{self.bucket_name}' does not exist")
                self._create_bucket()
            else:
                logger.error(f"Error accessing S3 bucket: {e}")
    
    def _create_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            if self.aws_region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                )
            logger.info(f"Created S3 bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error creating S3 bucket: {e}")
    
    def upload_raw_data(self, data, platform="unknown", brand="unknown"):
        """Upload raw data to S3 with organized folder structure"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            # Create timestamp-based folder structure
            now = datetime.utcnow()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            day = now.strftime("%d")
            hour = now.strftime("%H")
            
            # Create S3 key with hierarchical structure
            s3_key = f"raw-data/{platform}/{brand}/{year}/{month}/{day}/{hour}/data_{now.strftime('%Y%m%d_%H%M%S')}.json"
            
            # Prepare data for upload
            upload_data = {
                "metadata": {
                    "platform": platform,
                    "brand": brand,
                    "upload_timestamp": now.isoformat(),
                    "record_count": len(data) if isinstance(data, list) else 1
                },
                "data": data
            }
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(upload_data, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'platform': platform,
                    'brand': brand,
                    'upload_time': now.isoformat()
                }
            )
            
            logger.info(f"Successfully uploaded data to S3: s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading data to S3: {e}")
            return False
    
    def upload_processed_data(self, data, data_type="processed"):
        """Upload processed data to S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            now = datetime.utcnow()
            s3_key = f"processed-data/{data_type}/{now.strftime('%Y/%m/%d')}/processed_{now.strftime('%Y%m%d_%H%M%S')}.json"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(data, indent=2, default=str),
                ContentType='application/json'
            )
            
            logger.info(f"Successfully uploaded processed data to S3: s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading processed data to S3: {e}")
            return False
    
    def list_files(self, prefix="", max_keys=100):
        """List files in S3 bucket with given prefix"""
        if not self.s3_client:
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 files: {e}")
            return []
    
    def download_file(self, s3_key, local_path):
        """Download file from S3 to local path"""
        if not self.s3_client:
            return False
        
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded {s3_key} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False

# Global instance for backward compatibility
_s3_uploader = None

def get_s3_uploader():
    """Get or create S3 uploader instance"""
    global _s3_uploader
    if _s3_uploader is None:
        _s3_uploader = S3DataUploader()
    return _s3_uploader

# Function interface for backward compatibility
def upload_raw_data(data, platform="unknown", brand="unknown"):
    """
    Upload raw data to S3 with organized folder structure
    
    Args:
        data: The data to upload (dict, list, or any JSON-serializable object)
        platform: The platform name (e.g., 'reddit', 'youtube', 'gnews')
        brand: The brand name
    
    Returns:
        bool: True if upload successful, False otherwise
    """
    uploader = get_s3_uploader()
    return uploader.upload_raw_data(data, platform, brand)

def upload_processed_data(data, data_type="processed"):
    """
    Upload processed data to S3
    
    Args:
        data: The processed data to upload
        data_type: Type of processed data
    
    Returns:
        bool: True if upload successful, False otherwise
    """
    uploader = get_s3_uploader()
    return uploader.upload_processed_data(data, data_type)

def list_s3_files(prefix="", max_keys=100):
    """
    List files in S3 bucket with given prefix
    
    Args:
        prefix: S3 key prefix to filter files
        max_keys: Maximum number of files to return
    
    Returns:
        list: List of file information dictionaries
    """
    uploader = get_s3_uploader()
    return uploader.list_files(prefix, max_keys)

def download_s3_file(s3_key, local_path):
    """
    Download file from S3 to local path
    
    Args:
        s3_key: S3 key of the file to download
        local_path: Local path where file should be saved
    
    Returns:
        bool: True if download successful, False otherwise
    """
    uploader = get_s3_uploader()
    return uploader.download_file(s3_key, local_path)

# Example usage functions
def upload_reddit_data(reddit_data, brand="unknown"):
    """Upload Reddit data with platform-specific handling"""
    return upload_raw_data(reddit_data, platform="reddit", brand=brand)

def upload_youtube_data(youtube_data, brand="unknown"):
    """Upload YouTube data with platform-specific handling"""
    return upload_raw_data(youtube_data, platform="youtube", brand=brand)

def upload_gnews_data(gnews_data, brand="unknown"):
    """Upload Google News data with platform-specific handling"""
    return upload_raw_data(gnews_data, platform="gnews", brand=brand)

# For direct class usage
__all__ = [
    'S3DataUploader',
    'upload_raw_data',
    'upload_processed_data', 
    'list_s3_files',
    'download_s3_file',
    'upload_reddit_data',
    'upload_youtube_data', 
    'upload_gnews_data'
]