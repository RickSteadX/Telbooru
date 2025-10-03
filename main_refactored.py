#!/usr/bin/env python3
"""
Telbooru - Telegram Bot API Wrapper (Refactored with Repository Pattern)

A web API wrapper utilizing Telegram bot to send images to users.
This version implements the Repository Pattern for better separation of concerns,
testability, and maintainability.
"""

import asyncio
import logging
import os
from typing import Optional, Dict
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from dotenv import load_dotenv

# Import repositories
from repositories.booru_repository import BooruRepository
from repositories.user_repository import UserRepository, UserSettings
from repositories.search_repository import SearchRepository, SearchState

# Import services
from services.booru_service import BooruService
from services.user_service import UserService

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARN
)
logger = logging.getLogger(__name__)


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


class TelbooruBot:
    """
    Telegram bot for sending images from booru API (Refactored).
    
    This refactored version uses the Repository Pattern to separate concerns:
    - Repositories handle data access (API calls, file I/O)
    - Services handle business logic
    - Bot class handles presentation logic (Telegram interactions)
    """
    
    def __init__(self, telegram_token: str, api_base_url: str, 
                 api_key: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize the Telegram bot with dependency injection.
        
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
        
        # Initialize repositories
        self.user_repository = UserRepository(data_dir="user_data")
        self.search_repository = SearchRepository()
        
        # Initialize services
        self.user_service = UserService(self.user_repository)
        
        # Track user states for input handling
        self.user_states: Dict[int, str] = {}
    
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
        query = update.callback_query
        if not query or not query.data:
            logger.warning("No callback query or data in update")
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
        """Show settings menu using UserService."""
        user_id = query.from_user.id
        settings = self.user_service.get_settings(user_id)
        
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
        await self.perform_batch_search(update, text, user_id)
    
    async def process_autotag_addition(self, update: Update, tag_text: str, user_id: int):
        """Process auto-tag addition from user input using UserService."""
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
        
        # Use UserService to add the tag
        if self.user_service.add_auto_tag(user_id, tag_text):
            await update.message.reply_text(
                f"✅ Successfully added auto tag: '{tag_text}'",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
                ])
            )
        else:
            await update.message.reply_text(
                f"❌ Tag '{tag_text}' is already in your auto tags.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Auto Tags", callback_data="settings_autotags")]
                ])
            )
    
    async def handle_random_search(self, query):
        """Handle random image request."""
        user_id = query.from_user.id
        await self.perform_batch_search_callback(query, "", user_id)
    
    async def perform_batch_search(self, update: Update, tags: str, user_id: int):
        """Perform batch search using BooruService and display results with pagination."""
        if not update.message:
            return
            
        try:
            # Send "typing" action
            await update.message.chat.send_action(action="upload_photo")
            
            # Get user settings using UserService
            settings = self.user_service.get_settings(user_id)
            
            # Use BooruRepository and BooruService
            async with BooruRepository(self.api_base_url, self.api_key, self.user_id) as repo:
                service = BooruService(repo)
                
                # Search with user preferences
                logger.info(f"🔍 Starting search with tags: '{tags}'")
                posts = await service.search_posts_with_preferences(tags, settings, limit=50)
                
                if not posts:
                    logger.info(f"💭 No posts found for tags: '{tags}'")
                    await update.message.reply_text(
                        "😔 No images found for the given tags.\n"
                        "Try different tags or check your spelling.\n\n"
                        f"🎯 Search terms used: <code>{tags}</code>",
                        parse_mode='HTML'
                    )
                    return
                
                # Store search state using SearchRepository
                search_state = SearchState(
                    query=tags,
                    results=posts,
                    current_page=0,
                    total_pages=(len(posts) - 1) // 5 + 1
                )
                self.search_repository.save_search_state(user_id, search_state)
                
                # Show first page
                await self.send_search_results_page(update.message, user_id, 0, service)
                
        except Exception as e:
            logger.error(f"Error in perform_batch_search: {e}")
            await update.message.reply_text(
                "❌ An error occurred while searching for images.\n"
                "Please try again later."
            )
    
    async def perform_batch_search_callback(self, query, tags: str, user_id: int):
        """Perform batch search from callback query using BooruService."""
        try:
            # Get user settings using UserService
            settings = self.user_service.get_settings(user_id)
            
            # Use BooruRepository and BooruService
            async with BooruRepository(self.api_base_url, self.api_key, self.user_id) as repo:
                service = BooruService(repo)
                
                logger.info(f"🔍 Starting callback search with tags: '{tags}'")
                posts = await service.search_posts_with_preferences(tags, settings, limit=50)
                
                if not posts:
                    logger.info(f"💭 No posts found for callback tags: '{tags}'")
                    await query.edit_message_text(
                        "😔 No images found for the given tags.\n"
                        "Try different tags or check your spelling.\n\n"
                        f"🎯 Search terms used: <code>{tags}</code>",
                        parse_mode='HTML'
                    )
                    return
                
                # Store search state using SearchRepository
                search_state = SearchState(
                    query=tags,
                    results=posts,
                    current_page=0,
                    total_pages=(len(posts) - 1) // 5 + 1
                )
                self.search_repository.save_search_state(user_id, search_state)
                
                # Show first page
                await self.send_search_results_page_callback(query, user_id, 0, service)
                
        except Exception as e:
            logger.error(f"Error in perform_batch_search_callback: {e}")
            await query.edit_message_text(
                "❌ An error occurred while searching for images.\n"
                "Please try again later."
            )
    
    async def send_search_results_page(self, message, user_id: int, page: int, service: BooruService):
        """Send a page of search results as an album of preview images."""
        search_state = self.search_repository.get_search_state(user_id)
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
                preview_url = service.get_preview_url(post)
                if not preview_url:
                    continue
                    
                # Create caption for first image with search info
                if i == 0:
                    caption = f"🖼️ <b>Search Results</b> (Page {page + 1}/{search_state.total_pages})\n"
                    if search_state.query:
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
            
            # Create inline keyboard for post selection
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1
                media_type = service.get_media_type(post.get('file_url', ''))
                
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
            
            # Send keyboard as separate message
            keyboard_text = "🎯 Select a post to view:"
            menu_message = await message.reply_text(
                keyboard_text,
                reply_markup=reply_markup
            )
            
            # Update menu message ID in search state
            self.search_repository.update_menu_message_id(user_id, menu_message.message_id)
            
        except Exception as e:
            logger.error(f"Error sending search results album: {e}")
            await message.reply_text("❌ Failed to send search results. Please try again.")
    
    async def send_search_results_page_callback(self, query, user_id: int, page: int, service: BooruService):
        """Send a page of search results via callback query."""
        search_state = self.search_repository.get_search_state(user_id)
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
                preview_url = service.get_preview_url(post)
                if not preview_url:
                    continue
                    
                # Create caption for first image
                if i == 0:
                    caption = f"🖼️ <b>Search Results</b> (Page {page + 1}/{search_state.total_pages})\n"
                    if search_state.query:
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
            
            # Create inline keyboard
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1
                media_type = service.get_media_type(post.get('file_url', ''))
                
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
            
            # Update menu message ID
            self.search_repository.update_menu_message_id(user_id, new_menu.message_id)
            
        except Exception as e:
            logger.error(f"Error sending search results page: {e}")
            await query.answer("Failed to update results. Please try a new search.")
    
    async def show_search_page(self, query, user_id: int, page: int):
        """Show a specific search page."""
        search_state = self.search_repository.get_search_state(user_id)
        if search_state:
            self.search_repository.update_page(user_id, page)
        
        # Create service for this operation
        async with BooruRepository(self.api_base_url, self.api_key, self.user_id) as repo:
            service = BooruService(repo)
            await self.send_search_results_page_callback(query, user_id, page, service)
    
    async def send_full_image(self, query, user_id: int, post_index: int):
        """Send the full media for a selected post."""
        search_state = self.search_repository.get_search_state(user_id)
        if not search_state or post_index >= len(search_state.results):
            await query.answer("Media not found.")
            return
        
        post = search_state.results[post_index]
        
        # Create service for media operations
        async with BooruRepository(self.api_base_url, self.api_key, self.user_id) as repo:
            service = BooruService(repo)
            
            media_url = service.get_display_url(post, use_sample=True)
            media_type = service.get_media_type(post.get('file_url', ''))
            post_info = service.extract_post_info(post)
            
            if not media_url:
                await query.answer("Media URL not available.")
                return
            
            try:
                # Determine display order
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
                    f"{type_emoji} **{type_label} #{display_order}** (ID: {post_info['id']})\n"
                    f"📊 **Size:** {post_info['width']}x{post_info['height']}\n"
                    f"⭐ **Score:** {post_info['score']}\n"
                    f"🏷️ **Tags:** {escape_markdown(post_info['tags'][:500])}{'...' if len(post_info['tags']) > 500 else ''}"
                )
                
                # Send media based on type
                if media_type == 'video':
                    try:
                        await query.message.reply_video(
                            video=media_url,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                        await query.answer(f"{type_label} sent!")
                    except TelegramError as e:
                        logger.warning(f"Failed to send video: {e}")
                        await query.answer("Failed to send video. It might be too large.")
                        
                elif media_type == 'gif':
                    try:
                        await query.message.reply_animation(
                            animation=media_url,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                        await query.answer(f"{type_label} sent!")
                    except TelegramError as e:
                        logger.warning(f"Failed to send animation: {e}")
                        await query.answer("Failed to send animation. It might be too large.")
                        
                else:  # Image
                    try:
                        await query.message.reply_photo(
                            photo=media_url,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                        await query.answer(f"{type_label} sent!")
                    except TelegramError as e:
                        logger.warning(f"Failed to send image: {e}")
                        await query.answer("Failed to send image. It might be too large.")
                
                # Re-send selection menu
                await self._resend_selection_menu(query, user_id, search_state, service)
                
            except Exception as e:
                logger.error(f"Unexpected error in send_full_image: {e}")
                await query.answer("An unexpected error occurred.")
    
    async def _resend_selection_menu(self, query, user_id: int, search_state: SearchState, service: BooruService):
        """Send a fresh selection menu at the bottom after viewing media."""
        try:
            current_page = search_state.current_page
            start_idx = current_page * search_state.posts_per_page
            end_idx = min(start_idx + search_state.posts_per_page, len(search_state.results))
            page_posts = search_state.results[start_idx:end_idx]
            
            # Create inline keyboard
            keyboard = []
            for i, post in enumerate(page_posts):
                post_order = start_idx + i + 1
                media_type = service.get_media_type(post.get('file_url', ''))
                
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
            
            # Send fresh menu
            menu_text = f"🎯 Select another post: (Page {current_page + 1}/{search_state.total_pages})"
            new_menu = await query.message.chat.send_message(
                menu_text,
                reply_markup=reply_markup
            )
            
            # Update menu message ID
            self.search_repository.update_menu_message_id(user_id, new_menu.message_id)
            
        except Exception as e:
            logger.error(f"Error sending fresh selection menu: {e}")
    
    async def handle_settings_callback(self, query, data: str):
        """Handle settings-related callbacks."""
        user_id = query.from_user.id
        
        if data == "settings_autotags":
            await self.show_autotags_settings(query, user_id)
        elif data == "settings_toggles":
            await self.show_toggle_settings(query, user_id)
    
    async def show_autotags_settings(self, query, user_id: int):
        """Show auto tags settings menu using UserService."""
        settings = self.user_service.get_settings(user_id)
        
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
        
        auto_tags_list = "\n".join([f"• {tag}" for tag in settings.auto_tags]) if settings.auto_tags else "No auto tags set."
        
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
        """Show toggle rules settings menu using UserService."""
        settings = self.user_service.get_settings(user_id)
        
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
        
        enabled_rules = self.user_service.get_enabled_rules(user_id)
        enabled_text = "\n".join([f"• {rule}" for rule in enabled_rules]) if enabled_rules else "No rules enabled."
        
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
        """Handle toggle rule callbacks using UserService."""
        user_id = query.from_user.id
        
        # Parse the rule from callback data
        rule = data.replace("toggle_", "").replace("_COLON_", ":").replace("_GT_", ">")
        
        # Toggle the rule using UserService
        new_state = self.user_service.toggle_rule(user_id, rule)
        
        await query.answer(f"Toggled {rule}: {'ON' if new_state else 'OFF'}")
        
        # Refresh the toggle settings menu
        await self.show_toggle_settings(query, user_id)
    
    async def handle_autotag_callback(self, query, data: str):
        """Handle auto tag callbacks using UserService."""
        user_id = query.from_user.id
        
        if data.startswith("autotag_remove_"):
            index = int(data.split("_")[-1])
            if self.user_service.remove_auto_tag_by_index(user_id, index):
                await query.answer("Auto tag removed")
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
        """Search for tags and send results using BooruService."""
        if not update.message:
            return
            
        try:
            async with BooruRepository(self.api_base_url, self.api_key, self.user_id) as repo:
                service = BooruService(repo)
                
                # Use service method with fallback
                tags = await service.search_tags_with_fallback(query, limit=20)
                
                if not tags:
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
                
                # Format tag results
                tag_lines = []
                for tag in tags[:10]:
                    name = tag.get('name', 'Unknown')
                    safe_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    count = tag.get('count', 0)
                    tag_lines.append(f"• <code>{safe_name}</code> ({count} posts)")
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
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
            self.application.run_polling(
                poll_interval=2.0,
                timeout=10,
                bootstrap_retries=-1
            )
        else:
            logger.info("Starting Telbooru bot in PRODUCTION mode with optimal polling...")
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
        'api_key': api_key or '',
        'user_id': user_id or ''
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
        
        # Run the bot
        bot.run(development_mode=False)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise


if __name__ == "__main__":
    print("Telbooru Bot - Telegram Bot API Wrapper (Refactored)")
    print("Repository Pattern Implementation")
    print()
    main()