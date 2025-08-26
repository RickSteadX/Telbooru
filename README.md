# Telbooru Bot

A Telegram bot that serves as a web API wrapper for booru-style image boards, allowing users to search and view images directly through Telegram.

## Features

- 🔍 **Image Search**: Search for images using tags
- 🎲 **Random Images**: Get random images from the booru
- 🏷️ **Tag Search**: Find and explore available tags  
- 🖼️ **Album Previews**: Search results displayed as preview image albums
- 🎬 **Multi-Media Support**: Proper handling of images, videos, and GIFs
- 🤖 **Easy Commands**: Simple telegram commands and text input
- 🔐 **Authentication**: Optional API key and user ID support
- ⚡ **Async**: Built with async/await for optimal performance

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` to create a new bot
3. Follow the instructions and save your bot token

### 3. Configure Environment Variables

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` and fill in your values:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BOORU_API_BASE_URL=https://your-booru-site.com
BOORU_API_KEY=your_api_key_here  # Optional
BOORU_USER_ID=your_user_id_here  # Optional
```

### 4. Run the Bot

```bash
python main.py
```

## Usage

### Input Types

**🖼️ Image Search (Default)**  
Any text message you send will search for images:
- `cat girl` - Search for images with these tags
- `rating:safe` - Search for safe-rated images
- `score:>100 landscape` - Search for high-scored landscape images

**🏷️ Tag Search (Command)**  
Use `/tags` command to search for tag names:
- `/tags school` - Find tags containing "school"
- `/tags uniform` - Find tags containing "uniform"  
- `/tags cat*` - Find tags starting with "cat"

### Bot Commands

- `/start` - Welcome message and main menu
- `/tags <query>` - Search for tags matching the query

### Text Input

**Image Search**: Send any text to search for images:
```
cat girl rating:safe
landscape score:>100
school_uniform posing
```

**Tag Search**: Use the `/tags` command to find tags:
```
/tags school
/tags uniform
/tags cat*
```

### Tag Operators

- `rating:safe` - Safe images only
- `score:>100` - Images with score > 100
- `-tag` - Exclude a specific tag
- `tag1 tag2` - Images with both tags

### New Search Experience

**Album Previews**: Search results are now displayed as albums of preview images, making it easier to browse through results visually.

**Smart Media Handling**: 
- 🖼️ Images: Displayed as photos with sample quality when available
- 🎬 Videos: Played as video files (MP4)
- 🎭 Animations: Displayed as animated GIFs

**Organized Selection**: Posts are numbered (#1, #2, #3...) instead of showing internal IDs, making selection more intuitive.

## API Wrapper

The `BooruAPIWrapper` class can be used independently:

```python
import asyncio
from main import BooruAPIWrapper

async def example():
    async with BooruAPIWrapper("https://safebooru.org") as api:
        # Get posts
        posts = await api.get_posts(tags="cat", limit=10)
        
        # Search tags
        tags = await api.get_tags(name_pattern="%school%")
        
        # Get users
        users = await api.get_users(name="username")

asyncio.run(example())
```

## Supported API Endpoints

- **Posts**: Search and retrieve images
- **Tags**: Find and explore tags  
- **Users**: Search for users
- **Comments**: Get comments for posts
- **Deleted Images**: Access deleted content

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Your Telegram bot token |
| `BOORU_API_BASE_URL` | ✅ | Base URL of the booru API |
| `BOORU_API_KEY` | ❌ | API key for authentication |
| `BOORU_USER_ID` | ❌ | User ID for authentication |

### API Authentication

If your booru requires authentication:
1. Get your API key from your account options page
2. Get your user ID from your profile page  
3. Set both `BOORU_API_KEY` and `BOORU_USER_ID`

## Error Handling

The bot includes comprehensive error handling:
- Network errors are logged and user-friendly messages are sent
- Invalid images are skipped automatically
- Rate limiting is handled gracefully
- Configuration errors are clearly reported

## Logging

Logs are written to console with timestamps and log levels. Adjust logging level in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # For debug output
```

## Development

### Code Structure

- `BooruAPIWrapper`: Core API client for booru endpoints
- `TelbooruBot`: Telegram bot implementation
- Command handlers for different bot functions
- Async context managers for proper resource management

### Adding Features

To add new commands:

1. Add handler in `setup_handlers()`:
```python
self.application.add_handler(CommandHandler("newcmd", self.new_command))
```

2. Implement the handler:
```python
async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your command logic here
    await update.message.reply_text("Response")
```

## Troubleshooting

### Common Issues

1. **"Configuration error"**: Check your `.env` file has correct values
2. **"No images found"**: Try different tags or check booru availability  
3. **"Couldn't send images"**: Images might be too large or unsupported format
4. **Bot not responding**: Check your Telegram token and bot permissions

### Debug Mode

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is open source. Use responsibly and respect the terms of service of the booru sites you're accessing.