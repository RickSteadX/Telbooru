# Repository Pattern Usage Examples

This document provides practical examples of using the refactored Telbooru codebase with the Repository Pattern.

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Advanced Patterns](#advanced-patterns)
3. [Testing Examples](#testing-examples)
4. [Custom Implementations](#custom-implementations)
5. [Real-World Scenarios](#real-world-scenarios)

## Basic Usage

### Example 1: Simple Post Search

```python
import asyncio
from repositories.booru_repository import BooruRepository, PostSearchCriteria
from services.booru_service import BooruService

async def search_cat_images():
    """Search for cat images using the repository pattern."""
    
    # Configuration
    base_url = "https://gelbooru.com"
    api_key = "your_api_key"
    user_id = "your_user_id"
    
    # Use repository with context manager
    async with BooruRepository(base_url, api_key, user_id) as repo:
        # Create service
        service = BooruService(repo)
        
        # Search for posts
        posts = await service.search_posts(
            tags="cat rating:safe",
            limit=10
        )
        
        # Process results
        for post in posts:
            info = service.extract_post_info(post)
            print(f"Post ID: {info['id']}")
            print(f"Size: {info['width']}x{info['height']}")
            print(f"Score: {info['score']}")
            print(f"URL: {info['file_url']}")
            print("-" * 50)
        
        return posts

# Run the example
if __name__ == "__main__":
    asyncio.run(search_cat_images())
```

### Example 2: User Settings Management

```python
from repositories.user_repository import UserRepository, UserSettings
from services.user_service import UserService

def manage_user_preferences(user_id: int):
    """Manage user settings using the repository pattern."""
    
    # Initialize repository and service
    repo = UserRepository(data_dir="user_data")
    service = UserService(repo)
    
    # Add auto tags
    print("Adding auto tags...")
    service.add_auto_tag(user_id, "rating:safe")
    service.add_auto_tag(user_id, "score:>50")
    
    # Enable toggle rules
    print("Enabling toggle rules...")
    service.set_rule(user_id, "sort:score", True)
    service.set_rule(user_id, "rating:safe", True)
    
    # Get current settings
    settings = service.get_settings(user_id)
    print(f"\nCurrent Settings for User {user_id}:")
    print(f"Auto Tags: {settings.auto_tags}")
    print(f"Enabled Rules: {service.get_enabled_rules(user_id)}")
    
    # Toggle a rule
    new_state = service.toggle_rule(user_id, "sort:score")
    print(f"\nToggled 'sort:score': {'ON' if new_state else 'OFF'}")
    
    return settings

# Run the example
if __name__ == "__main__":
    user_id = 12345
    manage_user_preferences(user_id)
```

### Example 3: Search with User Preferences

```python
import asyncio
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository, UserSettings
from services.booru_service import BooruService
from services.user_service import UserService

async def personalized_search(user_id: int, search_tags: str):
    """Search with user's personalized preferences."""
    
    # Initialize repositories
    user_repo = UserRepository()
    user_service = UserService(user_repo)
    
    # Get user settings
    settings = user_service.get_settings(user_id)
    print(f"User preferences: {settings.auto_tags}")
    
    # Perform search with preferences
    base_url = "https://gelbooru.com"
    async with BooruRepository(base_url) as repo:
        service = BooruService(repo)
        
        # This automatically applies user's auto tags and toggle rules
        posts = await service.search_posts_with_preferences(
            tags=search_tags,
            user_settings=settings,
            limit=20
        )
        
        print(f"\nFound {len(posts)} posts")
        for i, post in enumerate(posts[:5], 1):
            info = service.extract_post_info(post)
            print(f"{i}. Post {info['id']} - Score: {info['score']}")
        
        return posts

# Run the example
if __name__ == "__main__":
    asyncio.run(personalized_search(12345, "anime girl"))
```

### Example 4: Tag Search

```python
import asyncio
from repositories.booru_repository import BooruRepository, TagSearchCriteria
from services.booru_service import BooruService

async def find_popular_tags(pattern: str):
    """Find popular tags matching a pattern."""
    
    base_url = "https://gelbooru.com"
    
    async with BooruRepository(base_url) as repo:
        service = BooruService(repo)
        
        # Search for tags with fallback
        tags = await service.search_tags_with_fallback(
            query=pattern,
            limit=20
        )
        
        # Sort by popularity
        sorted_tags = sorted(
            tags,
            key=lambda t: t.get('count', 0),
            reverse=True
        )
        
        print(f"Popular tags matching '{pattern}':\n")
        for i, tag in enumerate(sorted_tags[:10], 1):
            name = tag.get('name', 'Unknown')
            count = tag.get('count', 0)
            print(f"{i}. {name} ({count:,} posts)")
        
        return sorted_tags

# Run the example
if __name__ == "__main__":
    asyncio.run(find_popular_tags("school"))
```

## Advanced Patterns

### Example 5: Batch Processing

```python
import asyncio
from repositories.booru_repository import BooruRepository
from services.booru_service import BooruService

async def batch_download_posts(tag_list: list, posts_per_tag: int = 5):
    """Download posts for multiple tags in batch."""
    
    base_url = "https://gelbooru.com"
    all_results = {}
    
    async with BooruRepository(base_url) as repo:
        service = BooruService(repo)
        
        # Process each tag
        for tag in tag_list:
            print(f"Processing tag: {tag}")
            
            try:
                posts = await service.search_posts(
                    tags=tag,
                    limit=posts_per_tag
                )
                
                all_results[tag] = posts
                print(f"  Found {len(posts)} posts")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"  Error: {e}")
                all_results[tag] = []
        
        # Summary
        print("\n" + "=" * 50)
        print("Batch Processing Summary:")
        for tag, posts in all_results.items():
            print(f"  {tag}: {len(posts)} posts")
        
        return all_results

# Run the example
if __name__ == "__main__":
    tags = ["cat", "dog", "bird", "fish"]
    asyncio.run(batch_download_posts(tags, posts_per_tag=3))
```

### Example 6: Search State Management

```python
from repositories.search_repository import SearchRepository, SearchState

def manage_search_session(user_id: int):
    """Manage user's search session with pagination."""
    
    # Initialize repository
    repo = SearchRepository()
    
    # Simulate search results
    mock_posts = [
        {'id': i, 'title': f'Post {i}'} 
        for i in range(1, 26)
    ]
    
    # Create search state
    state = SearchState(
        query="test search",
        results=mock_posts,
        current_page=0,
        total_pages=5,
        posts_per_page=5
    )
    
    # Save state
    repo.save_search_state(user_id, state)
    print(f"Saved search state for user {user_id}")
    
    # Navigate pages
    for page in range(3):
        repo.update_page(user_id, page)
        current_state = repo.get_search_state(user_id)
        
        start = page * current_state.posts_per_page
        end = start + current_state.posts_per_page
        page_posts = current_state.results[start:end]
        
        print(f"\nPage {page + 1}:")
        for post in page_posts:
            print(f"  - {post['title']}")
    
    # Clean up
    repo.delete_search_state(user_id)
    print(f"\nCleared search state for user {user_id}")

# Run the example
if __name__ == "__main__":
    manage_search_session(12345)
```

### Example 7: Error Handling

```python
import asyncio
from repositories.booru_repository import BooruRepository
from repositories.interfaces import (
    RepositoryException,
    RepositoryConnectionException,
    RepositoryDataException
)
from services.booru_service import BooruService

async def robust_search(tags: str):
    """Search with comprehensive error handling."""
    
    base_url = "https://gelbooru.com"
    
    try:
        async with BooruRepository(base_url) as repo:
            service = BooruService(repo)
            
            posts = await service.search_posts(tags, limit=10)
            
            if not posts:
                print("No posts found for the given tags")
                return []
            
            print(f"Successfully found {len(posts)} posts")
            return posts
            
    except RepositoryConnectionException as e:
        print(f"Connection error: {e}")
        print("Please check your internet connection and try again")
        return []
        
    except RepositoryDataException as e:
        print(f"Data error: {e}")
        print("The API returned invalid data")
        return []
        
    except RepositoryException as e:
        print(f"Repository error: {e}")
        return []
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

# Run the example
if __name__ == "__main__":
    asyncio.run(robust_search("test"))
```

## Testing Examples

### Example 8: Unit Testing with Mocks

```python
import pytest
from unittest.mock import Mock, AsyncMock
from repositories.interfaces import IBooruRepository, IUserRepository
from repositories.user_repository import UserSettings
from services.booru_service import BooruService
from services.user_service import UserService

# Test BooruService
@pytest.mark.asyncio
async def test_search_posts():
    """Test searching posts with mocked repository."""
    
    # Arrange
    mock_repo = Mock(spec=IBooruRepository)
    mock_repo.get_posts = AsyncMock(return_value={
        'post': [
            {'id': 1, 'tags': 'cat', 'score': 100},
            {'id': 2, 'tags': 'dog', 'score': 200}
        ]
    })
    
    service = BooruService(mock_repo)
    
    # Act
    result = await service.search_posts("test", limit=10)
    
    # Assert
    assert len(result) == 2
    assert result[0]['id'] == 1
    assert result[1]['score'] == 200
    mock_repo.get_posts.assert_called_once()

# Test UserService
def test_add_auto_tag():
    """Test adding auto tag with mocked repository."""
    
    # Arrange
    mock_repo = Mock(spec=IUserRepository)
    mock_repo.get_user_settings.return_value = UserSettings(
        auto_tags=["existing_tag"]
    )
    
    service = UserService(mock_repo)
    
    # Act
    result = service.add_auto_tag(12345, "new_tag")
    
    # Assert
    assert result is True
    mock_repo.save_user_settings.assert_called_once()
    
    # Verify the saved settings
    call_args = mock_repo.save_user_settings.call_args
    saved_settings = call_args[0][1]
    assert "new_tag" in saved_settings.auto_tags
    assert "existing_tag" in saved_settings.auto_tags

def test_add_duplicate_auto_tag():
    """Test adding duplicate auto tag."""
    
    # Arrange
    mock_repo = Mock(spec=IUserRepository)
    mock_repo.get_user_settings.return_value = UserSettings(
        auto_tags=["existing_tag"]
    )
    
    service = UserService(mock_repo)
    
    # Act
    result = service.add_auto_tag(12345, "existing_tag")
    
    # Assert
    assert result is False
    mock_repo.save_user_settings.assert_not_called()

@pytest.mark.asyncio
async def test_search_with_preferences():
    """Test searching with user preferences applied."""
    
    # Arrange
    mock_repo = Mock(spec=IBooruRepository)
    mock_repo.get_posts = AsyncMock(return_value={
        'post': [{'id': 1, 'tags': 'cat rating:safe'}]
    })
    
    service = BooruService(mock_repo)
    settings = UserSettings(
        auto_tags=["rating:safe"],
        toggle_rules={"score:>100": True}
    )
    
    # Act
    result = await service.search_posts_with_preferences(
        "cat", settings, limit=10
    )
    
    # Assert
    assert len(result) == 1
    
    # Verify preferences were applied
    call_args = mock_repo.get_posts.call_args[0][0]
    assert "rating:safe" in call_args.tags
    assert "score:>100" in call_args.tags

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Example 9: Integration Testing

```python
import pytest
import asyncio
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository
from services.booru_service import BooruService
from services.user_service import UserService

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_search_workflow():
    """Integration test for complete search workflow."""
    
    # Setup
    base_url = "https://gelbooru.com"
    user_id = 99999  # Test user
    
    # Initialize repositories
    user_repo = UserRepository(data_dir="test_data")
    user_service = UserService(user_repo)
    
    try:
        # Configure user preferences
        user_service.add_auto_tag(user_id, "rating:safe")
        user_service.set_rule(user_id, "score:>50", True)
        
        # Get settings
        settings = user_service.get_settings(user_id)
        assert "rating:safe" in settings.auto_tags
        
        # Perform search
        async with BooruRepository(base_url) as repo:
            service = BooruService(repo)
            
            posts = await service.search_posts_with_preferences(
                "cat", settings, limit=5
            )
            
            # Verify results
            assert len(posts) <= 5
            assert all('id' in post for post in posts)
            
            # Verify media type detection
            for post in posts:
                media_type = service.get_media_type(post.get('file_url', ''))
                assert media_type in ['image', 'video', 'gif']
        
        print("✅ Integration test passed")
        
    finally:
        # Cleanup
        user_service.delete_user(user_id)

# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
```

## Custom Implementations

### Example 10: Custom Caching Repository

```python
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from repositories.interfaces import IBooruRepository
from repositories.booru_repository import BooruRepository, PostSearchCriteria

class CachedBooruRepository(IBooruRepository):
    """Repository with caching layer."""
    
    def __init__(self, base_repo: IBooruRepository, cache_ttl: int = 300):
        """
        Initialize cached repository.
        
        Args:
            base_repo: Underlying repository
            cache_ttl: Cache time-to-live in seconds
        """
        self.base_repo = base_repo
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
    
    def _get_cache_key(self, criteria: PostSearchCriteria) -> str:
        """Generate cache key from criteria."""
        return f"posts:{criteria.tags}:{criteria.limit}:{criteria.page}"
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cache entry is still valid."""
        return datetime.now() - timestamp < timedelta(seconds=self.cache_ttl)
    
    async def get_posts(self, criteria: PostSearchCriteria) -> Dict[str, Any]:
        """Get posts with caching."""
        cache_key = self._get_cache_key(criteria)
        
        # Check cache
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                print(f"✅ Cache hit for: {cache_key}")
                return data
            else:
                print(f"⏰ Cache expired for: {cache_key}")
                del self.cache[cache_key]
        
        # Cache miss - fetch from base repository
        print(f"❌ Cache miss for: {cache_key}")
        result = await self.base_repo.get_posts(criteria)
        
        # Store in cache
        self.cache[cache_key] = (result, datetime.now())
        
        return result
    
    async def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Get post by ID (delegated to base repository)."""
        return await self.base_repo.get_post_by_id(post_id)
    
    async def get_tags(self, criteria) -> Dict[str, Any]:
        """Get tags (delegated to base repository)."""
        return await self.base_repo.get_tags(criteria)
    
    async def get_comments(self, post_id: int) -> Dict[str, Any]:
        """Get comments (delegated to base repository)."""
        return await self.base_repo.get_comments(post_id)
    
    async def get_deleted_images(self, last_id: Optional[int] = None) -> Dict[str, Any]:
        """Get deleted images (delegated to base repository)."""
        return await self.base_repo.get_deleted_images(last_id)
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        print("🗑️ Cache cleared")

# Usage example
async def use_cached_repository():
    """Example using cached repository."""
    
    base_url = "https://gelbooru.com"
    
    async with BooruRepository(base_url) as base_repo:
        # Wrap with caching layer
        cached_repo = CachedBooruRepository(base_repo, cache_ttl=300)
        
        criteria = PostSearchCriteria(tags="cat", limit=10)
        
        # First call - cache miss
        print("\n1st call:")
        result1 = await cached_repo.get_posts(criteria)
        print(f"Got {len(result1.get('post', []))} posts")
        
        # Second call - cache hit
        print("\n2nd call:")
        result2 = await cached_repo.get_posts(criteria)
        print(f"Got {len(result2.get('post', []))} posts")
        
        # Clear cache
        cached_repo.clear_cache()
        
        # Third call - cache miss again
        print("\n3rd call:")
        result3 = await cached_repo.get_posts(criteria)
        print(f"Got {len(result3.get('post', []))} posts")

if __name__ == "__main__":
    asyncio.run(use_cached_repository())
```

### Example 11: Database User Repository

```python
import sqlite3
import json
from typing import Optional
from repositories.interfaces import IUserRepository
from repositories.user_repository import UserSettings

class DatabaseUserRepository(IUserRepository):
    """User repository using SQLite database."""
    
    def __init__(self, db_path: str = "users.db"):
        """Initialize database repository."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create database schema if not exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                auto_tags TEXT,
                toggle_rules TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """Get user settings from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT auto_tags, toggle_rules FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            auto_tags = json.loads(row[0]) if row[0] else []
            toggle_rules = json.loads(row[1]) if row[1] else {}
            return UserSettings(auto_tags=auto_tags, toggle_rules=toggle_rules)
        
        return UserSettings()
    
    def save_user_settings(self, user_id: int, settings: UserSettings) -> None:
        """Save user settings to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings (user_id, auto_tags, toggle_rules, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            json.dumps(settings.auto_tags),
            json.dumps(settings.toggle_rules)
        ))
        
        conn.commit()
        conn.close()
    
    def delete_user_settings(self, user_id: int) -> bool:
        """Delete user settings from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def user_exists(self, user_id: int) -> bool:
        """Check if user exists in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM user_settings WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists

# Usage example
def use_database_repository():
    """Example using database repository."""
    
    # Initialize database repository
    repo = DatabaseUserRepository(db_path="test_users.db")
    
    user_id = 12345
    
    # Save settings
    settings = UserSettings(
        auto_tags=["rating:safe", "score:>100"],
        toggle_rules={"sort:score": True}
    )
    repo.save_user_settings(user_id, settings)
    print(f"✅ Saved settings for user {user_id}")
    
    # Retrieve settings
    loaded_settings = repo.get_user_settings(user_id)
    print(f"📖 Loaded settings: {loaded_settings.auto_tags}")
    
    # Check existence
    exists = repo.user_exists(user_id)
    print(f"👤 User exists: {exists}")
    
    # Delete settings
    deleted = repo.delete_user_settings(user_id)
    print(f"🗑️ Deleted: {deleted}")

if __name__ == "__main__":
    use_database_repository()
```

## Real-World Scenarios

### Example 12: Building a CLI Tool

```python
import asyncio
import argparse
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository
from services.booru_service import BooruService
from services.user_service import UserService

async def cli_search(args):
    """CLI search command."""
    async with BooruRepository(args.api_url) as repo:
        service = BooruService(repo)
        
        posts = await service.search_posts(
            tags=args.tags,
            limit=args.limit
        )
        
        print(f"\nFound {len(posts)} posts for '{args.tags}':\n")
        for i, post in enumerate(posts, 1):
            info = service.extract_post_info(post)
            print(f"{i}. ID: {info['id']} | Score: {info['score']} | "
                  f"Size: {info['width']}x{info['height']}")

def cli_user_settings(args):
    """CLI user settings command."""
    repo = UserRepository()
    service = UserService(repo)
    
    if args.action == "add":
        service.add_auto_tag(args.user_id, args.tag)
        print(f"✅ Added auto tag: {args.tag}")
    
    elif args.action == "remove":
        service.remove_auto_tag(args.user_id, args.tag)
        print(f"🗑️ Removed auto tag: {args.tag}")
    
    elif args.action == "list":
        settings = service.get_settings(args.user_id)
        print(f"\nUser {args.user_id} Settings:")
        print(f"Auto Tags: {settings.auto_tags}")
        print(f"Toggle Rules: {service.get_enabled_rules(args.user_id)}")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Telbooru CLI Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for posts")
    search_parser.add_argument("tags", help="Search tags")
    search_parser.add_argument("--limit", type=int, default=10, help="Number of results")
    search_parser.add_argument("--api-url", default="https://gelbooru.com", help="API URL")
    
    # User settings command
    user_parser = subparsers.add_parser("user", help="Manage user settings")
    user_parser.add_argument("user_id", type=int, help="User ID")
    user_parser.add_argument("action", choices=["add", "remove", "list"], help="Action")
    user_parser.add_argument("--tag", help="Tag to add/remove")
    
    args = parser.parse_args()
    
    if args.command == "search":
        asyncio.run(cli_search(args))
    elif args.command == "user":
        cli_user_settings(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

Usage:
```bash
# Search for posts
python cli_tool.py search "cat rating:safe" --limit 5

# Manage user settings
python cli_tool.py user 12345 add --tag "rating:safe"
python cli_tool.py user 12345 list
python cli_tool.py user 12345 remove --tag "rating:safe"
```

### Example 13: Web API Endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository
from services.booru_service import BooruService
from services.user_service import UserService

app = FastAPI(title="Telbooru API")

# Configuration
API_BASE_URL = "https://gelbooru.com"

# Models
class SearchRequest(BaseModel):
    tags: str
    limit: int = 10
    user_id: Optional[int] = None

class UserSettingsRequest(BaseModel):
    auto_tags: List[str] = []
    toggle_rules: dict = {}

# Endpoints
@app.post("/api/search")
async def search_posts(request: SearchRequest):
    """Search for posts with optional user preferences."""
    try:
        async with BooruRepository(API_BASE_URL) as repo:
            service = BooruService(repo)
            
            if request.user_id:
                # Search with user preferences
                user_repo = UserRepository()
                user_service = UserService(user_repo)
                settings = user_service.get_settings(request.user_id)
                
                posts = await service.search_posts_with_preferences(
                    request.tags, settings, limit=request.limit
                )
            else:
                # Simple search
                posts = await service.search_posts(
                    request.tags, limit=request.limit
                )
            
            return {
                "success": True,
                "count": len(posts),
                "posts": [service.extract_post_info(p) for p in posts]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}/settings")
def get_user_settings(user_id: int):
    """Get user settings."""
    try:
        repo = UserRepository()
        service = UserService(repo)
        settings = service.get_settings(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "auto_tags": settings.auto_tags,
            "toggle_rules": settings.toggle_rules
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/{user_id}/settings")
def update_user_settings(user_id: int, request: UserSettingsRequest):
    """Update user settings."""
    try:
        repo = UserRepository()
        service = UserService(repo)
        
        # Clear existing settings
        service.reset_user(user_id)
        
        # Add new auto tags
        for tag in request.auto_tags:
            service.add_auto_tag(user_id, tag)
        
        # Set toggle rules
        for rule, enabled in request.toggle_rules.items():
            service.set_rule(user_id, rule, enabled)
        
        return {
            "success": True,
            "message": "Settings updated successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run with: uvicorn web_api:app --reload
```

These examples demonstrate the flexibility and power of the Repository Pattern implementation. You can easily extend, test, and maintain the codebase while keeping concerns properly separated.