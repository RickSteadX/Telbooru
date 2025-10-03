"""
Repository Interfaces

Abstract base classes defining the contract for data access operations.
These interfaces ensure loose coupling and enable easy testing and swapping
of implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PostSearchCriteria:
    """Criteria for searching posts."""
    tags: str = ""
    limit: int = 20
    page: int = 0
    post_id: Optional[int] = None
    change_id: Optional[int] = None


@dataclass
class TagSearchCriteria:
    """Criteria for searching tags."""
    limit: int = 100
    after_id: Optional[int] = None
    name: Optional[str] = None
    names: Optional[str] = None
    pattern: Optional[str] = None
    order: str = 'ASC'
    orderby: str = 'name'


class IBooruRepository(ABC):
    """
    Abstract repository interface for Booru API operations.
    
    This interface defines the contract for accessing booru-style image board data.
    Implementations can use different data sources (REST API, GraphQL, local cache, etc.)
    while maintaining the same interface.
    """
    
    @abstractmethod
    async def get_posts(self, criteria: PostSearchCriteria) -> Dict[str, Any]:
        """
        Retrieve posts based on search criteria.
        
        Args:
            criteria: PostSearchCriteria object containing search parameters
            
        Returns:
            Dictionary containing post data with 'post' key
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    async def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single post by ID.
        
        Args:
            post_id: The unique identifier of the post
            
        Returns:
            Post data dictionary or None if not found
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    async def get_tags(self, criteria: TagSearchCriteria) -> Dict[str, Any]:
        """
        Retrieve tags based on search criteria.
        
        Args:
            criteria: TagSearchCriteria object containing search parameters
            
        Returns:
            Dictionary containing tag data with 'tag' key
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    async def get_comments(self, post_id: int) -> Dict[str, Any]:
        """
        Retrieve comments for a specific post.
        
        Args:
            post_id: The post ID to get comments for
            
        Returns:
            Dictionary containing comment data
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    async def get_deleted_images(self, last_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve deleted images.
        
        Args:
            last_id: Return everything above this ID
            
        Returns:
            Dictionary containing deleted image data
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass


class IUserRepository(ABC):
    """
    Abstract repository interface for user data operations.
    
    This interface defines the contract for managing user settings and preferences.
    Implementations can use different storage mechanisms (files, databases, cache, etc.)
    """
    
    @abstractmethod
    def get_user_settings(self, user_id: int) -> 'UserSettings':
        """
        Retrieve user settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            UserSettings object containing user preferences
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    def save_user_settings(self, user_id: int, settings: 'UserSettings') -> None:
        """
        Save user settings.
        
        Args:
            user_id: The unique identifier of the user
            settings: UserSettings object to save
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    def delete_user_settings(self, user_id: int) -> bool:
        """
        Delete user settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if deleted, False if user settings didn't exist
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    def user_exists(self, user_id: int) -> bool:
        """
        Check if user settings exist.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if user settings exist, False otherwise
        """
        pass


class ISearchRepository(ABC):
    """
    Abstract repository interface for search state management.
    
    This interface defines the contract for managing search sessions and pagination state.
    Implementations can use different storage mechanisms (memory, cache, database, etc.)
    """
    
    @abstractmethod
    def save_search_state(self, user_id: int, state: 'SearchState') -> None:
        """
        Save search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            state: SearchState object to save
            
        Raises:
            RepositoryException: If the operation fails
        """
        pass
    
    @abstractmethod
    def get_search_state(self, user_id: int) -> Optional['SearchState']:
        """
        Retrieve search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            SearchState object or None if no active search
        """
        pass
    
    @abstractmethod
    def delete_search_state(self, user_id: int) -> bool:
        """
        Delete search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if deleted, False if no state existed
        """
        pass
    
    @abstractmethod
    def clear_all_states(self) -> int:
        """
        Clear all search states (useful for cleanup).
        
        Returns:
            Number of states cleared
        """
        pass


class RepositoryException(Exception):
    """Base exception for repository operations."""
    pass


class RepositoryConnectionException(RepositoryException):
    """Exception raised when connection to data source fails."""
    pass


class RepositoryDataException(RepositoryException):
    """Exception raised when data operation fails."""
    pass