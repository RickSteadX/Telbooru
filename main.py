#!/usr/bin/env python3
"""
Telbooru - Telegram Bot API Wrapper
A web API wrapper utilizing Telegram bot to send images to users.
"""

import asyncio
import aiohttp
import json
import logging
import os
import pickle
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode, quote_plus
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARN
)
logger = logging.getLogger(__name__)


@dataclass
class UserSettings:
    """User-specific settings for the bot."""
    auto_tags: List[str] = field(default_factory=list)  # Tags always applied to searches
    toggle_rules: Dict[str, bool] = field(default_factory=dict)  # Custom toggle rules
    

@dataclass
class SearchState:
    """Current search state for pagination."""
    query: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    current_page: int = 0
    total_pages: int = 0
    posts_per_page: int = 5
    last_menu_message_id: Optional[int] = None  # Track the last menu message to delete it


class UserDataManager:
    """Manages user data persistence."""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def get_user_file_path(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.pkl")
    
    def load_user_settings(self, user_id: int) -> UserSettings:
        """Load user settings from file."""
        file_path = self.get_user_file_path(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load user settings for {user_id}: {e}")
        return UserSettings()
    
    def save_user_settings(self, user_id: int, settings: UserSettings):
        """Save user settings to file."""
        file_path = self.get_user_file_path(user_id)
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(settings, f)
        except Exception as e:
            logger.error(f"Failed to save user settings for {user_id}: {e}")


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown parsing.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Markdown parsing
    """
    if not text:
        return text
    
    # Escape special Markdown characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def escape_markdown_query(text: str) -> str:
    """Escape special characters in search queries for Markdown parsing.
    
    This is a lighter version that only escapes the most problematic characters
    while preserving readable formatting.
    
    Args:
        text: Search query text to escape
        
    Returns:
        Escaped text safe for Markdown parsing
    """
    if not text:
        return text
    
    # Only escape the most problematic characters for queries
    escaped_text = text.replace('_', '\\_')
    escaped_text = escaped_text.replace('*', '\\*')
    escaped_text = escaped_text.replace('[', '\\[')
    escaped_text = escaped_text.replace(']', '\\]')
    
    return escaped_text


def get_media_type(file_url: str) -> str:
    """Determine media type from file URL.
    
    Args:
        file_url: URL of the media file
        
    Returns:
        Media type: 'video', 'gif', or 'image'
    """
    if not file_url:
        return 'image'  # Default fallback
    
    extension = file_url.lower().split('.')[-1] if '.' in file_url else ''
    
    if extension == 'mp4':
        return 'video'
    elif extension == 'gif':
        return 'gif'
    else:
        return 'image'  # jpeg, jpg, png, etc.


def get_preview_url(post: Dict[str, Any]) -> str:
    """Get the best preview URL for a post.
    
    Args:
        post: Post data from API
        
    Returns:
        Preview URL for thumbnails/albums
    """
    # Always use preview_url for thumbnails in albums
    return post.get('preview_url', post.get('file_url', ''))


def get_display_media_url(post: Dict[str, Any]) -> str:
    """Get the best URL for displaying full media.
    
    Args:
        post: Post data from API
        
    Returns:
        URL for full media display
    """
    # For full display, use sample if available for large images, otherwise file_url
    media_type = get_media_type(post.get('file_url', ''))
    
    if media_type in ['video', 'gif']:
        # Videos and GIFs: always use file_url
        return post.get('file_url', '')
    else:
        # Images: prefer sample_url if available, otherwise file_url
        return post.get('sample_url', post.get('file_url', ''))


class BooruAPIWrapper:
    """API wrapper for booru-style image board API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize the API wrapper.
        
        Args:
            base_url: Base URL of the API (e.g., 'https://example.com')
            api_key: API key for authentication
            user_id: User ID for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _build_auth_params(self) -> Dict[str, str]:
        """Build authentication parameters if available."""
        params = {}
        if self.api_key and self.user_id:
            params['api_key'] = self.api_key
            params['user_id'] = self.user_id
        return params
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make an API request.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            JSON response data
            
        Raises:
            aiohttp.ClientError: If request fails
        """
        if not self.session:
            raise RuntimeError("API wrapper not initialized. Use async context manager.")
        
        # Add authentication parameters
        auth_params = self._build_auth_params()
        params.update(auth_params)
        
        # Ensure JSON response (only if not already set)
        if 'json' not in params:
            params['json'] = '1'
        
        # Build URL with query parameters directly
        base_url = f"{self.base_url}{endpoint}"
        
        # Convert parameters to query string with proper encoding
        query_parts = []
        for key, value in params.items():
            if value is not None:  # Skip None values
                # Use quote_plus for proper URL encoding (handles spaces as +, special chars properly)
                encoded_key = quote_plus(str(key))
                encoded_value = quote_plus(str(value))
                query_parts.append(f"{encoded_key}={encoded_value}")
        
        # Build final URL with query string
        if query_parts:
            url = f"{base_url}?{'&'.join(query_parts)}"
        else:
            url = base_url
        
        # Log request details (without sensitive auth info)
        log_params = {k: v for k, v in params.items() if k not in ['api_key', 'user_id']}
        if auth_params:
            log_params['auth'] = 'present'
        
        logger.info(f"🌐 Booru API Request: {endpoint}")
        logger.debug(f"📋 Request URL: {url}")
        logger.debug(f"📝 Request params: {log_params}")
        
        import time
        start_time = time.time()
        
        try:
            # Make request with URL that includes query parameters
            async with self.session.get(url) as response:
                request_duration = time.time() - start_time
                
                logger.info(f"📡 API Response: {response.status} in {request_duration:.2f}s")
                logger.debug(f"📊 Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                
                response_data = await response.json()
                
                # Log response summary
                if isinstance(response_data, dict):
                    if 'post' in response_data:
                        post_count = len(response_data['post']) if isinstance(response_data['post'], list) else 1
                        logger.info(f"✅ Posts retrieved: {post_count}")
                    elif 'tag' in response_data:
                        tag_count = len(response_data['tag']) if isinstance(response_data['tag'], list) else 1
                        logger.info(f"✅ Tags retrieved: {tag_count}")
                    elif 'user' in response_data:
                        user_count = len(response_data['user']) if isinstance(response_data['user'], list) else 1
                        logger.info(f"✅ Users retrieved: {user_count}")
                    elif 'comment' in response_data:
                        comment_count = len(response_data['comment']) if isinstance(response_data['comment'], list) else 1
                        logger.info(f"✅ Comments retrieved: {comment_count}")
                    else:
                        logger.info(f"✅ Response received: {len(str(response_data))} chars")
                else:
                    logger.info(f"✅ Response received: {type(response_data).__name__}")
                
                return response_data
                
        except aiohttp.ClientResponseError as e:
            request_duration = time.time() - start_time
            logger.error(f"❌ HTTP Error {e.status}: {e.message} (after {request_duration:.2f}s)")
            logger.error(f"🔗 Failed URL: {url}")
            logger.error(f"📝 Request params: {log_params}")
            raise
        except aiohttp.ClientConnectionError as e:
            request_duration = time.time() - start_time
            logger.error(f"🔌 Connection Error: {e} (after {request_duration:.2f}s)")
            logger.error(f"🔗 Failed URL: {url}")
            raise
        except asyncio.TimeoutError as e:
            request_duration = time.time() - start_time
            logger.error(f"⏰ Timeout Error: {e} (after {request_duration:.2f}s)")
            logger.error(f"🔗 Failed URL: {url}")
            raise
        except Exception as e:
            request_duration = time.time() - start_time
            logger.error(f"💥 Unexpected Error: {type(e).__name__}: {e} (after {request_duration:.2f}s)")
            logger.error(f"🔗 Failed URL: {url}")
            logger.error(f"📝 Request params: {log_params}")
            raise
    
    async def get_posts(self, 
                       limit: int = 20, 
                       pid: int = 0, 
                       tags: str = "", 
                       cid: Optional[int] = None,
                       post_id: Optional[int] = None) -> Dict[str, Any]:
        """Get posts from the API.
        
        Args:
            limit: Number of posts to retrieve (max 100)
            pid: Page number
            tags: Tags to search for
            cid: Change ID of the post
            post_id: Specific post ID
            
        Returns:
            API response containing posts
        """
        logger.info(f"🖼️ Getting posts: limit={limit}, pid={pid}, tags='{tags}', cid={cid}, post_id={post_id}")
        
        # Use correct Gelbooru DAPI format
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'limit': min(limit, 100),
            'pid': pid,
            'json': '1'  # Ensure JSON response
        }
        
        if tags:
            # quote_plus will handle space-to-plus conversion and other special characters
            params['tags'] = tags
        if cid is not None:
            params['cid'] = cid
        if post_id is not None:
            params['id'] = post_id
            
        try:
            result = await self._make_request('/index.php', params)
            
            # Handle different response formats
            if result is None:
                logger.warning("⚠️ Received null response from API")
                return {'post': []}
            
            # Some booru APIs return the posts directly in an array
            if isinstance(result, list):
                return {'post': result}
            
            # Standard format should have 'post' key
            if not isinstance(result, dict):
                logger.warning(f"⚠️ Unexpected response format: {type(result)}")
                return {'post': []}
                
            # If no 'post' key but has 'posts', use that
            if 'post' not in result and 'posts' in result:
                result['post'] = result['posts']
                
            return result
            
        except Exception as e:
            logger.error(f"🚨 Failed to get posts: {e}")
            # Try fallback format for different booru implementations
            logger.info("🔄 Trying alternative API format...")
            
            # Alternative format (some booru sites use different parameters)
            alt_params = {
                'page': 'post',
                's': 'list',
                'limit': min(limit, 100),
                'pid': pid,
                'json': '1'
            }
            
            if tags:
                alt_params['tags'] = tags
            if post_id is not None:
                alt_params['id'] = post_id
                
            try:
                alt_result = await self._make_request('/index.php', alt_params)
                logger.info("✅ Alternative format succeeded")
                return alt_result if alt_result else {'post': []}
            except Exception as alt_e:
                logger.error(f"🚨 Alternative format also failed: {alt_e}")
                return {'post': []}
    
    async def get_tags(self, 
                      limit: int = 100,
                      after_id: Optional[int] = None,
                      name: Optional[str] = None,
                      names: Optional[str] = None,
                      tags: Optional[str] = None,
                      order: str = 'ASC',
                      orderby: str = 'name') -> Dict[str, Any]:
        """Get tags from the API.
        
        Args:
            limit: Number of tags to retrieve
            after_id: Get tags with ID greater than this value
            name: Find tag by exact name
            names: Multiple tag names separated by spaces
            tags: Wildcard search pattern
            order: Sort order (ASC or DESC)
            orderby: Field to order by (date, count, name)
            
        Returns:
            API response containing tags
        """
        logger.info(f"🏷️ Getting tags: limit={limit}, tags='{tags}', name='{name}'")
        
        params = {
            'page': 'dapi',
            's': 'tag',
            'q': 'index',
            'limit': limit,
            'order': order,
            'orderby': orderby,
            'json': '1'
        }
        
        if after_id is not None:
            params['after_id'] = after_id
        if name:
            params['name'] = name
        if names:
            params['names'] = names
        if tags:
            params['tags'] = tags
            
        try:
            result = await self._make_request('/index.php', params)
            
            # Handle different response formats
            if result is None:
                logger.warning("⚠️ Received null response from tags API")
                return {'tag': []}
            
            # Some booru APIs return the tags directly in an array
            if isinstance(result, list):
                return {'tag': result}
            
            # Standard format should have 'tag' key
            if not isinstance(result, dict):
                logger.warning(f"⚠️ Unexpected tags response format: {type(result)}")
                return {'tag': []}
                
            # If no 'tag' key but has 'tags', use that
            if 'tag' not in result and 'tags' in result:
                result['tag'] = result['tags']
                
            return result
            
        except Exception as e:
            logger.error(f"🚨 Failed to get tags: {e}")
            return {'tag': []}
    
    async def get_users(self, 
                       limit: int = 100,
                       pid: int = 0,
                       name: Optional[str] = None,
                       tags: Optional[str] = None) -> Dict[str, Any]:
        """Get users from the API.
        
        Args:
            limit: Number of users to retrieve
            pid: Page number
            name: Username to search for
            tags: Username wildcard pattern
            
        Returns:
            API response containing users
        """
        params = {
            'page': 'dapi',
            's': 'user',
            'q': 'index',
            'limit': limit,
            'pid': pid
        }
        
        if name:
            params['name'] = name
        if tags:
            params['tags'] = tags
            
        return await self._make_request('/index.php', params)
    
    async def get_comments(self, post_id: int) -> Dict[str, Any]:
        """Get comments for a specific post.
        
        Args:
            post_id: Post ID to get comments for
            
        Returns:
            API response containing comments
        """
        params = {
            'page': 'dapi',
            's': 'comment',
            'q': 'index',
            'post_id': post_id
        }
        
        return await self._make_request('/index.php', params)
    
    async def get_deleted_images(self, last_id: Optional[int] = None) -> Dict[str, Any]:
        """Get deleted images.
        
        Args:
            last_id: Return everything above this number
            
        Returns:
            API response containing deleted images
        """
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'deleted': 'show'
        }
        
        if last_id is not None:
            params['last_id'] = str(last_id)
            
        return await self._make_request('/index.php', params)


class TelbooruBot:
    """Telegram bot for sending images from booru API."""
    
    def __init__(self, telegram_token: str, api_base_url: str, 
                 api_key: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize the Telegram bot.
        
        Args:
            telegram_token: Telegram bot token
            api_base_url: Base URL of the booru API
            api_key: API key for authentication
            user_id: User ID for authentication
        """
        self.bot = Bot(token=telegram_token)
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.user_id = user_id
        self.application = None
        self.user_data_manager = UserDataManager()
        self.search_states: Dict[int, SearchState] = {}  # user_id -> SearchState
        self.user_states: Dict[int, str] = {}  # user_id -> current_state (for auto-tag addition)
    
    def setup_handlers(self):
        """Setup command and message handlers."""
        self.application = Application.builder().token(self.bot.token).build()
        
        logger.info("Setting up bot handlers...")
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        logger.info("Added start command handler")
        
        self.application.add_handler(CommandHandler("tags", self.tags_command))
        logger.info("Added tags command handler")
        
        # Callback query handler for menu navigation
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        logger.info("Added callback query handler")
        
        # Message handler for text searches (when in search mode)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input)
        )
        logger.info("Added text message handler")
        
        logger.info("All handlers setup complete")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - show main menu."""
        logger.info(f"Start command received from user: {update.effective_user}")
        
        if not update.message:
            logger.warning("No message in update")
            return
            
        keyboard = [
            [InlineKeyboardButton("🔍 Search Images", callback_data="menu_search")],
            [InlineKeyboardButton("🎲 Random Image", callback_data="menu_random")],
            [InlineKeyboardButton("🏷️ Browse Tags", callback_data="menu_tags")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🎨 <b>Welcome to Telbooru Bot!</b>\n\n"
            "I can help you search and view images from the booru.\n\n"
            "<b>Quick Start:</b>\n"
            "• Send me any text to search for images\n"
            "• Use /tags command to search for tags\n"
            "• Or use the menu below for more options\n\n"
            "<b>Examples:</b>\n"
            "• <code>cat girl rating:safe</code> - Search images\n"
            "• <code>/tags school</code> - Find tags containing 'school'"
        )
        
        logger.info("Sending welcome message with inline keyboard")
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        logger.info("Welcome message sent successfully")
    
    async def tags_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tags command - search for tags."""
        logger.info(f"Tags command received from user: {update.effective_user}")
        
        if not update.message:
            logger.warning("No message in update")
            return
        
        # Check if user provided query with the command
        query = None
        if context.args:
            query = ' '.join(context.args)
        
        if query:
            # User provided a query, search for tags immediately
            await self.search_and_send_tags(update, query)
        else:
            # No query provided, show usage instructions
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            usage_text = (
                "🏷️ <b>Tag Search</b>\n\n"
                "Use this command to search for tags:\n"
                "<code>/tags your_search_term</code>\n\n"
                "<b>Examples:</b>\n"
                "• <code>/tags school</code> - Find tags containing 'school'\n"
                "• <code>/tags uniform</code> - Find tags containing 'uniform'\n"
                "• <code>/tags cat*</code> - Find tags starting with 'cat'\n\n"
                "<b>Note:</b> Regular text messages are used for image searches."
            )
            
            await update.message.reply_text(
                usage_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        # Add debug logging
        logger.info(f"Callback query received: {update}")
        
        query = update.callback_query
        if not query:
            logger.warning("No callback query in update")
            return
            
        if not query.data:
            logger.warning("No data in callback query")
            return
            
        logger.info(f"Processing callback data: {query.data}")
        
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"User {user_id} triggered callback: {data}")
        
        # Clear any pending user states when navigating to main sections
        if data in ["menu_search", "menu_random", "menu_tags", "menu_settings", "back_main"]:
            self.user_states.pop(user_id, None)
        
        if data == "menu_search":
            await self.show_search_prompt(query)
        elif data == "menu_random":
            await self.handle_random_search(query)
        elif data == "menu_tags":
            await self.show_tags_prompt(query)
        elif data == "menu_settings":
            await self.show_settings_menu(query)
        elif data == "back_main":
            await self.show_main_menu(query)
        elif data.startswith("search_page_"):
            page = int(data.split("_")[-1])
            await self.show_search_page(query, user_id, page)
        elif data.startswith("post_"):
            post_index = int(data.split("_")[1])
            await self.send_full_image(query, user_id, post_index)
        elif data.startswith("settings_"):
            await self.handle_settings_callback(query, data)
        elif data.startswith("toggle_"):
            await self.handle_toggle_callback(query, data)
        elif data.startswith("autotag_"):
            await self.handle_autotag_callback(query, data)
        else:
            logger.warning(f"Unhandled callback data: {data}")
    
    async def show_main_menu(self, query):
        """Show the main menu."""
        keyboard = [
            [InlineKeyboardButton("🔍 Search Images", callback_data="menu_search")],
            [InlineKeyboardButton("🎲 Random Image", callback_data="menu_random")],
            [InlineKeyboardButton("🏷️ Browse Tags", callback_data="menu_tags")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🎨 <b>Telbooru Bot Main Menu</b>\n\n"
            "Choose an option from the menu below:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_search_prompt(self, query):
        """Show search prompt."""
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🔍 <b>Search Images</b>\n\n"
            "Send me tags to search for images.\n"
            "Example: <code>cat girl rating:safe</code>\n\n"
            "<b>Available operators:</b>\n"
            "• <code>rating:safe</code> - Safe images only\n"
            "• <code>score:>100</code> - High-scored images\n"
            "• <code>-tag</code> - Exclude a tag\n\n"
            "<b>Note:</b> To search for tags instead of images, use <code>/tags</code> command."
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_tags_prompt(self, query):
        """Show tags search prompt."""
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🏷️ <b>Browse Tags</b>\n\n"
            "Use the /tags command to search for tags:\n"
            "<code>/tags your_search_term</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/tags school</code> - Find tags containing 'school'\n"
            "• <code>/tags uniform</code> - Find tags containing 'uniform'\n"
            "• <code>/tags cat*</code> - Find tags starting with 'cat'\n\n"
            "<b>Note:</b> Regular text messages search for images, not tags."
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_settings_menu(self, query):
        """Show settings menu."""
        user_id = query.from_user.id
        settings = self.user_data_manager.load_user_settings(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🏷️ Manage Auto Tags", callback_data="settings_autotags")],
            [InlineKeyboardButton("🔄 Toggle Rules", callback_data="settings_toggles")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        auto_tags_text = ", ".join(settings.auto_tags) if settings.auto_tags else "None"
        toggle_rules_text = f"{len(settings.toggle_rules)} rules" if settings.toggle_rules else "None"
        
        text = (
            "⚙️ <b>Settings Menu</b>\n\n"
            f"<b>Auto Tags:</b> {auto_tags_text}\n"
            f"<b>Toggle Rules:</b> {toggle_rules_text}\n\n"
            "Choose a setting to modify:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input - check for auto-tag addition or treat as post search."""
        if not update.message or not update.message.text or not update.message.from_user:
            return
            
        user_id = update.message.from_user.id
        text = update.message.text.strip()
        
        # Check if user is in auto-tag addition state
        if self.user_states.get(user_id) == "WAITING_FOR_AUTOTAG":
            await self.process_autotag_addition(update, text, user_id)
            return
        
        # All other text input is treated as post search
        # Use /tags command for tag searches
        await self.perform_batch_search(update, text, user_id)
    
    async def process_autotag_addition(self, update: Update, tag_text: str, user_id: int):
        """Process auto-tag addition from user input."""
        # Clear the waiting state
        self.user_states.pop(user_id, None)
        
        # Validate tag text
        tag_text = tag_text.strip()
        if not tag_text:
            await update.message.reply_text(
                "❌ Invalid tag. Please enter a valid tag name.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
                ])
            )
            return
        
        # Load current settings
        settings = self.user_data_manager.load_user_settings(user_id)
        
        # Check if tag already exists
        if tag_text in settings.auto_tags:
            await update.message.reply_text(
                f"❌ Tag '{tag_text}' is already in your auto tags.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
                ])
            )
            return
        
        # Add the tag
        settings.auto_tags.append(tag_text)
        self.user_data_manager.save_user_settings(user_id, settings)
        
        # Send confirmation
        await update.message.reply_text(
            f"✅ Successfully added auto tag: '{tag_text}'",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
            ])
        )
    
    async def handle_random_search(self, query):
        """Handle random image request."""
        user_id = query.from_user.id
        await self.perform_batch_search_callback(query, "", user_id)
    
    async def perform_batch_search(self, update: Update, tags: str, user_id: int):
        """Perform batch search and display results with pagination."""
        if not update.message:
            return
            
        try:
            # Send "typing" action
            await update.message.chat.send_action(action="upload_photo")
            
            # Apply auto tags and toggle rules
            settings = self.user_data_manager.load_user_settings(user_id)
            
            # Apply auto tags
            if settings.auto_tags:
                auto_tags_str = " ".join(settings.auto_tags)
                tags = f"{tags} {auto_tags_str}" if tags else auto_tags_str
            
            # Apply enabled toggle rules
            enabled_toggles = [rule for rule, enabled in settings.toggle_rules.items() if enabled]
            if enabled_toggles:
                toggle_str = " ".join(enabled_toggles)
                tags = f"{tags} {toggle_str}" if tags else toggle_str
            
            async with BooruAPIWrapper(self.api_base_url, self.api_key, self.user_id) as api:
                # Search for posts (get more than 5 to allow pagination)
                logger.info(f"🔍 Starting search with final tags: '{tags}'")
                response = await api.get_posts(limit=50, tags=tags)
                
                logger.debug(f"📊 Search response type: {type(response)}, keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
                
                if not response:
                    logger.warning("⚠️ Empty response from API")
                    await update.message.reply_text(
                        "😔 No response from the image API.\n"
                        "The server might be temporarily unavailable. Please try again later."
                    )
                    return
                    
                if 'post' not in response:
                    logger.warning(f"⚠️ No 'post' key in response. Available keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                    await update.message.reply_text(
                        "😔 Invalid response format from the API.\n"
                        "Please try again or contact support if this persists."
                    )
                    return
                    
                if not response['post']:
                    logger.info(f"💭 No posts found for tags: '{tags}'")
                    await update.message.reply_text(
                        "😔 No images found for the given tags.\n"
                        "Try different tags or check your spelling.\n\n"
                        f"🎯 Search terms used: <code>{tags}</code>",
                        parse_mode='HTML'
                    )
                    return
                
                posts = response['post']
                if isinstance(posts, dict):
                    posts = [posts]  # Single post returned as dict
                
                # Store search state
                search_state = SearchState(
                    query=tags,
                    results=posts,
                    current_page=0,
                    total_pages=(len(posts) - 1) // 5 + 1
                )
                self.search_states[user_id] = search_state
                
                # Show first page
                await self.send_search_results_page(update.message, user_id, 0)
                
        except Exception as e:
            logger.error(f"Error in perform_batch_search: {e}")
            await update.message.reply_text(
                "❌ An error occurred while searching for images.\n"
                "Please try again later."
            )
    
    async def perform_batch_search_callback(self, query, tags: str, user_id: int):
        """Perform batch search from callback query."""
        try:
            # Apply auto tags and toggle rules
            settings = self.user_data_manager.load_user_settings(user_id)
            
            # Apply auto tags
            if settings.auto_tags:
                auto_tags_str = " ".join(settings.auto_tags)
                tags = f"{tags} {auto_tags_str}" if tags else auto_tags_str
            
            # Apply enabled toggle rules
            enabled_toggles = [rule for rule, enabled in settings.toggle_rules.items() if enabled]
            if enabled_toggles:
                toggle_str = " ".join(enabled_toggles)
                tags = f"{tags} {toggle_str}" if tags else toggle_str
            
            async with BooruAPIWrapper(self.api_base_url, self.api_key, self.user_id) as api:
                logger.info(f"🔍 Starting callback search with final tags: '{tags}'")
                response = await api.get_posts(limit=50, tags=tags)
                
                logger.debug(f"📊 Callback search response type: {type(response)}, keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
                
                if not response:
                    logger.warning("⚠️ Empty response from API (callback)")
                    await query.edit_message_text(
                        "😔 No response from the image API.\n"
                        "The server might be temporarily unavailable. Please try again later."
                    )
                    return
                    
                if 'post' not in response:
                    logger.warning(f"⚠️ No 'post' key in callback response. Available keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                    await query.edit_message_text(
                        "😔 Invalid response format from the API.\n"
                        "Please try again or contact support if this persists."
                    )
                    return
                    
                if not response['post']:
                    logger.info(f"💭 No posts found for callback tags: '{tags}'")
                    await query.edit_message_text(
                        "😔 No images found for the given tags.\n"
                        "Try different tags or check your spelling.\n\n"
                        f"🎯 Search terms used: <code>{tags}</code>",
                        parse_mode='HTML'
                    )
                    return
                
                posts = response['post']
                if isinstance(posts, dict):
                    posts = [posts]
                
                # Store search state
                search_state = SearchState(
                    query=tags,
                    results=posts,
                    current_page=0,
                    total_pages=(len(posts) - 1) // 5 + 1
                )
                self.search_states[user_id] = search_state
                
                # Show first page
                await self.send_search_results_page_callback(query, user_id, 0)
                
        except Exception as e:
            logger.error(f"Error in perform_batch_search_callback: {e}")
            await query.edit_message_text(
                "❌ An error occurred while searching for images.\n"
                "Please try again later."
            )
    
    async def send_search_results_page(self, message, user_id: int, page: int):
        """Send a page of search results as an album of preview images."""
        search_state = self.search_states.get(user_id)
        if not search_state:
            await message.reply_text("No active search. Please start a new search.")
            return
        
        start_idx = page * search_state.posts_per_page
        end_idx = min(start_idx + search_state.posts_per_page, len(search_state.results))
        page_posts = search_state.results[start_idx:end_idx]
        
        try:
            # Create media group for album
            media_group = []
            for i, post in enumerate(page_posts):
                preview_url = get_preview_url(post)
                if not preview_url:
                    continue
                    
                # Create caption for first image with search info
                if i == 0:
                    caption = f"🖼️ <b>Search Results</b> (Page {page + 1}/{search_state.total_pages})\n"
                    if search_state.query:
                        # No escaping needed for HTML
                        caption += f"<b>Query:</b> {search_state.query}\n"
                    caption += f"<b>Results:</b> {len(page_posts)} posts"
                else:
                    caption = None
                    
                media_group.append(InputMediaPhoto(
                    media=preview_url,
                    caption=caption,
                    parse_mode='HTML' if caption else None
                ))
            
            # Send album if we have media
            if media_group:
                await message.reply_media_group(media_group)
            
            # Create inline keyboard for post selection with order numbers
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1  # 1-based ordering
                media_type = get_media_type(post.get('file_url', ''))
                
                # Choose appropriate emoji based on media type
                if media_type == 'video':
                    emoji = "🎬"
                elif media_type == 'gif':
                    emoji = "🎭"
                else:
                    emoji = "🖼️"
                    
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} #{post_order}",
                    callback_data=f"post_{start_idx + i}"
                )])
            
            # Add navigation buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"search_page_{page - 1}"
                ))
            if page < search_state.total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"search_page_{page + 1}"
                ))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send keyboard as separate message and store its ID
            keyboard_text = "🎯 Select a post to view:"
            menu_message = await message.reply_text(
                keyboard_text,
                reply_markup=reply_markup
            )
            
            # Store the menu message ID for future reference
            search_state.last_menu_message_id = menu_message.message_id
            
        except Exception as e:
            logger.error(f"Error sending search results album: {e}")
            # Fallback to text-based display
            await self._send_text_fallback_results(message, user_id, page)
    
    async def _send_text_fallback_results(self, message, user_id: int, page: int):
        """Fallback method to send text-based results if album fails."""
        search_state = self.search_states.get(user_id)
        if not search_state:
            return
            
        start_idx = page * search_state.posts_per_page
        end_idx = min(start_idx + search_state.posts_per_page, len(search_state.results))
        page_posts = search_state.results[start_idx:end_idx]
        
        # Create inline keyboard for post selection with order numbers
        keyboard = []
        for i, post in enumerate(page_posts):
            post_order = start_idx + i + 1  # 1-based ordering
            media_type = get_media_type(post.get('file_url', ''))
            
            # Choose appropriate emoji based on media type
            if media_type == 'video':
                emoji = "🎬"
            elif media_type == 'gif':
                emoji = "🎭"
            else:
                emoji = "🖼️"
                
            keyboard.append([InlineKeyboardButton(
                f"{emoji} #{post_order}",
                callback_data=f"post_{start_idx + i}"
            )])
        
        # Add navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"search_page_{page - 1}"
            ))
        if page < search_state.total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"search_page_{page + 1}"
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Create preview text
        preview_text = f"🖼️ **Search Results** (Page {page + 1}/{search_state.total_pages})\n\n"
        
        if search_state.query:
            # Escape query for Markdown
            escaped_query = escape_markdown_query(search_state.query)
            preview_text += f"**Query:** {escaped_query}\n\n"
        
        for i, post in enumerate(page_posts):
            post_order = start_idx + i + 1
            width = post.get('width', 'Unknown')
            height = post.get('height', 'Unknown')
            score = post.get('score', 'Unknown')
            media_type = get_media_type(post.get('file_url', ''))
            
            if media_type == 'video':
                type_icon = "🎬"
            elif media_type == 'gif':
                type_icon = "🎭"
            else:
                type_icon = "🖼️"
            
            preview_text += (
                f"**#{post_order}. {type_icon} {media_type.title()}**\n"
                f"📊 Size: {width}x{height} | Score: {score}\n\n"
            )
        
        await message.reply_text(
            preview_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def send_search_results_page_callback(self, query, user_id: int, page: int):
        """Send a page of search results via callback query with fresh album previews."""
        search_state = self.search_states.get(user_id)
        if not search_state:
            await query.edit_message_text("No active search. Please start a new search.")
            return
        
        start_idx = page * search_state.posts_per_page
        end_idx = min(start_idx + search_state.posts_per_page, len(search_state.results))
        page_posts = search_state.results[start_idx:end_idx]
        
        try:
            # Delete the old menu message
            await query.message.delete()
            
            # Create media group for album
            media_group = []
            for i, post in enumerate(page_posts):
                preview_url = get_preview_url(post)
                if not preview_url:
                    continue
                    
                # Create caption for first image with search info
                if i == 0:
                    caption = f"🖼️ <b>Search Results</b> (Page {page + 1}/{search_state.total_pages})\n"
                    if search_state.query:
                        # No escaping needed for HTML
                        caption += f"<b>Query:</b> {search_state.query}\n"
                    caption += f"<b>Results:</b> {len(page_posts)} posts"
                else:
                    caption = None
                    
                media_group.append(InputMediaPhoto(
                    media=preview_url,
                    caption=caption,
                    parse_mode='HTML' if caption else None
                ))
            
            # Send album if we have media
            if media_group:
                await query.message.chat.send_media_group(media_group)
            
            # Create inline keyboard for post selection with order numbers
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1  # 1-based ordering
                media_type = get_media_type(post.get('file_url', ''))
                
                # Choose appropriate emoji based on media type
                if media_type == 'video':
                    emoji = "🎬"
                elif media_type == 'gif':
                    emoji = "🎭"
                else:
                    emoji = "🖼️"
                    
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} #{post_order}",
                    callback_data=f"post_{start_idx + i}"
                )])
            
            # Add navigation buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"search_page_{page - 1}"
                ))
            if page < search_state.total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"search_page_{page + 1}"
                ))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send fresh menu message
            menu_text = f"🎯 Select a post to view: (Page {page + 1}/{search_state.total_pages})"
            new_menu = await query.message.chat.send_message(
                menu_text,
                reply_markup=reply_markup
            )
            
            # Update the stored menu message ID
            search_state.last_menu_message_id = new_menu.message_id
            
        except Exception as e:
            logger.error(f"Error sending search results page: {e}")
            await query.answer("Failed to update results. Please try a new search.")
    
    async def show_search_page(self, query, user_id: int, page: int):
        """Show a specific search page."""
        search_state = self.search_states.get(user_id)
        if search_state:
            search_state.current_page = page
        await self.send_search_results_page_callback(query, user_id, page)
    
    async def send_full_image(self, query, user_id: int, post_index: int):
        """Send the full media for a selected post (image/video/gif)."""
        search_state = self.search_states.get(user_id)
        if not search_state or post_index >= len(search_state.results):
            await query.answer("Media not found.")
            return
        
        post = search_state.results[post_index]
        media_url = get_display_media_url(post)
        media_type = get_media_type(post.get('file_url', ''))
        
        # Add debug logging
        logger.info(f"🎯 send_full_image debug:")
        logger.info(f"   Post index: {post_index}")
        logger.info(f"   File URL: {post.get('file_url', 'N/A')}")
        logger.info(f"   Media type detected: {media_type}")
        logger.info(f"   Media URL to send: {media_url}")
        
        if not media_url:
            await query.answer("Media URL not available.")
            return
        
        try:
            # Extract media info
            media_id = post.get('id', 'Unknown')
            width = post.get('width', 'Unknown')
            height = post.get('height', 'Unknown')
            tags_list = post.get('tags', '').strip()
            score = post.get('score', 'Unknown')
            
            # Determine display order from search state
            display_order = post_index + 1
            
            # Create appropriate emoji and type label
            if media_type == 'video':
                type_emoji = "🎬"
                type_label = "Video"
            elif media_type == 'gif':
                type_emoji = "🎭"
                type_label = "Animation"
            else:
                type_emoji = "🖼️"
                type_label = "Image"
            
            caption = (
                f"{type_emoji} **{type_label} #{display_order}** (ID: {media_id})\n"
                f"📊 **Size:** {width}x{height}\n"
                f"⭐ **Score:** {score}\n"
                f"🏷️ **Tags:** {escape_markdown(tags_list[:500])}{'...' if len(tags_list) > 500 else ''}"
            )
            
            # Send media based on type with debug logging
            if media_type == 'video':
                logger.info(f"🎬 Sending video using reply_video()")
                try:
                    await query.message.reply_video(
                        video=media_url,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                    await query.answer(f"{type_label} sent!")
                except TelegramError as e:
                    logger.warning(f"Failed to send video {media_url}: {e}")
                    # Fallback to document if video fails
                    try:
                        await query.message.reply_document(
                            document=media_url,
                            caption=f"{type_emoji} Video file (ID: {media_id})",
                            parse_mode='Markdown'
                        )
                        await query.answer("Video sent as file!")
                    except TelegramError as e2:
                        logger.error(f"Failed to send video as document {media_url}: {e2}")
                        await query.answer("Failed to send video. It might be too large or in an unsupported format.")
                        
            elif media_type == 'gif':
                logger.info(f"🎭 Sending GIF using reply_animation()")
                try:
                    await query.message.reply_animation(
                        animation=media_url,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                    await query.answer(f"{type_label} sent!")
                except TelegramError as e:
                    logger.warning(f"Failed to send animation {media_url}: {e}")
                    # Fallback to document if animation fails
                    try:
                        await query.message.reply_document(
                            document=media_url,
                            caption=f"{type_emoji} Animation file (ID: {media_id})",
                            parse_mode='Markdown'
                        )
                        await query.answer("Animation sent as file!")
                    except TelegramError as e2:
                        logger.error(f"Failed to send animation as document {media_url}: {e2}")
                        await query.answer("Failed to send animation. It might be too large or in an unsupported format.")
                        
            else:  # Image
                logger.info(f"🖼️ Sending image using reply_photo()")
                try:
                    await query.message.reply_photo(
                        photo=media_url,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                    await query.answer(f"{type_label} sent!")
                except TelegramError as e:
                    logger.warning(f"Failed to send image {media_url}: {e}")
                    # Fallback to document if image fails
                    try:
                        await query.message.reply_document(
                            document=media_url,
                            caption=f"{type_emoji} Image file (ID: {media_id})",
                            parse_mode='Markdown'
                        )
                        await query.answer("Image sent as file!")
                    except TelegramError as e2:
                        logger.error(f"Failed to send image as document {media_url}: {e2}")
                        await query.answer("Failed to send image. It might be too large or in an unsupported format.")
            
            # After sending media, re-send the selection menu at the bottom
            await self._resend_selection_menu(query, user_id, search_state)
            
        except Exception as e:
            logger.error(f"Unexpected error in send_full_image: {e}")
            await query.answer("An unexpected error occurred while sending the media.")
    
    async def _resend_selection_menu(self, query, user_id: int, search_state: SearchState):
        """Send a fresh selection menu at the bottom after viewing media."""
        try:
            current_page = search_state.current_page
            start_idx = current_page * search_state.posts_per_page
            end_idx = min(start_idx + search_state.posts_per_page, len(search_state.results))
            page_posts = search_state.results[start_idx:end_idx]
            
            # Create inline keyboard for post selection with order numbers
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1  # 1-based ordering
                media_type = get_media_type(post.get('file_url', ''))
                
                # Choose appropriate emoji based on media type
                if media_type == 'video':
                    emoji = "🎬"
                elif media_type == 'gif':
                    emoji = "🎭"
                else:
                    emoji = "🖼️"
                    
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} #{post_order}",
                    callback_data=f"post_{start_idx + i}"
                )])
            
            # Add navigation buttons
            nav_buttons = []
            if current_page > 0:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"search_page_{current_page - 1}"
                ))
            if current_page < search_state.total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"search_page_{current_page + 1}"
                ))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send fresh menu at the bottom
            menu_text = f"🎯 Select another post: (Page {current_page + 1}/{search_state.total_pages})"
            new_menu = await query.message.chat.send_message(
                menu_text,
                reply_markup=reply_markup
            )
            
            # Update the stored menu message ID
            search_state.last_menu_message_id = new_menu.message_id
            
        except Exception as e:
            logger.error(f"Error sending fresh selection menu: {e}")
    
    async def handle_settings_callback(self, query, data: str):
        """Handle settings-related callbacks."""
        user_id = query.from_user.id
        
        if data == "settings_autotags":
            await self.show_autotags_settings(query, user_id)
        elif data == "settings_toggles":
            await self.show_toggle_settings(query, user_id)
        """Handle settings-related callbacks."""
        user_id = query.from_user.id
        
        if data == "settings_autotags":
            await self.show_autotags_settings(query, user_id)
        elif data == "settings_toggles":
            await self.show_toggle_settings(query, user_id)
    
    async def show_autotags_settings(self, query, user_id: int):
        """Show auto tags settings menu."""
        settings = self.user_data_manager.load_user_settings(user_id)
        
        keyboard = []
        
        if settings.auto_tags:
            for i, tag in enumerate(settings.auto_tags):
                keyboard.append([InlineKeyboardButton(
                    f"❌ Remove: {tag}",
                    callback_data=f"autotag_remove_{i}"
                )])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Add New Auto Tag", callback_data="autotag_add")],
            [InlineKeyboardButton("⬅️ Back to Settings", callback_data="menu_settings")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        auto_tags_list = "\n".join([f"\u2022 {tag}" for tag in settings.auto_tags]) if settings.auto_tags else "No auto tags set."
        
        text = (
            "🏷️ <b>Auto Tags Settings</b>\n\n"
            "Auto tags are automatically added to all your searches.\n\n"
            f"<b>Current auto tags:</b>\n{auto_tags_list}\n\n"
            "Use the buttons below to manage your auto tags:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_toggle_settings(self, query, user_id: int):
        """Show toggle rules settings menu."""
        settings = self.user_data_manager.load_user_settings(user_id)
        
        # Common toggle rules
        common_toggles = [
            ("rating:safe", "Safe content only"),
            ("rating:questionable", "Questionable content"),
            ("rating:explicit", "Explicit content"),
            ("score:>100", "High quality (score > 100)"),
            ("sort:score", "Sort by score")
        ]
        
        keyboard = []
        
        for rule, description in common_toggles:
            is_enabled = settings.toggle_rules.get(rule, False)
            status = "✅" if is_enabled else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status} {description}",
                callback_data=f"toggle_{rule.replace(':', '_COLON_').replace('>', '_GT_')}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="menu_settings")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        enabled_rules = [rule for rule, enabled in settings.toggle_rules.items() if enabled]
        enabled_text = "\n".join([f"\u2022 {rule}" for rule in enabled_rules]) if enabled_rules else "No rules enabled."
        
        text = (
            "🔄 <b>Toggle Rules Settings</b>\n\n"
            "Toggle rules are search modifiers that can be enabled or disabled.\n\n"
            f"<b>Currently enabled:</b>\n{enabled_text}\n\n"
            "Click the buttons below to toggle rules on/off:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def handle_toggle_callback(self, query, data: str):
        """Handle toggle rule callbacks."""
        user_id = query.from_user.id
        settings = self.user_data_manager.load_user_settings(user_id)
        
        # Parse the rule from callback data
        rule = data.replace("toggle_", "").replace("_COLON_", ":").replace("_GT_", ">")
        
        # Toggle the rule
        current_state = settings.toggle_rules.get(rule, False)
        settings.toggle_rules[rule] = not current_state
        
        # Save settings
        self.user_data_manager.save_user_settings(user_id, settings)
        
        await query.answer(f"Toggled {rule}: {'ON' if not current_state else 'OFF'}")
        
        # Refresh the toggle settings menu
        await self.show_toggle_settings(query, user_id)
    
    async def handle_autotag_callback(self, query, data: str):
        """Handle auto tag callbacks."""
        user_id = query.from_user.id
        settings = self.user_data_manager.load_user_settings(user_id)
        
        if data.startswith("autotag_remove_"):
            index = int(data.split("_")[-1])
            if 0 <= index < len(settings.auto_tags):
                removed_tag = settings.auto_tags.pop(index)
                self.user_data_manager.save_user_settings(user_id, settings)
                await query.answer(f"Removed auto tag: {removed_tag}")
                await self.show_autotags_settings(query, user_id)
        elif data == "autotag_add":
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = (
                "➕ <b>Add New Auto Tag</b>\n\n"
                "Send me the tag you want to add as an auto tag.\n"
                "Example: <code>rating:safe</code> or <code>school_uniform</code>\n\n"
                "The tag will be automatically added to all your future searches."
            )
            
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            # Set user state to waiting for auto tag
            self.user_states[user_id] = "WAITING_FOR_AUTOTAG"
    
    async def search_and_send_tags(self, update: Update, query: str):
        """Search for tags and send results to the user (adapted for menu system)."""
        if not update.message:
            return
            
        try:
            async with BooruAPIWrapper(self.api_base_url, self.api_key, self.user_id) as api:
                # Use exact search unless user explicitly includes wildcards
                if '%' in query or '*' in query:
                    # User specified wildcards, use as-is
                    search_pattern = query
                    logger.info(f"🔍 Tag search with user-specified wildcards: '{search_pattern}'")
                    response = await api.get_tags(limit=20, tags=search_pattern)
                else:
                    # Exact name search first, then fallback to pattern search if no results
                    logger.info(f"🔍 Tag search (exact): '{query}'")
                    response = await api.get_tags(limit=20, name=query)
                    
                    # If no exact matches and query is short enough, try pattern search
                    if (not response or 'tag' not in response or not response['tag']) and len(query) >= 3:
                        logger.info(f"🔍 No exact matches, trying pattern search: '*{query}*'")
                        response = await api.get_tags(limit=20, tags=f"%{query}%")
                
                if not response or 'tag' not in response or not response['tag']:
                    keyboard = [
                        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"😔 No tags found matching '{query}'.\n"
                        "Try a different search term.",
                        reply_markup=reply_markup
                    )
                    return
                
                tags = response['tag']
                if isinstance(tags, dict):
                    tags = [tags]  # Single tag returned as dict
                
                # Format tag results with HTML escaping
                tag_lines = []
                for tag in tags[:10]:  # Limit to 10 tags
                    name = tag.get('name', 'Unknown')
                    # Escape HTML characters in tag names
                    safe_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    count = tag.get('count', 0)
                    tag_lines.append(f"\u2022 <code>{safe_name}</code> ({count} posts)")
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Escape HTML characters in query
                safe_query = query.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                result_text = (
                    f"🏷️ <b>Tags matching '{safe_query}':</b>\n\n" +
                    "\n".join(tag_lines)
                )
                
                if len(tags) > 10:
                    result_text += f"\n\n... and {len(tags) - 10} more tags"
                
                await update.message.reply_text(
                    result_text, 
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in search_and_send_tags: {e}")
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ An error occurred while searching for tags.\n"
                "Please try again later.",
                reply_markup=reply_markup
            )
    

    def run(self, development_mode: bool = False):
        """Run the bot with optimal polling intervals."""
        if not self.application:
            raise RuntimeError("Bot handlers not set up. Call setup_handlers() first.")
        
        if development_mode:
            logger.info("Starting Telbooru bot in DEVELOPMENT mode with responsive polling...")
            # Use 2-second polling for development (responsive but not abusive)
            self.application.run_polling(
                poll_interval=2.0,  # 2 seconds for development
                timeout=10,
                bootstrap_retries=-1
            )
        else:
            logger.info("Starting Telbooru bot in PRODUCTION mode with optimal polling...")
            # Use 2-second polling for production (balanced approach)
            self.application.run_polling(
                poll_interval=2.0,
                timeout=20,
                bootstrap_retries=-1
            )


def load_config() -> Dict[str, str]:
    """Load configuration from environment variables."""
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    api_base_url = os.getenv('BOORU_API_BASE_URL')
    api_key = os.getenv('BOORU_API_KEY')
    user_id = os.getenv('BOORU_USER_ID')
    
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    if not api_base_url:
        raise ValueError("BOORU_API_BASE_URL environment variable is required")
    
    return {
        'telegram_token': telegram_token,
        'api_base_url': api_base_url,
        'api_key': api_key or '',  # Convert None to empty string for optional values
        'user_id': user_id or ''   # Convert None to empty string for optional values
    }


def main():
    """Main function to run the bot."""
    try:
        # Load configuration
        config = load_config()
        
        # Create and setup bot
        bot = TelbooruBot(
            telegram_token=config['telegram_token'],
            api_base_url=config['api_base_url'],
            api_key=config['api_key'] if config['api_key'] else None,
            user_id=config['user_id'] if config['user_id'] else None
        )
        
        bot.setup_handlers()
        
        # Run the bot in production mode with optimal polling (30 seconds)
        # Change to bot.run(development_mode=True) for debugging with 2-second polling
        bot.run(development_mode=False)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise


if __name__ == "__main__":
    # Example usage and testing
    print("Telbooru Bot - Telegram Bot API Wrapper")
    print("Set the following environment variables:")
    print("- TELEGRAM_BOT_TOKEN: Your Telegram bot token")
    print("- BOORU_API_BASE_URL: Base URL of the booru API")
    print("- BOORU_API_KEY: (Optional) API key for authentication")
    print("- BOORU_USER_ID: (Optional) User ID for authentication")
    print()
    
    # Run the bot if environment variables are set
    try:
        config = load_config()
        main()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set the required environment variables and try again.")
