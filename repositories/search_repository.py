"""
Search Repository Implementation

Concrete implementation of ISearchRepository using in-memory storage.
This implementation provides fast access to search state data.
"""

import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from typing import List, Any

from .interfaces import (
    ISearchRepository,
    RepositoryException
)

logger = logging.getLogger(__name__)


@dataclass
class SearchState:
    """Current search state for pagination."""
    query: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    current_page: int = 0
    total_pages: int = 0
    posts_per_page: int = 5
    last_menu_message_id: Optional[int] = None  # Track the last menu message to delete it


class SearchRepository(ISearchRepository):
    """
    Concrete implementation of ISearchRepository using in-memory storage.
    
    This repository manages search state in memory for fast access.
    Search states are temporary and don't need persistence across restarts.
    
    Example:
        repo = SearchRepository()
        state = SearchState(query="cat girl", results=posts)
        repo.save_search_state(user_id=12345, state=state)
        
        # Later...
        state = repo.get_search_state(user_id=12345)
        if state:
            print(f"Current page: {state.current_page}")
    """
    
    def __init__(self):
        """Initialize the search repository with empty state storage."""
        self._states: Dict[int, SearchState] = {}
        logger.debug("SearchRepository initialized")
    
    def save_search_state(self, user_id: int, state: SearchState) -> None:
        """
        Save search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            state: SearchState object to save
            
        Example:
            state = SearchState(
                query="cat rating:safe",
                results=posts,
                current_page=0,
                total_pages=5
            )
            repo.save_search_state(12345, state)
        """
        self._states[user_id] = state
        logger.debug(f"Saved search state for user {user_id}: {state.query}")
    
    def get_search_state(self, user_id: int) -> Optional[SearchState]:
        """
        Retrieve search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            SearchState object or None if no active search
            
        Example:
            state = repo.get_search_state(12345)
            if state:
                print(f"Query: {state.query}")
                print(f"Page: {state.current_page + 1}/{state.total_pages}")
        """
        state = self._states.get(user_id)
        if state:
            logger.debug(f"Retrieved search state for user {user_id}")
        else:
            logger.debug(f"No search state found for user {user_id}")
        return state
    
    def delete_search_state(self, user_id: int) -> bool:
        """
        Delete search state for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if deleted, False if no state existed
            
        Example:
            if repo.delete_search_state(12345):
                print("Search state cleared")
        """
        if user_id in self._states:
            del self._states[user_id]
            logger.debug(f"Deleted search state for user {user_id}")
            return True
        logger.debug(f"No search state to delete for user {user_id}")
        return False
    
    def clear_all_states(self) -> int:
        """
        Clear all search states (useful for cleanup).
        
        Returns:
            Number of states cleared
            
        Example:
            count = repo.clear_all_states()
            print(f"Cleared {count} search states")
        """
        count = len(self._states)
        self._states.clear()
        logger.info(f"Cleared all search states: {count} states removed")
        return count
    
    def get_active_user_count(self) -> int:
        """
        Get the number of users with active search states.
        
        Returns:
            Number of active users
            
        Example:
            active = repo.get_active_user_count()
            print(f"{active} users have active searches")
        """
        return len(self._states)
    
    def get_all_user_ids(self) -> List[int]:
        """
        Get all user IDs with active search states.
        
        Returns:
            List of user IDs
            
        Example:
            user_ids = repo.get_all_user_ids()
            for user_id in user_ids:
                state = repo.get_search_state(user_id)
                print(f"User {user_id}: {state.query}")
        """
        return list(self._states.keys())
    
    def update_page(self, user_id: int, page: int) -> bool:
        """
        Update the current page for a user's search state.
        
        Args:
            user_id: The unique identifier of the user
            page: The new page number
            
        Returns:
            True if updated, False if no state exists
            
        Example:
            if repo.update_page(12345, page=2):
                print("Page updated successfully")
        """
        state = self._states.get(user_id)
        if state:
            state.current_page = page
            logger.debug(f"Updated page for user {user_id} to {page}")
            return True
        logger.debug(f"Cannot update page: no state for user {user_id}")
        return False
    
    def update_menu_message_id(self, user_id: int, message_id: int) -> bool:
        """
        Update the last menu message ID for a user's search state.
        
        Args:
            user_id: The unique identifier of the user
            message_id: The new message ID
            
        Returns:
            True if updated, False if no state exists
            
        Example:
            if repo.update_menu_message_id(12345, message_id=98765):
                print("Menu message ID updated")
        """
        state = self._states.get(user_id)
        if state:
            state.last_menu_message_id = message_id
            logger.debug(f"Updated menu message ID for user {user_id} to {message_id}")
            return True
        logger.debug(f"Cannot update menu message ID: no state for user {user_id}")
        return False