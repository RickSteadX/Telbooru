# Repository Pattern Refactoring Guide

## Overview

This document explains the refactoring of the Telbooru bot to implement the Repository Pattern, a design pattern that provides an abstraction layer between the business logic and data access layers.

## What is the Repository Pattern?

The Repository Pattern is a design pattern that:
- **Separates concerns**: Business logic is separated from data access logic
- **Improves testability**: Repositories can be easily mocked for unit testing
- **Increases maintainability**: Changes to data sources don't affect business logic
- **Enables flexibility**: Easy to swap data sources (API, database, cache, etc.)

## Architecture Changes

### Before Refactoring

```
┌─────────────────────────────────────┐
│         TelbooruBot                 │
│  (Presentation + Business Logic +   │
│        Data Access Mixed)           │
├─────────────────────────────────────┤
│  - Direct API calls                 │
│  - File I/O operations              │
│  - Business logic                   │
│  - Telegram handlers                │
└─────────────────────────────────────┘
```

**Problems:**
- Tight coupling between layers
- Difficult to test
- Hard to maintain
- Cannot easily swap data sources

### After Refactoring

```
┌─────────────────────────────────────┐
│      Presentation Layer             │
│      (TelbooruBot)                  │
│  - Telegram handlers                │
│  - UI logic                         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Service Layer                 │
│  (BooruService, UserService)        │
│  - Business logic                   │
│  - Domain rules                     │
│  - Orchestration                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Repository Layer               │
│  (BooruRepository, UserRepository)  │
│  - Data access abstraction          │
│  - CRUD operations                  │
│  - Data source management           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Data Sources                  │
│  - Booru API                        │
│  - File system                      │
│  - Memory cache                     │
└─────────────────────────────────────┘
```

**Benefits:**
- Clear separation of concerns
- Easy to test each layer independently
- Flexible data source management
- Better code organization

## New Structure

### 1. Repository Interfaces (`repositories/interfaces.py`)

Abstract base classes defining contracts for data access:

```python
class IBooruRepository(ABC):
    """Interface for Booru API operations"""
    @abstractmethod
    async def get_posts(self, criteria: PostSearchCriteria) -> Dict[str, Any]:
        pass

class IUserRepository(ABC):
    """Interface for user data operations"""
    @abstractmethod
    def get_user_settings(self, user_id: int) -> UserSettings:
        pass

class ISearchRepository(ABC):
    """Interface for search state management"""
    @abstractmethod
    def save_search_state(self, user_id: int, state: SearchState) -> None:
        pass
```

### 2. Concrete Repositories

#### BooruRepository (`repositories/booru_repository.py`)
- Implements `IBooruRepository`
- Handles all HTTP API calls
- Manages connection lifecycle
- Provides error handling

#### UserRepository (`repositories/user_repository.py`)
- Implements `IUserRepository`
- Manages file-based user data storage
- Handles serialization/deserialization
- Provides CRUD operations

#### SearchRepository (`repositories/search_repository.py`)
- Implements `ISearchRepository`
- Manages in-memory search state
- Provides fast access to pagination data
- Handles state cleanup

### 3. Service Layer

#### BooruService (`services/booru_service.py`)
- Orchestrates Booru operations
- Applies business rules (user preferences)
- Provides high-level operations
- Coordinates repository calls

#### UserService (`services/user_service.py`)
- Manages user settings
- Implements user-related business logic
- Provides convenient methods for common operations
- Validates user input

### 4. Refactored Bot (`main_refactored.py`)
- Uses dependency injection
- Delegates to services
- Focuses on presentation logic
- Cleaner, more maintainable code

## Key Improvements

### 1. Separation of Concerns

**Before:**
```python
# Mixed concerns in one class
class TelbooruBot:
    async def perform_batch_search(self, update, tags, user_id):
        # Load user settings (data access)
        settings = self.user_data_manager.load_user_settings(user_id)
        
        # Apply business logic
        if settings.auto_tags:
            tags = f"{tags} {' '.join(settings.auto_tags)}"
        
        # Make API call (data access)
        async with BooruAPIWrapper(...) as api:
            response = await api.get_posts(limit=50, tags=tags)
        
        # Handle presentation
        await self.send_search_results_page(...)
```

**After:**
```python
# Clear separation
class TelbooruBot:
    async def perform_batch_search(self, update, tags, user_id):
        # Get settings via service
        settings = self.user_service.get_settings(user_id)
        
        # Use service for business logic
        async with BooruRepository(...) as repo:
            service = BooruService(repo)
            posts = await service.search_posts_with_preferences(
                tags, settings, limit=50
            )
        
        # Focus on presentation
        await self.send_search_results_page(...)
```

### 2. Improved Testability

**Before:** Hard to test due to tight coupling
```python
# Cannot easily mock API calls or file I/O
def test_search():
    bot = TelbooruBot(...)  # Requires real API credentials
    # Test requires actual API calls
```

**After:** Easy to test with mocks
```python
# Can mock repositories
def test_search():
    mock_repo = Mock(spec=IBooruRepository)
    mock_repo.get_posts.return_value = {'post': [test_data]}
    
    service = BooruService(mock_repo)
    result = await service.search_posts("test")
    
    assert len(result) == 1
```

### 3. Flexibility

**Before:** Changing data source requires modifying multiple files
```python
# Tightly coupled to file storage
class UserDataManager:
    def load_user_settings(self, user_id):
        with open(file_path, 'rb') as f:
            return pickle.load(f)
```

**After:** Easy to swap implementations
```python
# Can easily create alternative implementations
class DatabaseUserRepository(IUserRepository):
    def get_user_settings(self, user_id):
        return self.db.query(UserSettings).filter_by(id=user_id).first()

class RedisUserRepository(IUserRepository):
    def get_user_settings(self, user_id):
        data = self.redis.get(f"user:{user_id}")
        return UserSettings.from_json(data)
```

### 4. Better Error Handling

**Before:** Generic exceptions
```python
try:
    response = await api.get_posts(...)
except Exception as e:
    logger.error(f"Error: {e}")
```

**After:** Specific repository exceptions
```python
try:
    posts = await repo.get_posts(criteria)
except RepositoryConnectionException as e:
    # Handle connection errors
    logger.error(f"Connection failed: {e}")
except RepositoryDataException as e:
    # Handle data errors
    logger.error(f"Data error: {e}")
```

## Migration Path

### Step 1: Use Refactored Version
```bash
# Backup original
cp main.py main_original.py

# Use refactored version
cp main_refactored.py main.py
```

### Step 2: Test Thoroughly
- Test all bot commands
- Verify search functionality
- Check settings management
- Validate error handling

### Step 3: Monitor Performance
- Check response times
- Monitor memory usage
- Verify API call patterns

### Step 4: Gradual Adoption
- Start with new features using repositories
- Gradually refactor existing code
- Maintain backward compatibility

## Usage Examples

### Example 1: Using BooruService

```python
from repositories.booru_repository import BooruRepository, PostSearchCriteria
from services.booru_service import BooruService

async def search_images(tags: str):
    async with BooruRepository(base_url, api_key, user_id) as repo:
        service = BooruService(repo)
        
        # Simple search
        posts = await service.search_posts(tags, limit=10)
        
        # Search with user preferences
        settings = UserSettings(auto_tags=["rating:safe"])
        posts = await service.search_posts_with_preferences(
            tags, settings, limit=10
        )
        
        # Get specific post
        post = await service.get_post_by_id(12345)
        
        return posts
```

### Example 2: Using UserService

```python
from repositories.user_repository import UserRepository
from services.user_service import UserService

def manage_user_settings(user_id: int):
    repo = UserRepository(data_dir="user_data")
    service = UserService(repo)
    
    # Add auto tag
    service.add_auto_tag(user_id, "rating:safe")
    
    # Toggle rule
    enabled = service.toggle_rule(user_id, "score:>100")
    
    # Get all settings
    settings = service.get_settings(user_id)
    print(f"Auto tags: {settings.auto_tags}")
    print(f"Enabled rules: {service.get_enabled_rules(user_id)}")
```

### Example 3: Custom Repository Implementation

```python
from repositories.interfaces import IUserRepository
from repositories.user_repository import UserSettings

class DatabaseUserRepository(IUserRepository):
    """Alternative implementation using database"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        row = self.db.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if row:
            return UserSettings(
                auto_tags=json.loads(row['auto_tags']),
                toggle_rules=json.loads(row['toggle_rules'])
            )
        return UserSettings()
    
    def save_user_settings(self, user_id: int, settings: UserSettings):
        self.db.execute(
            "INSERT OR REPLACE INTO user_settings VALUES (?, ?, ?)",
            (user_id, json.dumps(settings.auto_tags), 
             json.dumps(settings.toggle_rules))
        )
        self.db.commit()
```

## Testing Strategy

### Unit Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock
from repositories.interfaces import IBooruRepository
from services.booru_service import BooruService

@pytest.mark.asyncio
async def test_search_posts():
    # Arrange
    mock_repo = Mock(spec=IBooruRepository)
    mock_repo.get_posts = AsyncMock(return_value={
        'post': [{'id': 1, 'tags': 'test'}]
    })
    
    service = BooruService(mock_repo)
    
    # Act
    result = await service.search_posts("test", limit=10)
    
    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 1
    mock_repo.get_posts.assert_called_once()

def test_add_auto_tag():
    # Arrange
    mock_repo = Mock(spec=IUserRepository)
    mock_repo.get_user_settings.return_value = UserSettings()
    
    service = UserService(mock_repo)
    
    # Act
    result = service.add_auto_tag(12345, "rating:safe")
    
    # Assert
    assert result is True
    mock_repo.save_user_settings.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_search_flow():
    # Use real repositories with test data
    async with BooruRepository(test_api_url) as repo:
        service = BooruService(repo)
        
        # Test actual API call
        posts = await service.search_posts("test", limit=5)
        
        assert len(posts) <= 5
        assert all('id' in post for post in posts)
```

## Best Practices

### 1. Always Use Interfaces
```python
# Good: Depend on interface
def __init__(self, repo: IBooruRepository):
    self.repo = repo

# Bad: Depend on concrete class
def __init__(self, repo: BooruRepository):
    self.repo = repo
```

### 2. Use Dependency Injection
```python
# Good: Inject dependencies
service = BooruService(repository)

# Bad: Create dependencies internally
class BooruService:
    def __init__(self):
        self.repo = BooruRepository(...)  # Hard-coded
```

### 3. Handle Errors Appropriately
```python
# Good: Specific error handling
try:
    posts = await repo.get_posts(criteria)
except RepositoryConnectionException:
    # Handle connection errors
    return []
except RepositoryDataException:
    # Handle data errors
    return []

# Bad: Generic error handling
try:
    posts = await repo.get_posts(criteria)
except Exception:
    return []
```

### 4. Keep Services Stateless
```python
# Good: Stateless service
class BooruService:
    def __init__(self, repo: IBooruRepository):
        self.repo = repo  # Only dependency

# Bad: Stateful service
class BooruService:
    def __init__(self, repo: IBooruRepository):
        self.repo = repo
        self.cached_posts = []  # State
```

## Performance Considerations

### 1. Connection Pooling
```python
# Use context managers for proper resource management
async with BooruRepository(base_url) as repo:
    service = BooruService(repo)
    posts = await service.search_posts("test")
# Connection automatically closed
```

### 2. Caching
```python
# Add caching layer if needed
class CachedBooruRepository(IBooruRepository):
    def __init__(self, repo: IBooruRepository, cache):
        self.repo = repo
        self.cache = cache
    
    async def get_posts(self, criteria):
        cache_key = f"posts:{criteria.tags}:{criteria.limit}"
        
        if cached := self.cache.get(cache_key):
            return cached
        
        result = await self.repo.get_posts(criteria)
        self.cache.set(cache_key, result, ttl=300)
        return result
```

### 3. Batch Operations
```python
# Use bulk operations when available
user_service.bulk_update_settings({
    12345: settings1,
    67890: settings2
})
```

## Troubleshooting

### Issue: Import Errors
```bash
# Ensure repositories package is importable
export PYTHONPATH="${PYTHONPATH}:/path/to/Telbooru"
```

### Issue: Async Context Manager Errors
```python
# Always use async with for repositories
async with BooruRepository(...) as repo:
    # Use repo here
# Don't forget await
```

### Issue: Pickle Compatibility
```python
# If upgrading from old version, handle migration
try:
    settings = pickle.load(f)
except Exception:
    # Migrate to new format
    settings = UserSettings()
```

## Conclusion

The Repository Pattern refactoring provides:
- ✅ Better code organization
- ✅ Improved testability
- ✅ Increased flexibility
- ✅ Easier maintenance
- ✅ Clear separation of concerns

The refactored codebase is production-ready and follows industry best practices for software architecture.