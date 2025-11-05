# Der-Bot - German Vocabulary Learning Telegram Bot

An AI-powered Telegram bot for learning German vocabulary with intelligent word type detection, article assignment, and spaced repetition quizzes.

## Features

### Core Vocabulary Management
- **Smart Word Addition** (`/addword`) - Add single German words with automatic article detection for nouns
- **Bulk Import** (`/bulkadd`) - Paste vocabulary lists and extract German words automatically
- **Image OCR** (`/addphoto`) - Extract words from photos of textbooks, notes, or flashcards
- **Vocabulary Browser** (`/mywords`) - View all your words with learning statistics
- **Word Deletion** (`/delete`) - Remove words from your vocabulary

### Intelligent Features
- **AI Word Type Detection** - Automatically identifies nouns, verbs, adjectives, phrases, etc.
- **Article Management** - Articles (der/die/das) only assigned to nouns, not verbs or adjectives
- **Phrase Recognition** - Multi-word expressions like "sich kümmern um" stored as single entries
- **Smart Filtering** - Automatically filters out German articles, pronouns, and particles from bulk imports
- **Lazy Translation Loading** - Learn translations during quiz practice, not during word addition

### Quiz System
- **Interactive Quizzes** (`/quiz`) - Practice with AI-powered answer validation
- **Synonym Acceptance** - AI accepts close translations and synonyms
- **Progress Tracking** - Track correct/incorrect attempts and success rates
- **Encouraging Feedback** - AI provides helpful, supportive feedback on answers

### Technical Highlights
- Full service connectivity checks on startup
- Async-first architecture for high performance
- Batch processing for efficient bulk operations (1-2 API calls for 50+ words)
- Ready for deployment on Render.com with PostgreSQL

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- PostgreSQL database (or SQLite for local development)
- MCP OCR Server endpoint (optional)

## Project Structure

```
der-bot/
├── config/
│   ├── __init__.py
│   ├── settings.py           # Environment configuration
│   └── logging_config.py     # Logging setup
├── database/
│   ├── __init__.py
│   └── database.py           # Database connection
├── handlers/
│   ├── __init__.py
│   └── message_handler.py    # Telegram message handlers
├── services/
│   ├── __init__.py
│   ├── openai_service.py     # OpenAI API integration
│   └── ocr_service.py        # MCP OCR integration
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .env                     # Environment variables (not in git)
├── .gitignore
└── README.md
```

## Local Setup

### 1. Clone and Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_ENV=development
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
OPENAI_API_KEY=your_openai_api_key
MCP_OCR_ENDPOINT=https://your-mcp-ocr-server.com
DATABASE_URL=sqlite+aiosqlite:///./telegram_bot.db  # SQLite for local
LOG_LEVEL=INFO
```

### 3. Get Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token and add it to `.env`

### 4. Run the Bot

```bash
python main.py
```

### Expected Startup Output

```
2025-01-28 10:00:00 - root - INFO - Logging configured with level: INFO
============================================================
Starting Telegram Bot - Performing Service Checks
============================================================
2025-01-28 10:00:01 - database.database - INFO - ✓ Database connection successful
2025-01-28 10:00:01 - services.openai_service - INFO - ✓ OpenAI client initialized
2025-01-28 10:00:02 - services.openai_service - INFO - ✓ OpenAI API connection successful
2025-01-28 10:00:02 - services.ocr_service - INFO - ✓ MCP OCR client initialized
2025-01-28 10:00:03 - services.ocr_service - INFO - ✓ MCP OCR server connection successful
============================================================
All critical service checks passed!
============================================================
2025-01-28 10:00:03 - __main__ - INFO - ✓ Telegram bot authorized successfully
2025-01-28 10:00:03 - __main__ - INFO - Bot is starting polling...
```

## Deployment to Render.com

### Option 1: Using render.yaml

1. Create a new Web Service on Render.com
2. Connect your GitHub repository
3. Render will automatically detect `render.yaml` and configure the service
4. Set environment variables in Render dashboard

### Option 2: Manual Configuration

1. Create a new Web Service
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python main.py`
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `MCP_OCR_ENDPOINT`
   - `DATABASE_URL` (use Render PostgreSQL)
   - `APP_ENV=production`
   - `LOG_LEVEL=INFO`

### PostgreSQL on Render

1. Create a PostgreSQL database on Render
2. Copy the "Internal Database URL"
3. Replace `postgresql://` with `postgresql+asyncpg://`
4. Set as `DATABASE_URL` in environment variables

Example:
```
postgresql+asyncpg://user:password@hostname:5432/database
```

## Testing

### Test Message Reception

1. Start the bot (locally or on Render)
2. Open Telegram and search for your bot
3. Send `/start` command
4. Send any message
5. Bot should reply "Message received" to every message

### Check Logs

Look for these success indicators in startup logs:

- ✓ Database connection successful
- ✓ OpenAI client initialized
- ✓ OpenAI API connection successful
- ✓ MCP OCR client initialized
- ✓ MCP OCR server connection successful (or warning if unavailable)
- ✓ Telegram bot authorized successfully

## Troubleshooting

### Bot doesn't respond

1. Check if bot is running: Look for "Bot is starting polling..." in logs
2. Verify Telegram token: Should start with a number followed by colon
3. Check firewall/network: Bot needs internet access

### Database connection failed

- **SQLite**: Ensure write permissions in bot directory
- **PostgreSQL**: Verify connection string format and credentials
- Check `DATABASE_URL` format matches database type

### OpenAI API error

1. Verify API key is valid and has credits
2. Check API key format: Should start with `sk-`
3. Test key at https://platform.openai.com/api-keys

### MCP OCR server unavailable

- OCR checks are non-blocking - bot will start even if OCR fails
- Verify endpoint URL is correct
- Check if server is running and accessible

## Next Steps (Stage 2+)

- [ ] Add FSM (Finite State Machine) for conversation flows
- [ ] Implement document processing with OCR
- [ ] Add database models and user tracking
- [ ] Create advanced OpenAI integrations
- [ ] Add error recovery and retry logic

## Development

### Adding New Handlers

Create new handler files in `handlers/` directory:

```python
from aiogram import Router, types

router = Router()

@router.message()
async def my_handler(message: types.Message):
    # Your logic here
    pass
```

Register in `main.py`:

```python
from handlers.my_handler import router as my_router
dp.include_router(my_router)
```

### Environment Variables

All configuration is loaded via `config/settings.py` using Pydantic settings. Add new variables:

1. Add to `.env.example`
2. Add field to `Settings` class in `config/settings.py`
3. Use via `settings.your_variable_name`

## License

MIT License
