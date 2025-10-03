"""
Booru Service

Business logic layer for Booru operations. This service orchestrates
repository operations and implements domain-specific functionality.
"""

import logging
from typing import Dict, List, Any, Optional

from repositories.interfaces import IBooruRepository
from repositories.booru_repository import PostSearchCriteria, TagSearchCriteria
from repositories.user_repository import UserSettings

logger = logging.getLogger(__name__)


class BooruService:
    """
    Service layer for Booru operations.
    
    This service encapsulates business logic for searching posts, tags,
    and applying user preferences. It coordinates between repositories
    and implements domain-specific rules.
    
    Example:
        async with BooruRepository(base_url, api_key, user_id) as repo:
            service = BooruService(repo)
            posts = await service.search_posts_with_preferences(
                tags="cat girl",
                user_settings=user_settings,
                limit=20
            )
    """
    
    def __init__(self, booru_repository: IBooruRepository):
        """
        Initialize the Booru service.
        
        Args:
            booru_repository: Repository for Booru API operations
        """
        self.repository = booru_repository
    
    def _apply_user_preferences(self, tags: str, user_settings: UserSettings) -> str:
        """
        Apply user preferences (auto tags and toggle rules) to search tags.
        
        Args:
            tags: Original search tags
            user_settings: User settings containing preferences
            
        Returns:
            Modified tags with user preferences applied
        """
        # Apply auto tags
        if user_settings.auto_tags:
            auto_tags_str = " ".join(user_settings.auto_tags)
            tags = f"{tags} {auto_tags_str}" if tags else auto_tags_str
        
        # Apply enabled toggle rules
        enabled_toggles = [rule for rule, enabled in user_settings.toggle_rules.items() if enabled]
        if enabled_toggles:
            toggle_str = " ".join(enabled_toggles)
            tags = f"{tags} {toggle_str}" if tags else toggle_str
        
        return tags.strip()
    
    async def search_posts(self, tags: str = "", limit: int = 20, 
                          page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for posts with given tags.
        
        Args:
            tags: Search tags
            limit: Maximum number of posts to retrieve
            page: Page number for pagination
            
        Returns:
            List of post dictionaries
            
        Example:
            posts = await service.search_posts("cat girl rating:safe", limit=10)
            for post in posts:
                print(f"Post ID: {post['id']}")
        """
        criteria = PostSearchCriteria(tags=tags, limit=limit, page=page)
        result = await self.repository.get_posts(criteria)
        
        posts = result.get('post', [])
        if isinstance(posts, dict):
            posts = [posts]
        
        logger.info(f"Found {len(posts)} posts for tags: '{tags}'")
        return posts
    
    async def search_posts_with_preferences(self, tags: str, user_settings: UserSettings,
                                           limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for posts with user preferences applied.
        
        Args:
            tags: Base search tags
            user_settings: User settings to apply
            limit: Maximum number of posts to retrieve
            page: Page number for pagination
            
        Returns:
            List of post dictionaries
            
        Example:
            settings = UserSettings(auto_tags=["rating:safe"])
            posts = await service.search_posts_with_preferences(
                "cat girl", settings, limit=10
            )
        """
        modified_tags = self._apply_user_preferences(tags, user_settings)
        logger.info(f"Searching with preferences: '{tags}' -> '{modified_tags}'")
        return await self.search_posts(modified_tags, limit, page)
    
    async def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific post by ID.
        
        Args:
            post_id: The post ID to retrieve
            
        Returns:
            Post dictionary or None if not found
            
        Example:
            post = await service.get_post_by_id(12345)
            if post:
                print(f"Found post: {post['id']}")
        """
        return await self.repository.get_post_by_id(post_id)
    
    async def search_tags(self, pattern: Optional[str] = None, 
                         name: Optional[str] = None,
                         limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for tags by pattern or exact name.
        
        Args:
            pattern: Wildcard pattern for tag search
            name: Exact tag name to search for
            limit: Maximum number of tags to retrieve
            
        Returns:
            List of tag dictionaries
            
        Example:
            # Search by pattern
            tags = await service.search_tags(pattern="school*", limit=10)
            
            # Search by exact name
            tag = await service.search_tags(name="school_uniform")
        """
        criteria = TagSearchCriteria(
            pattern=pattern,
            name=name,
            limit=limit
        )
        
        result = await self.repository.get_tags(criteria)
        tags = result.get('tag', [])
        
        if isinstance(tags, dict):
            tags = [tags]
        
        logger.info(f"Found {len(tags)} tags")
        return tags
    
    async def search_tags_with_fallback(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for tags with intelligent fallback strategy.
        
        First tries exact name match, then falls back to pattern search if needed.
        
        Args:
            query: Search query
            limit: Maximum number of tags to retrieve
            
        Returns:
            List of tag dictionaries
            
        Example:
            tags = await service.search_tags_with_fallback("school", limit=10)
        """
        # Try exact match first
        tags = await self.search_tags(name=query, limit=limit)
        
        # If no exact matches and query is long enough, try pattern search
        if not tags and len(query) >= 3:
            logger.info(f"No exact matches, trying pattern search for: {query}")
            tags = await self.search_tags(pattern=f"%{query}%", limit=limit)
        
        return tags
    
    async def get_comments(self, post_id: int) -> List[Dict[str, Any]]:
        """
        Get comments for a specific post.
        
        Args:
            post_id: The post ID to get comments for
            
        Returns:
            List of comment dictionaries
            
        Example:
            comments = await service.get_comments(12345)
            for comment in comments:
                print(f"Comment: {comment['body']}")
        """
        result = await self.repository.get_comments(post_id)
        comments = result.get('comment', [])
        
        if isinstance(comments, dict):
            comments = [comments]
        
        return comments
    
    def extract_post_info(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize post information.
        
        Args:
            post: Raw post dictionary from API
            
        Returns:
            Normalized post information
            
        Example:
            info = service.extract_post_info(post)
            print(f"ID: {info['id']}, Size: {info['width']}x{info['height']}")
        """
        return {
            'id': post.get('id', 'Unknown'),
            'width': post.get('width', 'Unknown'),
            'height': post.get('height', 'Unknown'),
            'score': post.get('score', 'Unknown'),
            'rating': post.get('rating', 'Unknown'),
            'tags': post.get('tags', '').strip(),
            'file_url': post.get('file_url', ''),
            'preview_url': post.get('preview_url', ''),
            'sample_url': post.get('sample_url', ''),
            'created_at': post.get('created_at', ''),
            'source': post.get('source', '')
        }
    
    def get_media_type(self, file_url: str) -> str:
        """
        Determine media type from file URL.
        
        Args:
            file_url: URL of the media file
            
        Returns:
            Media type: 'video', 'gif', or 'image'
            
        Example:
            media_type = service.get_media_type("https://example.com/image.mp4")
            print(media_type)  # 'video'
        """
        if not file_url:
            return 'image'
        
        extension = file_url.lower().split('.')[-1] if '.' in file_url else ''
        
        if extension == 'mp4':
            return 'video'
        elif extension == 'gif':
            return 'gif'
        else:
            return 'image'
    
    def get_display_url(self, post: Dict[str, Any], use_sample: bool = True) -> str:
        """
        Get the best URL for displaying media.
        
        Args:
            post: Post dictionary
            use_sample: Whether to prefer sample URL for images
            
        Returns:
            URL for displaying the media
            
        Example:
            url = service.get_display_url(post, use_sample=True)
        """
        file_url = post.get('file_url', '')
        media_type = self.get_media_type(file_url)
        
        if media_type in ['video', 'gif']:
            return file_url
        else:
            if use_sample:
                return post.get('sample_url', file_url)
            return file_url
    
    def get_preview_url(self, post: Dict[str, Any]) -> str:
        """
        Get the preview/thumbnail URL for a post.
        
        Args:
            post: Post dictionary
            
        Returns:
            Preview URL
            
        Example:
            preview = service.get_preview_url(post)
        """
        return post.get('preview_url', post.get('file_url', ''))