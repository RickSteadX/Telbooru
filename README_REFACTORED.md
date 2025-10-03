# Telbooru - Repository Pattern Implementation

> A clean, maintainable, and testable architecture for the Telbooru Telegram bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Repository Pattern](https://img.shields.io/badge/pattern-repository-green.svg)](https://martinfowler.com/eaaCatalog/repository.html)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

## 🎯 Overview

This is a refactored version of Telbooru that implements the **Repository Pattern**, providing:

- ✅ **Clear Separation of Concerns** - Presentation, business logic, and data access are separated
- ✅ **Improved Testability** - Easy to mock and test each layer independently
- ✅ **Better Maintainability** - Changes to one layer don't affect others
- ✅ **Increased Flexibility** - Easy to swap data sources or add new features
- ✅ **SOLID Principles** - Follows industry best practices

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│      Presentation Layer             │
│      (TelbooruBot)                  │
│  • Telegram handlers                │
│  • UI logic                         │
│  • User interaction                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Service Layer                 │
│  (BooruService, UserService)        │
│  • Business logic                   │
│  • Domain rules                     │
│  • Orchestration                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Repository Layer               │
│  (Repositories)                     │
│  • Data access abstraction          │
│  • CRUD operations                  │
│  • Data source management           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Data Sources                  │
│  • Booru API (HTTP)                 │
│  • File system (Pickle)             │
│  • Memory (Cache)                   │
└─────────────────────────────────────┘
```

## 📦 Components

### Repository Layer

#### BooruRepository
Handles all Booru API interactions:
```python
async with BooruRepository(base_url, api_key, user_id) as repo:
    criteria = PostSearchCriteria(tags="cat", limit=10)
    result = await repo.get_posts(criteria)
```

**Features:**
- Async HTTP client management
- Automatic connection handling
- Error handling with custom exceptions
- Query parameter encoding
- Response normalization

#### UserRepository
Manages user settings persistence:
```python
repo = UserRepository(data_dir="user_data")
settings = repo.get_user_settings(user_id)
settings.auto_tags.append("rating:safe")
repo.save_user_settings(user_id, settings)
```

**Features:**
- File-based storage
- Pickle serialization
- Automatic directory creation
- Bulk operations support
- User existence checking

#### SearchRepository
Manages search state in memory:
```python
repo = SearchRepository()
state = SearchState(query="cat", results=posts, current_page=0)
repo.save_search_state(user_id, state)
```

**Features:**
- Fast in-memory storage
- Pagination support
- State cleanup
- Active user tracking

### Service Layer

#### BooruService
Encapsulates Booru business logic:
```python
service = BooruService(booru_repository)

# Simple search
posts = await service.search_posts("cat", limit=10)

# Search with user preferences
posts = await service.search_posts_with_preferences(
    "cat", user_settings, limit=10
)

# Get specific post
post = await service.get_post_by_id(12345)

# Search tags
tags = await service.search_tags_with_fallback("school", limit=20)
```

**Features:**
- User preference application (auto tags, toggle rules)
- Media type detection
- URL selection (preview, sample, full)
- Post information extraction
- Tag search with fallback

#### UserService
Manages user-related operations:
```python
service = UserService(user_repository)

# Manage auto tags
service.add_auto_tag(user_id, "rating:safe")
service.remove_auto_tag(user_id, "rating:safe")
tags = service.get_auto_tags(user_id)

# Manage toggle rules
enabled = service.toggle_rule(user_id, "score:>100")
service.set_rule(user_id, "sort:score", True)
rules = service.get_enabled_rules(user_id)

# User management
settings = service.get_settings(user_id)
service.reset_user(user_id)
service.delete_user(user_id)
```

**Features:**
- Auto tag management
- Toggle rule management
- Settings persistence
- User lifecycle management
- Bulk operations

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/RickSteadX/Telbooru.git
cd Telbooru

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

```bash
# .env file
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
BOORU_API_BASE_URL=https://gelbooru.com
BOORU_API_KEY=your_api_key  # Optional
BOORU_USER_ID=your_user_id  # Optional
```

### Running the Bot

```bash
# Use the refactored version
python main_refactored.py

# Or use the original version
python main.py
```

## 📚 Documentation

### Comprehensive Guides

1. **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
2. **[REFACTORING_GUIDE.md](REFACTORING_GUIDE.md)** - Detailed architecture guide
3. **[EXAMPLES.md](EXAMPLES.md)** - 13+ practical examples
4. **[SUMMARY.md](SUMMARY.md)** - Project summary and metrics

### Code Documentation

All classes and methods include:
- Comprehensive docstrings
- Parameter descriptions
- Return value documentation
- Usage examples
- Type hints

## 💡 Usage Examples

### Example 1: Simple Search

```python
import asyncio
from repositories.booru_repository import BooruRepository
from services.booru_service import BooruService

async def search_images():
    async with BooruRepository("https://gelbooru.com") as repo:
        service = BooruService(repo)
        posts = await service.search_posts("cat rating:safe", limit=10)
        
        for post in posts:
            info = service.extract_post_info(post)
            print(f"Post {info['id']}: {info['width']}x{info['height']}")

asyncio.run(search_images())
```

### Example 2: User Settings

```python
from repositories.user_repository import UserRepository
from services.user_service import UserService

def manage_settings(user_id):
    repo = UserRepository()
    service = UserService(repo)
    
    # Add preferences
    service.add_auto_tag(user_id, "rating:safe")
    service.set_rule(user_id, "score:>100", True)
    
    # View settings
    settings = service.get_settings(user_id)
    print(f"Auto tags: {settings.auto_tags}")
    print(f"Rules: {service.get_enabled_rules(user_id)}")

manage_settings(12345)
```

### Example 3: Personalized Search

```python
import asyncio
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository
from services.booru_service import BooruService
from services.user_service import UserService

async def personalized_search(user_id, tags):
    # Get user preferences
    user_repo = UserRepository()
    user_service = UserService(user_repo)
    settings = user_service.get_settings(user_id)
    
    # Search with preferences applied
    async with BooruRepository("https://gelbooru.com") as repo:
        service = BooruService(repo)
        posts = await service.search_posts_with_preferences(
            tags, settings, limit=20
        )
        return posts

asyncio.run(personalized_search(12345, "anime girl"))
```

## 🧪 Testing

### Unit Testing

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
        'post': [{'id': 1, 'tags': 'cat'}]
    })
    
    service = BooruService(mock_repo)
    
    # Act
    result = await service.search_posts("cat", limit=10)
    
    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 1
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow():
    async with BooruRepository("https://gelbooru.com") as repo:
        service = BooruService(repo)
        posts = await service.search_posts("test", limit=5)
        
        assert len(posts) <= 5
        assert all('id' in post for post in posts)
```

## 🎨 Extending the Code

### Custom Repository Implementation

```python
from repositories.interfaces import IUserRepository
from repositories.user_repository import UserSettings

class DatabaseUserRepository(IUserRepository):
    """User repository using database instead of files."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        # Implement database query
        row = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
        return UserSettings.from_dict(row)
    
    def save_user_settings(self, user_id: int, settings: UserSettings):
        # Implement database save
        self.db.execute("UPDATE users SET settings = ? WHERE id = ?",
                       settings.to_dict(), user_id)
```

### Custom Service

```python
from services.booru_service import BooruService

class AnalyticsService:
    """Service for analytics and statistics."""
    
    def __init__(self, booru_service: BooruService):
        self.booru_service = booru_service
    
    async def get_popular_tags(self, limit: int = 10):
        tags = await self.booru_service.search_tags(limit=100)
        sorted_tags = sorted(tags, key=lambda t: t.get('count', 0), reverse=True)
        return sorted_tags[:limit]
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Your Telegram bot token |
| `BOORU_API_BASE_URL` | Yes | Base URL of the Booru API |
| `BOORU_API_KEY` | No | API key for authentication |
| `BOORU_USER_ID` | No | User ID for authentication |

### Repository Configuration

```python
# File-based user repository
user_repo = UserRepository(data_dir="user_data")

# In-memory search repository
search_repo = SearchRepository()

# Booru repository with authentication
async with BooruRepository(
    base_url="https://gelbooru.com",
    api_key="your_key",
    user_id="your_id"
) as repo:
    # Use repository
    pass
```

## 📊 Performance

### Benchmarks

- **API Calls:** Same performance as original (no overhead)
- **File I/O:** Same performance as original
- **Memory Usage:** Minimal overhead from abstraction layers
- **Startup Time:** Negligible difference

### Optimization Opportunities

1. **Caching Layer:** Easy to add (see Example 10 in EXAMPLES.md)
2. **Connection Pooling:** Can be implemented in repository
3. **Batch Operations:** Supported by repositories
4. **Query Optimization:** Can be done at repository level

## 🔒 Security

- Same security model as original
- No new external dependencies
- Maintains existing authentication
- Secure file storage
- No sensitive data in logs

## 🤝 Contributing

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests
- Update documentation

## 📝 Migration Guide

### From Original to Refactored

1. **Test the refactored version:**
   ```bash
   python main_refactored.py
   ```

2. **Verify functionality:**
   - Test all bot commands
   - Check user settings
   - Verify search results

3. **Switch to refactored version:**
   ```bash
   mv main.py main_original.py
   mv main_refactored.py main.py
   ```

4. **Monitor for issues:**
   - Check logs
   - Monitor performance
   - Verify user data

### Backward Compatibility

- ✅ All existing features work
- ✅ User data format unchanged
- ✅ Same environment variables
- ✅ Same dependencies
- ✅ No breaking changes

## 🐛 Troubleshooting

### Common Issues

**Issue:** Import errors
```bash
# Solution: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Telbooru"
```

**Issue:** Async context manager errors
```python
# Solution: Always use async with
async with BooruRepository(...) as repo:
    # Use repo here
```

**Issue:** Pickle compatibility
```python
# Solution: Handle migration
try:
    settings = pickle.load(f)
except Exception:
    settings = UserSettings()  # Use defaults
```

## 📈 Metrics

| Metric | Value |
|--------|-------|
| Total Lines Added | 4,400+ |
| New Files | 12 |
| Repositories | 3 |
| Services | 2 |
| Documentation Pages | 4 |
| Examples | 13+ |
| Test Examples | 5+ |

## 🎓 Learning Resources

### Recommended Reading Order

1. **[QUICK_START.md](QUICK_START.md)** - Start here
2. **[EXAMPLES.md](EXAMPLES.md)** - Practical examples
3. **[REFACTORING_GUIDE.md](REFACTORING_GUIDE.md)** - Deep dive
4. **Code Documentation** - Inline docstrings

### External Resources

- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection)

## 📞 Support

- **Documentation:** See guides in this repository
- **Issues:** Create an issue on GitHub
- **Pull Request:** https://github.com/RickSteadX/Telbooru/pull/1

## 📄 License

Same license as the original Telbooru project.

## 🙏 Acknowledgments

This refactoring follows industry best practices and design patterns to improve code quality and maintainability while preserving all existing functionality.

## ✨ What's Next?

### Planned Enhancements

- [ ] Add caching layer
- [ ] Implement database repository
- [ ] Add more unit tests
- [ ] Performance optimization
- [ ] Add monitoring/metrics
- [ ] Create admin dashboard

### Community Contributions Welcome!

We welcome contributions that:
- Add new repository implementations
- Improve existing services
- Add more tests
- Improve documentation
- Fix bugs

---

**Made with ❤️ using the Repository Pattern**

For questions or feedback, please create an issue or submit a pull request.