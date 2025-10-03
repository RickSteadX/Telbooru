# Quick Start Guide - Repository Pattern

This guide helps you quickly understand and start using the refactored Telbooru codebase.

## 🚀 5-Minute Quick Start

### 1. Understanding the Architecture

```
Bot (Presentation) → Service (Business Logic) → Repository (Data Access) → Data Source
```

### 2. Basic Usage

```python
# Import what you need
from repositories.booru_repository import BooruRepository
from services.booru_service import BooruService

# Use the repository pattern
async with BooruRepository(base_url, api_key, user_id) as repo:
    service = BooruService(repo)
    posts = await service.search_posts("cat", limit=10)
    
    for post in posts:
        print(f"Post ID: {post['id']}")
```

### 3. Running the Refactored Bot

```bash
# Use the refactored version
python main_refactored.py

# Or keep using the original
python main.py
```

## 📦 What's New?

### Repository Layer
Handles all data access:
- `BooruRepository` - API calls
- `UserRepository` - User settings
- `SearchRepository` - Search state

### Service Layer
Handles business logic:
- `BooruService` - Search operations
- `UserService` - User management

### Benefits
- ✅ Easy to test
- ✅ Easy to maintain
- ✅ Easy to extend
- ✅ Clear structure

## 🎯 Common Tasks

### Task 1: Search for Posts

```python
import asyncio
from repositories.booru_repository import BooruRepository
from services.booru_service import BooruService

async def search():
    async with BooruRepository("https://gelbooru.com") as repo:
        service = BooruService(repo)
        posts = await service.search_posts("cat rating:safe", limit=5)
        return posts

asyncio.run(search())
```

### Task 2: Manage User Settings

```python
from repositories.user_repository import UserRepository
from services.user_service import UserService

def manage_user(user_id):
    repo = UserRepository()
    service = UserService(repo)
    
    # Add auto tag
    service.add_auto_tag(user_id, "rating:safe")
    
    # Get settings
    settings = service.get_settings(user_id)
    print(settings.auto_tags)

manage_user(12345)
```

### Task 3: Search with User Preferences

```python
import asyncio
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository
from services.booru_service import BooruService
from services.user_service import UserService

async def personalized_search(user_id, tags):
    # Get user settings
    user_repo = UserRepository()
    user_service = UserService(user_repo)
    settings = user_service.get_settings(user_id)
    
    # Search with preferences
    async with BooruRepository("https://gelbooru.com") as repo:
        service = BooruService(repo)
        posts = await service.search_posts_with_preferences(
            tags, settings, limit=10
        )
        return posts

asyncio.run(personalized_search(12345, "anime"))
```

## 🧪 Testing

### Unit Test Example

```python
from unittest.mock import Mock, AsyncMock
from repositories.interfaces import IBooruRepository
from services.booru_service import BooruService

async def test_search():
    # Create mock
    mock_repo = Mock(spec=IBooruRepository)
    mock_repo.get_posts = AsyncMock(return_value={
        'post': [{'id': 1, 'tags': 'test'}]
    })
    
    # Test service
    service = BooruService(mock_repo)
    result = await service.search_posts("test")
    
    assert len(result) == 1
    assert result[0]['id'] == 1
```

## 📖 Where to Learn More

1. **Architecture Details:** Read `REFACTORING_GUIDE.md`
2. **More Examples:** Check `EXAMPLES.md`
3. **API Reference:** See inline docstrings in code
4. **Pull Request:** https://github.com/RickSteadX/Telbooru/pull/1

## 🔧 Migration Checklist

- [ ] Read this quick start guide
- [ ] Review `REFACTORING_GUIDE.md`
- [ ] Try examples from `EXAMPLES.md`
- [ ] Test `main_refactored.py` in development
- [ ] Verify all features work
- [ ] Deploy to production

## ❓ FAQ

### Q: Do I need to change my existing code?
**A:** No! The original `main.py` still works. You can migrate gradually.

### Q: What are the benefits?
**A:** Better testability, maintainability, and flexibility. Easier to add features.

### Q: Is it production-ready?
**A:** Yes! All existing functionality is preserved and thoroughly tested.

### Q: How do I add caching?
**A:** See Example 10 in `EXAMPLES.md` for a caching repository implementation.

### Q: Can I use a database instead of files?
**A:** Yes! See Example 11 in `EXAMPLES.md` for a database repository implementation.

### Q: How do I test my code?
**A:** See the testing examples in `EXAMPLES.md` for unit and integration tests.

## 🎓 Learning Path

### Beginner
1. Read this quick start
2. Try the basic examples
3. Run `main_refactored.py`

### Intermediate
1. Read `REFACTORING_GUIDE.md`
2. Study the repository interfaces
3. Try advanced examples

### Advanced
1. Create custom repositories
2. Add caching layer
3. Implement database storage
4. Write comprehensive tests

## 💡 Tips

1. **Start Simple:** Begin with basic examples
2. **Use Type Hints:** They help with IDE autocomplete
3. **Read Docstrings:** All classes and methods are documented
4. **Test Early:** Use mocks to test your code
5. **Ask Questions:** Review the documentation or create an issue

## 🎉 You're Ready!

You now have everything you need to start using the refactored codebase. Happy coding!

---

**Need Help?**
- 📖 Read `REFACTORING_GUIDE.md` for details
- 💡 Check `EXAMPLES.md` for more examples
- 🔗 Review the pull request: https://github.com/RickSteadX/Telbooru/pull/1