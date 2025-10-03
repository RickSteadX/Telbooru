"""
Booru Repository Implementation

Concrete implementation of IBooruRepository using the existing BooruAPIWrapper.
This implementation provides a clean abstraction over the HTTP API calls.
"""

import logging
from typing import Dict, Any, Optional
import aiohttp

from .interfaces import (
    IBooruRepository,
    PostSearchCriteria,
    TagSearchCriteria,
    RepositoryException,
    RepositoryConnectionException,
    RepositoryDataException
)

logger = logging.getLogger(__name__)


class BooruRepository(IBooruRepository):
    """
    Concrete implementation of IBooruRepository.
    
    This repository handles all interactions with the Booru API, providing
    a clean abstraction layer that isolates the rest of the application
    from HTTP implementation details.
    
    Example:
        async with BooruRepository(base_url, api_key, user_id) as repo:
            criteria = PostSearchCriteria(tags="cat girl", limit=10)
            posts = await repo.get_posts(criteria)
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, 
                 user_id: Optional[str] = None):
        """
        Initialize the Booru repository.
        
        Args:
            base_url: Base URL of the Booru API
            api_key: Optional API key for authentication
            user_id: Optional user ID for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _build_auth_params(self) -> Dict[str, str]:
        """Build authentication parameters if available."""
        params = {}
        if self.api_key and self.user_id:
            params['api_key'] = self.api_key
            params['user_id'] = self.user_id
        return params
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an API request with proper error handling.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            JSON response data
            
        Raises:
            RepositoryConnectionException: If connection fails
            RepositoryDataException: If data operation fails
        """
        if not self.session:
            raise RepositoryException("Repository not initialized. Use async context manager.")
        
        try:
            # Add authentication parameters
            auth_params = self._build_auth_params()
            params.update(auth_params)
            
            # Ensure JSON response
            if 'json' not in params:
                params['json'] = '1'
            
            # Build URL with query parameters
            from urllib.parse import quote_plus
            query_parts = []
            for key, value in params.items():
                if value is not None:
                    encoded_key = quote_plus(str(key))
                    encoded_value = quote_plus(str(value))
                    query_parts.append(f"{encoded_key}={encoded_value}")
            
            url = f"{self.base_url}{endpoint}"
            if query_parts:
                url = f"{url}?{'&'.join(query_parts)}"
            
            logger.debug(f"Making request to: {url}")
            
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise RepositoryConnectionException(f"Failed to connect to API: {e}")
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP error {e.status}: {e.message}")
            raise RepositoryDataException(f"API returned error {e.status}: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise RepositoryException(f"Unexpected error during API request: {e}")
    
    async def get_posts(self, criteria: PostSearchCriteria) -> Dict[str, Any]:
        """
        Retrieve posts based on search criteria.
        
        Args:
            criteria: PostSearchCriteria object containing search parameters
            
        Returns:
            Dictionary containing post data with 'post' key
            
        Example:
            criteria = PostSearchCriteria(tags="cat rating:safe", limit=20)
            result = await repo.get_posts(criteria)
            posts = result.get('post', [])
        """
        logger.info(f"Fetching posts with criteria: {criteria}")
        
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'limit': min(criteria.limit, 100),
            'pid': criteria.page,
            'json': '1'
        }
        
        if criteria.tags:
            params['tags'] = criteria.tags
        if criteria.change_id is not None:
            params['cid'] = criteria.change_id
        if criteria.post_id is not None:
            params['id'] = criteria.post_id
        
        try:
            result = await self._make_request('/index.php', params)
            
            # Handle different response formats
            if result is None:
                logger.warning("Received null response from API")
                return {'post': []}
            
            if isinstance(result, list):
                return {'post': result}
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected response format: {type(result)}")
                return {'post': []}
            
            # Normalize response format
            if 'post' not in result and 'posts' in result:
                result['post'] = result['posts']
            
            return result
            
        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to get posts: {e}")
            raise RepositoryDataException(f"Failed to retrieve posts: {e}")
    
    async def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single post by ID.
        
        Args:
            post_id: The unique identifier of the post
            
        Returns:
            Post data dictionary or None if not found
            
        Example:
            post = await repo.get_post_by_id(12345)
            if post:
                print(f"Found post: {post['id']}")
        """
        criteria = PostSearchCriteria(post_id=post_id, limit=1)
        result = await self.get_posts(criteria)
        
        posts = result.get('post', [])
        if posts:
            return posts[0] if isinstance(posts, list) else posts
        return None
    
    async def get_tags(self, criteria: TagSearchCriteria) -> Dict[str, Any]:
        """
        Retrieve tags based on search criteria.
        
        Args:
            criteria: TagSearchCriteria object containing search parameters
            
        Returns:
            Dictionary containing tag data with 'tag' key
            
        Example:
            criteria = TagSearchCriteria(pattern="school*", limit=10)
            result = await repo.get_tags(criteria)
            tags = result.get('tag', [])
        """
        logger.info(f"Fetching tags with criteria: {criteria}")
        
        params = {
            'page': 'dapi',
            's': 'tag',
            'q': 'index',
            'limit': criteria.limit,
            'order': criteria.order,
            'orderby': criteria.orderby,
            'json': '1'
        }
        
        if criteria.after_id is not None:
            params['after_id'] = criteria.after_id
        if criteria.name:
            params['name'] = criteria.name
        if criteria.names:
            params['names'] = criteria.names
        if criteria.pattern:
            params['tags'] = criteria.pattern
        
        try:
            result = await self._make_request('/index.php', params)
            
            # Handle different response formats
            if result is None:
                logger.warning("Received null response from tags API")
                return {'tag': []}
            
            if isinstance(result, list):
                return {'tag': result}
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected tags response format: {type(result)}")
                return {'tag': []}
            
            # Normalize response format
            if 'tag' not in result and 'tags' in result:
                result['tag'] = result['tags']
            
            return result
            
        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to get tags: {e}")
            raise RepositoryDataException(f"Failed to retrieve tags: {e}")
    
    async def get_comments(self, post_id: int) -> Dict[str, Any]:
        """
        Retrieve comments for a specific post.
        
        Args:
            post_id: The post ID to get comments for
            
        Returns:
            Dictionary containing comment data
            
        Example:
            comments = await repo.get_comments(12345)
            for comment in comments.get('comment', []):
                print(comment['body'])
        """
        logger.info(f"Fetching comments for post: {post_id}")
        
        params = {
            'page': 'dapi',
            's': 'comment',
            'q': 'index',
            'post_id': post_id,
            'json': '1'
        }
        
        try:
            return await self._make_request('/index.php', params)
        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to get comments: {e}")
            raise RepositoryDataException(f"Failed to retrieve comments: {e}")
    
    async def get_deleted_images(self, last_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve deleted images.
        
        Args:
            last_id: Return everything above this ID
            
        Returns:
            Dictionary containing deleted image data
            
        Example:
            deleted = await repo.get_deleted_images(last_id=1000)
            for image in deleted.get('post', []):
                print(f"Deleted: {image['id']}")
        """
        logger.info(f"Fetching deleted images (last_id: {last_id})")
        
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'deleted': 'show',
            'json': '1'
        }
        
        if last_id is not None:
            params['last_id'] = str(last_id)
        
        try:
            return await self._make_request('/index.php', params)
        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to get deleted images: {e}")
            raise RepositoryDataException(f"Failed to retrieve deleted images: {e}")