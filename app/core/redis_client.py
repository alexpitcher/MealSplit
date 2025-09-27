import redis
from typing import Optional
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_client = None
        self.connect()

    def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        if not self.redis_client:
            return None
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a value in Redis."""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def publish(self, channel: str, message: str) -> bool:
        """Publish a message to a Redis channel."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.publish(channel, message)
            return True
        except Exception as e:
            logger.error(f"Redis PUBLISH error: {e}")
            return False

    def subscribe(self, channels: list):
        """Subscribe to Redis channels."""
        if not self.redis_client:
            return None
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error: {e}")
            return None


redis_client = RedisClient()