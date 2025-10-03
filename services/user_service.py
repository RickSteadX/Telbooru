"""
User Service

Business logic layer for user management operations. This service orchestrates
user repository operations and implements user-related business rules.
"""

import logging
from typing import List, Dict

from repositories.interfaces import IUserRepository
from repositories.user_repository import UserSettings

logger = logging.getLogger(__name__)


class UserService:
    """
    Service layer for user management operations.
    
    This service encapsulates business logic for managing user settings,
    preferences, and related operations.
    
    Example:
        user_repo = UserRepository()
        service = UserService(user_repo)
        
        # Add auto tag
        service.add_auto_tag(user_id=12345, tag="rating:safe")
        
        # Toggle rule
        service.toggle_rule(user_id=12345, rule="score:>100")
    """
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize the user service.
        
        Args:
            user_repository: Repository for user data operations
        """
        self.repository = user_repository
    
    def get_settings(self, user_id: int) -> UserSettings:
        """
        Get user settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            UserSettings object
            
        Example:
            settings = service.get_settings(12345)
            print(f"Auto tags: {settings.auto_tags}")
        """
        return self.repository.get_user_settings(user_id)
    
    def save_settings(self, user_id: int, settings: UserSettings) -> None:
        """
        Save user settings.
        
        Args:
            user_id: The unique identifier of the user
            settings: UserSettings object to save
            
        Example:
            settings = UserSettings(auto_tags=["rating:safe"])
            service.save_settings(12345, settings)
        """
        self.repository.save_user_settings(user_id, settings)
        logger.info(f"Saved settings for user {user_id}")
    
    def add_auto_tag(self, user_id: int, tag: str) -> bool:
        """
        Add an auto tag for a user.
        
        Args:
            user_id: The unique identifier of the user
            tag: Tag to add
            
        Returns:
            True if added, False if tag already exists
            
        Example:
            if service.add_auto_tag(12345, "rating:safe"):
                print("Auto tag added successfully")
        """
        settings = self.get_settings(user_id)
        
        if tag in settings.auto_tags:
            logger.debug(f"Tag '{tag}' already exists for user {user_id}")
            return False
        
        settings.auto_tags.append(tag)
        self.save_settings(user_id, settings)
        logger.info(f"Added auto tag '{tag}' for user {user_id}")
        return True
    
    def remove_auto_tag(self, user_id: int, tag: str) -> bool:
        """
        Remove an auto tag for a user.
        
        Args:
            user_id: The unique identifier of the user
            tag: Tag to remove
            
        Returns:
            True if removed, False if tag didn't exist
            
        Example:
            if service.remove_auto_tag(12345, "rating:safe"):
                print("Auto tag removed successfully")
        """
        settings = self.get_settings(user_id)
        
        if tag not in settings.auto_tags:
            logger.debug(f"Tag '{tag}' not found for user {user_id}")
            return False
        
        settings.auto_tags.remove(tag)
        self.save_settings(user_id, settings)
        logger.info(f"Removed auto tag '{tag}' for user {user_id}")
        return True
    
    def remove_auto_tag_by_index(self, user_id: int, index: int) -> bool:
        """
        Remove an auto tag by index.
        
        Args:
            user_id: The unique identifier of the user
            index: Index of the tag to remove
            
        Returns:
            True if removed, False if index is invalid
            
        Example:
            if service.remove_auto_tag_by_index(12345, 0):
                print("First auto tag removed")
        """
        settings = self.get_settings(user_id)
        
        if index < 0 or index >= len(settings.auto_tags):
            logger.debug(f"Invalid index {index} for user {user_id}")
            return False
        
        removed_tag = settings.auto_tags.pop(index)
        self.save_settings(user_id, settings)
        logger.info(f"Removed auto tag '{removed_tag}' at index {index} for user {user_id}")
        return True
    
    def get_auto_tags(self, user_id: int) -> List[str]:
        """
        Get all auto tags for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            List of auto tags
            
        Example:
            tags = service.get_auto_tags(12345)
            print(f"Auto tags: {', '.join(tags)}")
        """
        settings = self.get_settings(user_id)
        return settings.auto_tags.copy()
    
    def clear_auto_tags(self, user_id: int) -> int:
        """
        Clear all auto tags for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            Number of tags cleared
            
        Example:
            count = service.clear_auto_tags(12345)
            print(f"Cleared {count} auto tags")
        """
        settings = self.get_settings(user_id)
        count = len(settings.auto_tags)
        settings.auto_tags.clear()
        self.save_settings(user_id, settings)
        logger.info(f"Cleared {count} auto tags for user {user_id}")
        return count
    
    def toggle_rule(self, user_id: int, rule: str) -> bool:
        """
        Toggle a rule on/off for a user.
        
        Args:
            user_id: The unique identifier of the user
            rule: Rule to toggle
            
        Returns:
            New state of the rule (True if enabled, False if disabled)
            
        Example:
            enabled = service.toggle_rule(12345, "rating:safe")
            print(f"Rule is now: {'enabled' if enabled else 'disabled'}")
        """
        settings = self.get_settings(user_id)
        current_state = settings.toggle_rules.get(rule, False)
        new_state = not current_state
        settings.toggle_rules[rule] = new_state
        self.save_settings(user_id, settings)
        logger.info(f"Toggled rule '{rule}' to {new_state} for user {user_id}")
        return new_state
    
    def set_rule(self, user_id: int, rule: str, enabled: bool) -> None:
        """
        Set a rule to a specific state.
        
        Args:
            user_id: The unique identifier of the user
            rule: Rule to set
            enabled: Whether the rule should be enabled
            
        Example:
            service.set_rule(12345, "rating:safe", True)
        """
        settings = self.get_settings(user_id)
        settings.toggle_rules[rule] = enabled
        self.save_settings(user_id, settings)
        logger.info(f"Set rule '{rule}' to {enabled} for user {user_id}")
    
    def get_enabled_rules(self, user_id: int) -> List[str]:
        """
        Get all enabled rules for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            List of enabled rules
            
        Example:
            rules = service.get_enabled_rules(12345)
            print(f"Enabled rules: {', '.join(rules)}")
        """
        settings = self.get_settings(user_id)
        return [rule for rule, enabled in settings.toggle_rules.items() if enabled]
    
    def get_all_rules(self, user_id: int) -> Dict[str, bool]:
        """
        Get all rules and their states for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            Dictionary mapping rules to their enabled state
            
        Example:
            rules = service.get_all_rules(12345)
            for rule, enabled in rules.items():
                print(f"{rule}: {'ON' if enabled else 'OFF'}")
        """
        settings = self.get_settings(user_id)
        return settings.toggle_rules.copy()
    
    def clear_rules(self, user_id: int) -> int:
        """
        Clear all toggle rules for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            Number of rules cleared
            
        Example:
            count = service.clear_rules(12345)
            print(f"Cleared {count} rules")
        """
        settings = self.get_settings(user_id)
        count = len(settings.toggle_rules)
        settings.toggle_rules.clear()
        self.save_settings(user_id, settings)
        logger.info(f"Cleared {count} rules for user {user_id}")
        return count
    
    def reset_user(self, user_id: int) -> None:
        """
        Reset all settings for a user to defaults.
        
        Args:
            user_id: The unique identifier of the user
            
        Example:
            service.reset_user(12345)
            print("User settings reset to defaults")
        """
        default_settings = UserSettings()
        self.save_settings(user_id, default_settings)
        logger.info(f"Reset settings for user {user_id}")
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete all data for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if deleted, False if user didn't exist
            
        Example:
            if service.delete_user(12345):
                print("User data deleted successfully")
        """
        result = self.repository.delete_user_settings(user_id)
        if result:
            logger.info(f"Deleted user {user_id}")
        return result
    
    def user_exists(self, user_id: int) -> bool:
        """
        Check if a user has saved settings.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            True if user has settings, False otherwise
            
        Example:
            if service.user_exists(12345):
                print("User has saved settings")
        """
        return self.repository.user_exists(user_id)