# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Der-Bot** is an AI-powered German vocabulary learning Telegram bot with intelligent word type detection, automatic article assignment (for nouns only), phrase recognition, and lazy-loading translation. The system automatically filters out articles and pronouns, detects word types (noun/verb/adjective/phrase), and uses batch processing for efficient bulk vocabulary imports.

**Tech Stack**: aiogram 3.15 (async Telegram), SQLAlchemy 2.0 (async ORM), OpenAI API (gpt-4o-mini), OCR.space API, PostgreSQL/SQLite

**Key Innovation**: Batch word type detection reduces API calls from O(n) to O(1) for bulk operations, processing 30+ words per API call.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, DATABASE_URL
```

### Running
```bash
# Start bot (performs startup checks: DB, OpenAI, OCR)
python main.py

# Expected startup output shows service connectivity checks:
# ✓ Database connection successful
# ✓ OpenAI API connection successful
# ✓ MCP OCR server connection (warning if unavailable is OK)
```

### Testing
```bash
# Run vocabulary service tests
python test_vocabulary.py

# Test external service connections
python test_services.py

# Note: Tests use real API calls; requires valid credentials in .env
```

### Database
```bash
# Local development (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./telegram_bot.db

# Production (PostgreSQL on Render.com)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

## Architecture Overview

### Layered Design
```
Handlers (Telegram message routing, FSM state management)
    ↓
Services (Business logic, external API orchestration)
    ↓
Repositories (Database query encapsulation)
    ↓
Models (SQLAlchemy ORM definitions)
    ↓
Database (Async engine and session management)
```

### Key Architectural Patterns

**1. Async-First Throughout**: All handlers, services, repositories, and database operations use `async`/`await`. This enables non-blocking concurrent request handling without thread overhead.

**2. FSM (Finite State Machine)**: Multi-turn conversations use aiogram's FSM with `MemoryStorage`. States defined in `handlers/states.py`:
- `AddWordStates` - Single word addition flow
- `QuizStates` - Quiz answer validation flow
- `ImageOCRStates` - Image text extraction flow
- `BulkAddStates` - Bulk word import flow

**3. Repository Pattern**: All database queries isolated in repository classes (`repositories/`). Handlers never write SQL directly.

**4. Lazy-Loading Translation**: Words saved with `translation="[pending]"` on add. First quiz attempt validates user's answer and stores correct translation for future quizzes.

**5. Agent Pattern**: `GermanValidatorAgent` encapsulates OpenAI logic with specialized system prompts for German article detection and translation validation.

### Critical Component Interaction Flow

**Example: /addword command**
```
User: "/addword"
  → vocabulary_handler.cmd_addword() sets FSM state
  → User sends "Hund"
  → vocabulary_handler.process_german_word()
      → VocabularyService.add_word_without_translation()
          → GermanValidatorAgent.check_article("Hund")  [OpenAI API]
              → Returns: {article: "der", word: "Hund", full_word: "der Hund"}
          → WordRepository.create(german_word="Hund", article="der", translation="[pending]")
              → Database INSERT + COMMIT
      → Reply with article info, clear FSM state
```

**Example: /quiz command**
```
User: "/quiz"
  → vocabulary_handler.cmd_quiz()
      → VocabularyService.get_random_word_for_quiz()
          → WordRepository.get_random_word() [random.choice() from user's words]
      → Save word_id to FSM state, ask: "Translate: der Hund"
  → User: "dog"
  → vocabulary_handler.process_quiz_answer()
      → VocabularyService.validate_quiz_answer()
          → GermanValidatorAgent.validate_translation("der Hund", "dog")  [OpenAI API]
              → Returns: ValidationResult(is_correct=True, feedback="...", correct_translation="dog")
          → If translation was "[pending]", update_translation("dog")
          → WordRepository.update_review_stats(word_id, is_correct=True)
              → correct_count++, total_reviews++, last_reviewed=now()
      → Reply with feedback + stats, clear FSM state
```

## Directory Structure

### `/handlers` - Telegram Message Processing
- `vocabulary_handler.py` - Core commands with FSM flows:
  - `/addword` - Single word addition
  - `/mywords` - Display user's vocabulary list
  - `/quiz` - Practice with AI validation
  - `/bulkadd` - Bulk import from pasted text
  - `/addphoto` - Image OCR text extraction
  - `/delete` - Word removal
- `message_handler.py` - Generic handlers: `/start`, `/help`, catch-all
- `states.py` - FSM state definitions

**Router Registration Order Matters**: In `main.py`, register `vocabulary_router` before `message_router` to prevent generic handlers from short-circuiting specific commands.

### `/services` - Business Logic
- `vocabulary_service.py` - Core vocabulary operations orchestration
- `openai_service.py` - OpenAI API client wrapper and connection testing
- `ocr_service.py` - OCR.space API integration for image text extraction
- `text_parser.py` - German word extraction from mixed-language text (handles conjugations, filters grammar notations)
- `health_server.py` - HTTP health check endpoint (Render.com requirement on port 10000)

### `/database` - Data Persistence
- `database.py` - Async SQLAlchemy engine and session factory
- `models.py` - ORM models:
  - `User` - Telegram user tracking
  - `Word` - German vocabulary with learning metrics (correct_count, incorrect_count, total_reviews, last_reviewed)

### `/repositories` - Data Access
- `user_repository.py` - User CRUD operations
- `word_repository.py` - Word CRUD, random quiz selection, stats updates

### `/agents` - AI-Powered Logic
- `german_validator.py` - OpenAI-powered validation:
  - `check_article(german_word)` - Detects grammatical article (der/die/das)
  - `validate_translation(german_word, user_translation)` - Checks correctness, provides feedback

### `/config` - Application Configuration
- `settings.py` - Pydantic-based environment variable loading
- `logging_config.py` - Centralized logging setup

## Important Implementation Details

### Startup Flow (main.py)
1. `setup_logging()` - Initialize structured logging
2. `startup_checks()` - **Blocking checks**:
   - Database connection (exit on failure)
   - OpenAI API connection (exit on failure)
   - OCR service connection (warning only, non-blocking)
3. Initialize Bot + Dispatcher with `MemoryStorage` FSM
4. Register routers (order: vocabulary_router, then message_router)
5. Start health server (async parallel task for Render.com port binding)
6. Start polling (long-running async loop)

### Error Handling Philosophy
- **Critical services fail fast**: Database and OpenAI errors terminate startup
- **Optional services degrade gracefully**: OCR unavailable logs warning, bot continues
- **User-facing errors**: Informative messages returned to Telegram chat
- **Graceful shutdown**: Closes all connections (DB, OCR, bot session) on interrupt

### Database Models
**Word model** (`database/models.py`):
- `german_word` - Word without article (e.g., "Hund")
- `word_type` - Part of speech: "noun", "verb", "adjective", "adverb", "phrase", "other"
- `article` - Grammatical gender: "der", "die", "das" (ONLY for nouns, null for other types)
- `translation` - English translation (initially "[pending]")
- `correct_count`, `incorrect_count`, `total_reviews` - Learning progress tracking
- `validated_by_agent` - Boolean flag for AI validation status
- `validation_feedback` - JSON field for storing validation results
- `last_reviewed` - Timestamp for spaced repetition

**Computed property**: `full_german_word` returns "der Hund" format for nouns only; verbs/adjectives shown without articles.

### FSM Storage
Uses `MemoryStorage` (in-process, not persistent). States lost on bot restart. Fine for single instance; requires Redis/database-backed storage for multi-instance clustering.

### OpenAI Integration
- **Model**: gpt-4o-mini (fast, cost-effective)
- **Temperature**: 0.1 for word type detection (consistency), 0.3 for validation
- **Response format**: JSON mode with strictly defined schema
- **Validation logic**: Accepts synonyms, provides encouraging feedback (1-2 sentences)
- **Batch Processing**: `detect_batch_word_types()` processes 30+ words per API call for efficiency

### Word Type Detection System (`agents/german_validator.py`)
**New Methods**:
- `detect_word_type_and_article(word)` - Analyzes single word, returns type + article (nouns only)
- `detect_batch_word_types(words, batch_size=30)` - **Batch processes multiple words in 1-2 API calls**
- `check_article(word)` - Deprecated, kept for backward compatibility

**Word Types Supported**: noun, verb, adjective, adverb, phrase, other

**Key Design**: Article field is null for non-nouns. Phrase detection handles multi-word expressions like "sich kümmern um".

**Performance**: Batch mode reduces 50 individual API calls to 1-2 batched calls (~50x faster, ~50x cheaper).

### German Filters (`services/german_filters.py`)
**Filtered Word Categories**:
- Articles: der, die, das, ein, eine, etc.
- Pronouns: ich, du, er, sie, mein, dein, etc.
- Prepositions: an, auf, bei, mit, von, zu, etc.
- Conjunctions: und, oder, aber, weil, dass, etc.

**Filter Function**: `should_filter_word(word)` - Returns True if word should not be saved as vocabulary

**Phrase Detection**: `is_phrase(text)` - Identifies multi-word expressions

### Text Parser Enhancements (`services/text_parser.py`)
- **Phrase Preservation**: Multi-word expressions stored as single entries
- **Automatic Filtering**: Articles/pronouns removed during bulk parsing
- **Conjugation Handling**: Verb forms like "anfangen fing an angefangen" → keeps only "anfangen"
- **Mixed Language Support**: Extracts German from text mixed with Russian/English translations

### OCR Integration
- **Provider**: OCR.space free tier (25,000 requests/month)
- **Flow**: User sends photo → Download file → Upload to OCR.space → Extract text → Parse German words → Filter articles/pronouns → User confirms → Batch save with type detection
- **Language**: German language detection enabled

## Common Development Tasks

### Adding a New Command
1. Add handler method to `handlers/vocabulary_handler.py`:
```python
@router.message(Command("mycommand"))
async def cmd_mycommand(message: types.Message):
    # Implementation
    pass
```

2. If multi-turn flow needed, define states in `handlers/states.py`:
```python
class MyCommandStates(StatesGroup):
    waiting_for_input = State()
```

3. Router automatically registered via `main.py` inclusion.

### Adding New Service Methods
1. Add method to appropriate service class (e.g., `services/vocabulary_service.py`)
2. Use dependency injection pattern: pass session/repositories via constructor
3. Follow async patterns: all service methods should be `async def`

### Extending Database Models
1. Add fields to model classes in `database/models.py`
2. Database auto-creates tables on startup (no manual migration for now)
3. Update repository methods if new queries needed

### Testing External Services
Run `test_services.py` to verify:
- OpenAI API connectivity and response format
- OCR service connectivity and text extraction
- Database connection and query execution

## Deployment (Render.com)

**Configuration**: `render.yaml` declares web service + PostgreSQL database

**Environment Variables** (set in Render dashboard):
- `TELEGRAM_BOT_TOKEN` - From BotFather
- `OPENAI_API_KEY` - OpenAI API key
- `OCR_API_KEY` - OCR.space API key (optional)
- `DATABASE_URL` - Auto-injected from linked PostgreSQL service
- `APP_ENV=production`
- `PORT=10000` - Health check server port (required for Render)

**Health Check**: Bot runs HTTP server on port 10000 with routes: `/`, `/health`, `/healthz`. Render monitors this for service health.

**Important**: PostgreSQL connection string must use `postgresql+asyncpg://` scheme (not `postgresql://`) for async compatibility.

## Key Tradeoffs

| Decision | Benefit | Cost |
|----------|---------|------|
| Async throughout | Non-blocking, high concurrency | Debugging complexity |
| In-memory FSM | Simple, no DB overhead | Lost on restart, single-instance only |
| Lazy-loading translations | User-driven learning pace | Requires OpenAI call on first quiz |
| OpenAI for articles | Accurate grammatical gender | API costs (~$0.01 per word) |
| OCR as external service | No ML infrastructure needed | Third-party dependency |
| MemoryStorage FSM | Zero external dependencies | Not suitable for clustering |
