# Telbooru Architecture - Repository Pattern

## 📐 System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
│                      (Telegram Messages)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│                      (TelbooruBot)                               │
├─────────────────────────────────────────────────────────────────┤
│  • Command Handlers (/start, /tags)                             │
│  • Callback Query Handlers (buttons)                            │
│  • Message Handlers (text input)                                │
│  • UI Logic (keyboards, menus)                                  │
│  • User State Management                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│              (Business Logic & Orchestration)                    │
├──────────────────────────────┬──────────────────────────────────┤
│     BooruService             │        UserService               │
├──────────────────────────────┼──────────────────────────────────┤
│  • search_posts()            │  • get_settings()                │
│  • search_posts_with_        │  • add_auto_tag()                │
│    preferences()             │  • remove_auto_tag()             │
│  • get_post_by_id()          │  • toggle_rule()                 │
│  • search_tags()             │  • set_rule()                    │
│  • search_tags_with_         │  • get_enabled_rules()           │
│    fallback()                │  • reset_user()                  │
│  • get_media_type()          │  • delete_user()                 │
│  • extract_post_info()       │                                  │
└────────────────────────────┬┴──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REPOSITORY LAYER                              │
│              (Data Access Abstraction)                           │
├──────────────┬──────────────────────┬───────────────────────────┤
│   Booru      │      User            │      Search               │
│  Repository  │   Repository         │    Repository             │
├──────────────┼──────────────────────┼───────────────────────────┤
│ • get_posts()│ • get_user_settings()│ • save_search_state()     │
│ • get_post_  │ • save_user_         │ • get_search_state()      │
│   by_id()    │   settings()         │ • delete_search_state()   │
│ • get_tags() │ • delete_user_       │ • clear_all_states()      │
│ • get_       │   settings()         │ • update_page()           │
│   comments() │ • user_exists()      │ • update_menu_message_id()│
│ • get_       │ • get_all_user_ids() │ • get_active_user_count() │
│   deleted_   │ • bulk_update_       │                           │
│   images()   │   settings()         │                           │
└──────────────┴──────────────────────┴───────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                               │
├──────────────┬──────────────────────┬───────────────────────────┤
│  Booru API   │   File System        │      Memory               │
│   (HTTP)     │   (Pickle Files)     │     (Dictionary)          │
├──────────────┼──────────────────────┼───────────────────────────┤
│ • REST API   │ • user_data/         │ • search_states: {}       │
│ • JSON       │   user_12345.pkl     │ • Fast access             │
│   responses  │ • Persistent         │ • Temporary               │
│ • External   │   storage            │   storage                 │
└──────────────┴──────────────────────┴───────────────────────────┘
```

## 🔄 Data Flow

### Search Flow (with User Preferences)

```
1. User sends message: "cat girl"
   │
   ▼
2. TelbooruBot.handle_text_input()
   │
   ▼
3. TelbooruBot.perform_batch_search()
   │
   ├─► UserService.get_settings(user_id)
   │   │
   │   └─► UserRepository.get_user_settings(user_id)
   │       │
   │       └─► File System: Load user_12345.pkl
   │           │
   │           └─► Returns: UserSettings(auto_tags=["rating:safe"])
   │
   ├─► BooruService.search_posts_with_preferences(tags, settings)
   │   │
   │   ├─► Apply user preferences: "cat girl" + "rating:safe"
   │   │
   │   └─► BooruRepository.get_posts(criteria)
   │       │
   │       └─► HTTP API: GET /index.php?tags=cat+girl+rating:safe
   │           │
   │           └─► Returns: {'post': [...]}
   │
   ├─► SearchRepository.save_search_state(user_id, state)
   │   │
   │   └─► Memory: search_states[12345] = SearchState(...)
   │
   └─► TelbooruBot.send_search_results_page()
       │
       └─► Telegram: Send media group + keyboard
```

### Settings Update Flow

```
1. User clicks "Add Auto Tag" button
   │
   ▼
2. TelbooruBot.handle_autotag_callback()
   │
   └─► Set user state: WAITING_FOR_AUTOTAG
   
3. User sends message: "rating:safe"
   │
   ▼
4. TelbooruBot.process_autotag_addition()
   │
   └─► UserService.add_auto_tag(user_id, "rating:safe")
       │
       ├─► UserRepository.get_user_settings(user_id)
       │   │
       │   └─► File System: Load user_12345.pkl
       │
       ├─► Add tag to settings.auto_tags
       │
       └─► UserRepository.save_user_settings(user_id, settings)
           │
           └─► File System: Save user_12345.pkl
```

## 🏛️ Layer Responsibilities

### Presentation Layer (TelbooruBot)

**Responsibilities:**
- Handle Telegram events (commands, callbacks, messages)
- Manage UI state (keyboards, menus)
- Format messages for display
- Coordinate user interactions

**Does NOT:**
- Make direct API calls
- Access files directly
- Implement business logic
- Manage data persistence

**Example:**
```python
async def handle_text_input(self, update, context):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Delegate to service layer
    await self.perform_batch_search(update, text, user_id)
```

### Service Layer (BooruService, UserService)

**Responsibilities:**
- Implement business logic
- Apply domain rules
- Orchestrate repository operations
- Transform data for presentation

**Does NOT:**
- Handle HTTP requests
- Access files directly
- Manage UI state
- Format Telegram messages

**Example:**
```python
async def search_posts_with_preferences(self, tags, user_settings, limit):
    # Business logic: Apply user preferences
    modified_tags = self._apply_user_preferences(tags, user_settings)
    
    # Delegate to repository
    return await self.repository.get_posts(
        PostSearchCriteria(tags=modified_tags, limit=limit)
    )
```

### Repository Layer (Repositories)

**Responsibilities:**
- Abstract data access
- Manage connections
- Handle CRUD operations
- Normalize data formats

**Does NOT:**
- Implement business logic
- Format UI messages
- Apply domain rules
- Manage user state

**Example:**
```python
async def get_posts(self, criteria):
    # Data access: Make HTTP request
    params = self._build_params(criteria)
    response = await self._make_request('/index.php', params)
    
    # Normalize response
    return self._normalize_response(response)
```

## 🔌 Dependency Injection

### Constructor Injection

```python
# Service depends on repository interface
class BooruService:
    def __init__(self, repository: IBooruRepository):
        self.repository = repository

# Bot depends on services
class TelbooruBot:
    def __init__(self, telegram_token, api_base_url, api_key, user_id):
        # Create repositories
        self.user_repository = UserRepository()
        self.search_repository = SearchRepository()
        
        # Create services with injected repositories
        self.user_service = UserService(self.user_repository)
```

### Benefits

1. **Testability:** Easy to inject mocks
2. **Flexibility:** Can swap implementations
3. **Decoupling:** Layers don't know about concrete implementations
4. **Maintainability:** Changes isolated to specific layers

## 🎯 Interface Contracts

### IBooruRepository

```python
class IBooruRepository(ABC):
    """Contract for Booru data access"""
    
    @abstractmethod
    async def get_posts(self, criteria: PostSearchCriteria) -> Dict[str, Any]:
        """Get posts matching criteria"""
        pass
    
    @abstractmethod
    async def get_tags(self, criteria: TagSearchCriteria) -> Dict[str, Any]:
        """Get tags matching criteria"""
        pass
```

**Implementations:**
- `BooruRepository` - HTTP API implementation
- `CachedBooruRepository` - With caching layer (example)
- `MockBooruRepository` - For testing

### IUserRepository

```python
class IUserRepository(ABC):
    """Contract for user data access"""
    
    @abstractmethod
    def get_user_settings(self, user_id: int) -> UserSettings:
        """Get user settings"""
        pass
    
    @abstractmethod
    def save_user_settings(self, user_id: int, settings: UserSettings) -> None:
        """Save user settings"""
        pass
```

**Implementations:**
- `UserRepository` - File-based storage
- `DatabaseUserRepository` - Database storage (example)
- `MockUserRepository` - For testing

## 🔄 Request/Response Flow

### Successful Search Request

```
User Input: "cat rating:safe"
    │
    ▼
┌─────────────────────────────────────┐
│ Presentation: handle_text_input()  │
│ • Validate input                    │
│ • Extract user_id                   │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Service: search_posts_with_         │
│          preferences()              │
│ • Get user settings                 │
│ • Apply auto tags                   │
│ • Apply toggle rules                │
│ • Final tags: "cat rating:safe      │
│   score:>50"                        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Repository: get_posts()             │
│ • Build HTTP request                │
│ • Make API call                     │
│ • Handle response                   │
│ • Normalize data                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Data Source: Booru API              │
│ • Process request                   │
│ • Query database                    │
│ • Return JSON                       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Repository: Normalize response      │
│ • Convert to standard format        │
│ • Handle edge cases                 │
│ • Return: {'post': [...]}           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Service: Process results            │
│ • Extract post info                 │
│ • Determine media types             │
│ • Return: List[Dict]                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Presentation: Display results       │
│ • Create media group                │
│ • Build keyboard                    │
│ • Send to Telegram                  │
└─────────────────────────────────────┘
             │
             ▼
User sees: Album of images + selection menu
```

### Error Handling Flow

```
Repository Error
    │
    ▼
┌─────────────────────────────────────┐
│ Repository: Catch exception         │
│ • Log error details                 │
│ • Wrap in RepositoryException       │
│ • Propagate to service              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Service: Handle repository error    │
│ • Log business context              │
│ • Return empty result or default    │
│ • Propagate if critical             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Presentation: Handle service error  │
│ • Log user context                  │
│ • Format user-friendly message      │
│ • Send error message to user        │
└─────────────────────────────────────┘
             │
             ▼
User sees: "❌ An error occurred. Please try again."
```

## 📊 Component Interaction Matrix

| Component | Depends On | Used By | Purpose |
|-----------|-----------|---------|---------|
| TelbooruBot | Services | Telegram | Presentation logic |
| BooruService | BooruRepository | TelbooruBot | Booru business logic |
| UserService | UserRepository | TelbooruBot | User business logic |
| BooruRepository | HTTP Client | BooruService | API data access |
| UserRepository | File System | UserService | User data access |
| SearchRepository | Memory | TelbooruBot | State management |

## 🎨 Design Patterns Used

### 1. Repository Pattern
- Abstracts data access
- Provides consistent interface
- Enables testing with mocks

### 2. Service Layer Pattern
- Encapsulates business logic
- Orchestrates operations
- Provides transaction boundaries

### 3. Dependency Injection
- Loose coupling
- Easy testing
- Flexible configuration

### 4. Strategy Pattern
- Different repository implementations
- Swappable data sources
- Runtime configuration

### 5. Factory Pattern (Implicit)
- Repository creation
- Service instantiation
- Configuration management

## 🔐 Security Architecture

```
┌─────────────────────────────────────┐
│         External Input              │
│      (Telegram Messages)            │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│    Input Validation Layer           │
│  • Sanitize user input              │
│  • Validate message format          │
│  • Check user permissions           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│    Business Logic Layer             │
│  • Apply business rules             │
│  • Enforce constraints              │
│  • Validate operations              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│    Data Access Layer                │
│  • Secure API calls                 │
│  • Encrypted storage                │
│  • Access control                   │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│       Data Storage                  │
│  • File permissions                 │
│  • Secure serialization             │
│  • Audit logging                    │
└─────────────────────────────────────┘
```

## 📈 Scalability Considerations

### Horizontal Scaling

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Bot       │  │   Bot       │  │   Bot       │
│ Instance 1  │  │ Instance 2  │  │ Instance 3  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Shared Storage │
              │   (Database)    │
              └─────────────────┘
```

### Vertical Scaling

```
┌─────────────────────────────────────┐
│         Bot Instance                │
├─────────────────────────────────────┤
│  • Connection pooling               │
│  • Caching layer                    │
│  • Batch operations                 │
│  • Async processing                 │
└─────────────────────────────────────┘
```

## 🎯 Summary

The architecture provides:

1. **Clear Separation:** Each layer has distinct responsibilities
2. **Loose Coupling:** Layers communicate through interfaces
3. **High Cohesion:** Related functionality grouped together
4. **Testability:** Easy to mock and test each layer
5. **Maintainability:** Changes isolated to specific layers
6. **Flexibility:** Easy to swap implementations
7. **Scalability:** Can scale horizontally and vertically

This architecture follows SOLID principles and industry best practices for building maintainable, testable, and scalable applications.