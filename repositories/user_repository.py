"""
User Repository Implementation

Concrete implementation of IUserRepository using file-based storage.
This implementation provides a clean abstraction over file I/O operations.
"""

import os
import pickle
import logging
from typing import Optional
from dataclasses import dataclass, field
from typing import Dict, List

from .interfaces import (
    IUserRepository,
    RepositoryException,
    RepositoryDataException
)

logger = logging.getLogger(__name__)


@dataclass
class UserSettings:
    """User-specific settings for the bot."""
    auto_tags: List[str] = field(default_factory=list)  # Tags always applied to searches
    toggle_rules: Dict[str, bool] = field(default_factory=dict)  # Custom toggle rules


class UserRepository(IUserRepository):
    """
    Concrete implementation of IUserRepository using file-based storage.
    
    This repository manages user settings persistence using pickle files.
    Each user's settings are stored in a separate file for isolation and
    easy management.
    
    Example:
        repo = UserRepository(data_dir="user_data")
        settings = repo.get_user_settings(user_id=12345)
        settings.auto_tags.append("rating:safe")
        repo.save_user_settings(user_id=12345, settings=settings)
    """
    
    def __init__(self, data_dir: str = "user_data"):
        """
        Initialize the user repository.
        
        Args:
            data_dir: Directory to store user data files
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            logger.debug(f"Data directory ensured: {self.data_dir}")
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise RepositoryException(f"Failed to create data directory: {e}")
    
    def _get_user_file_path(self, user_id: int) -> str:
        """
        Get the file path for a user's settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            Full path to the user's settings file
        """
        return os.path.join(self.data_dir, f"user_{user_id}.pkl")
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """
        Retrieve user settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            UserSettings object containing user preferences
            
        Example:
            settings = repo.get_user_settings(12345)
            print(f"Auto tags: {settings.auto_tags}")
        """
        file_path = self._get_user_file_path(user_id)
        
        if not os.path.exists(file_path):
            logger.debug(f"No settings found for user {user_id}, returning defaults")
            return UserSettings()
        
        try:
            with open(file_path, 'rb') as f:
                settings = pickle.load(f)
                logger.debug(f"Loaded settings for user {user_id}")
                return settings
        except Exception as e:
            logger.warning(f"Failed to load settings for user {user_id}: {e}")
            logger.warning("Returning default settings")
            return UserSettings()
    
    def save_user_settings(self, user_id: int, settings: UserSettings) -> None:
        """
        Save user settings.
        
        Args:
            user_id: The unique identifier of the user
            settings: UserSettings object to save
            
        Raises:
            RepositoryDataException: If save operation fails
            
        Example:
            settings = UserSettings(auto_tags=["rating:safe"])
            repo.save_user_settings(12345, settings)
        """
        file_path = self._get_user_file_path(user_id)
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(settings, f)
                logger.debug(f"Saved settings for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save settings for user {user_id}: {e}")
            raise RepositoryDataException(f"Failed to save user settings: {e}")
    
    def delete_user_settings(self, user_id: int) -> bool:
        """
        Delete user settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if deleted, False if user settings didn't exist
            
        Example:
            if repo.delete_user_settings(12345):
                print("Settings deleted successfully")
        """
        file_path = self._get_user_file_path(user_id)
        
        if not os.path.exists(file_path):
            logger.debug(f"No settings to delete for user {user_id}")
            return False
        
        try:
            os.remove(file_path)
            logger.info(f"Deleted settings for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete settings for user {user_id}: {e}")
            raise RepositoryDataException(f"Failed to delete user settings: {e}")
    
    def user_exists(self, user_id: int) -> bool:
        """
        Check if user settings exist.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if user settings exist, False otherwise
            
        Example:
            if repo.user_exists(12345):
                print("User has saved settings")
        """
        file_path = self._get_user_file_path(user_id)
        return os.path.exists(file_path)
    
    def get_all_user_ids(self) -> List[int]:
        """
        Get all user IDs that have settings stored.
        
        Returns:
            List of user IDs
            
        Example:
            user_ids = repo.get_all_user_ids()
            print(f"Total users: {len(user_ids)}")
        """
        try:
            user_ids = []
            for filename in os.listdir(self.data_dir):
                if filename.startswith("user_") and filename.endswith(".pkl"):
                    try:
                        user_id = int(filename[5:-4])  # Extract ID from "user_123.pkl"
                        user_ids.append(user_id)
                    except ValueError:
                        logger.warning(f"Invalid user file name: {filename}")
            return user_ids
        except Exception as e:
            logger.error(f"Failed to list user IDs: {e}")
            raise RepositoryException(f"Failed to list user IDs: {e}")
    
    def bulk_update_settings(self, updates: Dict[int, UserSettings]) -> int:
        """
        Bulk update multiple user settings.
        
        Args:
            updates: Dictionary mapping user_id to UserSettings
            
        Returns:
            Number of successfully updated users
            
        Example:
            updates = {
                12345: UserSettings(auto_tags=["rating:safe"]),
                67890: UserSettings(auto_tags=["rating:safe"])
            }
            count = repo.bulk_update_settings(updates)
            print(f"Updated {count} users")
        """
        success_count = 0
        for user_id, settings in updates.items():
            try:
                self.save_user_settings(user_id, settings)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to update user {user_id}: {e}")
        
        logger.info(f"Bulk update completed: {success_count}/{len(updates)} successful")
        return success_count