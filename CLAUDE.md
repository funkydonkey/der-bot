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

### Database Migrations
```bash
# Run migration to add word_type column (required for new features)
python migrate_add_word_type.py

# For production: See MIGRATION_INSTRUCTIONS.md for detailed steps
# Quick option: Run SQL directly on Render.com:
#   ALTER TABLE words ADD COLUMN word_type VARCHAR(50);
#   UPDATE words SET word_type = 'other' WHERE word_type IS NULL;
```

**IMPORTANT**: After pulling code with database schema changes, you must run migrations before starting the bot. The bot will fail with "column does not exist" errors if migrations are missing.

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

## Common Issues & Troubleshooting

### "column 'word_type' does not exist" Error
**Symptom**: Bot crashes when adding words with database error about missing column.

**Cause**: Database schema is outdated. The `word_type` column was added in recent updates but your database doesn't have it yet.

**Solution**: Run database migration:
```bash
# Local (SQLite)
python migrate_add_word_type.py

# Production (PostgreSQL on Render.com)
# Option 1: Run SQL directly (fastest):
ALTER TABLE words ADD COLUMN word_type VARCHAR(50);
UPDATE words SET word_type = 'other' WHERE word_type IS NULL;

# Option 2: See MIGRATION_INSTRUCTIONS.md for detailed steps
```

After migration, **restart the bot** for changes to take effect.

### Verbs Getting Articles
**Symptom**: Bot assigns articles like "das" to verbs like "arbeiten" or "machen".

**Cause**: Code changes not loaded into memory (bot still running old code).

**Solution**:
1. Restart the bot process (Ctrl+C and `python main.py` or redeploy on Render)
2. Verify you have the latest code with triple safety checks in `agents/german_validator.py`

**Prevention**: Code is loaded once at startup. Always restart after git pull.

### OCR Shows Articles/Pronouns
**Symptom**: OCR results include "der", "die", "das", "ich", "du", etc.

**Cause**: Bot process running old code without filtering.

**Solution**: Restart the bot. The filtering is in `services/ocr_service.py::_extract_words_from_text()`.

**Verification**: Check logs for "Filtered out from OCR" debug messages.

### OpenAI Rate Limits
**Symptom**: Slow responses or "rate limit exceeded" errors during bulk operations.

**Solution**:
- Use batch processing (already implemented in `bulk_add_words()`)
- For 50+ words: Processing happens in batches of 30
- Reduce batch size if needed: modify `batch_size` parameter in `detect_batch_word_types()`

### Database Connection Fails on Startup
**Symptom**: Bot exits with "Database connection failed" error.

**Common causes**:
1. **Wrong DATABASE_URL format**: Must use `postgresql+asyncpg://` for PostgreSQL or `sqlite+aiosqlite:///` for SQLite
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Database not accessible**: Check firewall, credentials, or Render.com database status

### Code Changes Not Taking Effect
**Symptom**: Made code changes but bot behavior unchanged.

**Root cause**: Python loads code into memory at startup. Running bot process has old code.

**Solution**: **Always restart the bot after code changes**:
```bash
# Local: Ctrl+C, then
python main.py

# Render.com: Click "Restart Service" or trigger new deployment
```

### FSM State Confusion
**Symptom**: Bot doesn't respond correctly to multi-turn conversations (addword, quiz, bulkadd).

**Cause**: FSM state stored in memory gets lost on restart or bot confused by unexpected input.

**Solution**:
- Send `/start` to reset state
- FSM states are lost on bot restart (expected behavior with MemoryStorage)
- For production with multiple instances, consider Redis-backed FSM storage

## Development Best Practices

### Before Committing
1. Run migration scripts if you modified database models
2. Test locally with SQLite first
3. Verify all handlers use new service methods
4. Check logs for any deprecation warnings

### After Pulling Updates
1. Check for new migration scripts (e.g., `migrate_*.py`)
2. Run migrations on your database
3. Restart bot process
4. Test core flows: /addword, /quiz, /bulkadd, /addphoto

### When Adding New Fields
1. Add field to `database/models.py`
2. Create migration script (see `migrate_add_word_type.py` as template)
3. Update repositories if needed
4. Update services to use new field
5. Document in CLAUDE.md

### When Modifying AI Prompts
- Test with real examples (nouns, verbs, adjectives, phrases)
- Add explicit rules and examples for edge cases
- Include "IMPORTANT" warnings for critical constraints
- Implement safety checks in code (don't rely only on AI)
