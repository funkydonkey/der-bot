---
tags:
  - agentic
  - ai
  - claude
created: 2025-10-28
---


# Stage 1 (Setup Environment and Connect All Services)

## Goal
Deliver a working Telegram bot that can receive any message and reply “Message received”. All external services (Telegram API, PostgreSQL, OpenAI SDK, MCP OCR server) must be connected and tested for connectivity. This ensures that the entire infrastructure and secrets are functional before adding features.

---

## Deliverables

- The project builds and runs locally and on Render.com
- The following files exist: `requirements.txt`, `.env.example`, `render.yaml`/`Dockerfile` (if needed), `README.md`
- All environment variables are stored in `.env`
- After launch, the bot replies “Message received” to every incoming message
- Startup logs show successful connections to:
    - Telegram API (bot authorized)
    - Database (PostgreSQL or SQLite)
    - OpenAI API (valid key, successful test request)
    - MCP OCR server (valid endpoint, successful healthcheck)
- Minimal directory structure and modules are created:
    - handlers/ (at least for receiving messages)
    - database/database.py (minimal DB init)
    - services/openai_service.py and ocr_service.py (empty or stubbed)
- README describes how to run locally and on Render, and how to fill `.env`

---

## Key Actions

1. **Create project structure and virtual environment**
   - `python -m venv venv`
   - `pip install -r requirements.txt`
   - Create `.env.example` template for all secrets

2. **Connect and test all services**
   - Register Telegram bot via BotFather
   - Send test messages in Telegram and confirm bot replies
   - Initialize database connection (asyncpg/SQLAlchemy)
   - Send test request to OpenAI API (e.g. “ping” to GPT-3.5)
   - Healthcheck request to MCP OCR server (e.g. `/health` endpoint)

3. **Minimal message handler**
   - No FSM needed
   - Any incoming message → reply “Message received”

4. **Logging**
   - Print detailed logs for startup and connection errors

---

## Example environment variables (.env.example)

TELEGRAM_BOT_TOKEN=your_token_here  
OPENAI_API_KEY=your_api_key_here  
MCP_OCR_ENDPOINT=[https://mcp-ocr.example.com](https://mcp-ocr.example.com/)  
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/project_db  
APP_ENV=development


---

## Readiness Checklist

- [ ] All keys and services tested via logs/healthcheck
- [ ] Bot replies to messages
- [ ] Connection errors are logged, not crashing the bot
- [ ] Project documented (README)

---

**If any service fails, log the error clearly—never crash the bot.**


# Stage 2: Agent Validation and Manual Word Input

## Objective

Extend the basic bot from Stage 1 to support:
- Manual entry of German vocabulary through chat
- Intelligent translation validation and instant user feedback with an OpenAI Agent
- Storage and tracking of user vocabulary and learning progress in the database

---

## Features & User Stories

### 1. Manual Word Entry Flow
- The user sends a command to add a new word (e.g. `/add` or a button)
- The bot prompts: “Enter the German word”
- User enters the word (e.g. [Hund])
- OpenAI Agent is checking if correct article provided, if not then add it on his own
- Result is stored in the database (with status) for future quizzes
- Bot replies to the user with feedback and confirmation of saving

### 2. Agent-Powered Translation Validation
- Use OpenAI Agents SDK to implement an intelligent agent specializing in German vocabulary validation and feedback
- The agent recognizes acceptable synonyms and common errors, not just literal matches
- Agent provides:
    - Confirmation if the answer is correct or nearly correct
    - Short, encouraging explanation/correction for wrong or incomplete answers
    - Simple grammatical hints, if relevant
- Agent configuration can be in a dedicated Python file (e.g., `agents/german_validator.py`) with system instructions in English

### 3. Vocabulary Storage and Progress Tracking
- Each user’s word is stored in a database table (`words` or similar) and linked to their Telegram ID
- Store at least: German word, translation, date added, user_id, validation status/result, last reviewed date
- For each review or validation, update stats (e.g., correct/incorrect count)

### 4. Simple Vocabulary Check/Quiz (Optional for this stage, can be stubbed)
- Provide a simple command to show all words or to quiz (“/mywords” or “/quiz”)
- Bot show random word from database and prompts for the translation: “Enter the translation”
- User enters translation (e.g. “dog”)
- The word and translation are sent to an OpenAI Agent for validation (see below)
- The agent checks the translation and replies back (“Correct”, “Almost correct”, or provides the right answer/explanation)
- Bot replies to the user with feedback
- Quiz flow may be stubbed with a static message, or ask the user to translate a saved word, reply using the Agent

---

## Architecture & Components

- **Message Handlers (`handlers/`)**: FSM logic for adding words, prompting user input, handling validation response from the agent
- **Agent Layer (`agents/`)**: OpenAI Agent definition with translation checking and feedback logic (use OpenAI Agents SDK function tools)
- **Database Layer (`database/`, `repositories/`)**: Async storage and retrieval of user words and translations, progress updates
- **Services (`services/`)**: Service code for orchestrating input handling, DB logic calls, and agent API calls
- **Config**: All environment variables loaded from `.env`

---

## Endpoints / Bot Commands

- `/addword` or button: Start manual word entry
- `/mywords`: List user’s saved words (may be stub or simple output)
- `/quiz` (optional): Initiates a review mode by randomly selecting a user word and asking for translation

---

## Data Model

- `users` (user_id, telegram_id, language_preference, etc.)
- `words` (word_id, user_id, german_word, translation, status, date_added, validated_by_agent, correct_count, incorrect_count, last_reviewed)
- Optional: `learning_progress` — may be integrated at this or next stage

---

## OpenAI Agent Example (pseudo-code)

You don't need to replicate it

``` python
from openai_agents import Agent, function_tool

agent = Agent(  
name="GermanVocabValidator",  
instructions="""  
You are a helpful German vocabulary tutor for English speakers.

- When a user provides a word and its translation, check if the translation is correct.
    
- Accept synonyms and close matches, but point out subtle errors.
    
- If the translation is wrong, reply with a brief correction and one sentence tip.
    
- Always be polite and keep explanations concise.
    
- Example:  
    German: Katze, User: cat → Correct  
    German: Hund, User: hound → Almost correct. 'Hund' means 'dog'. 'Hound' is related but not exact.  
    German: Tisch, User: fish → Incorrect. 'Tisch' means 'table'.  
    """,  
    model="gpt-4o",  
    tools=[function_tool(validate_translation)]  
    )
    

@function_tool  
def validate_translation(german_word: str, user_translation: str) -> dict:  
"""Checks if user's translation is correct, returns status, and feedback."""  

```

---

## Example Handler Logic (pseudo-code)

You don't need to replicate it

```python
@router.message(Command("addword"))  
async def start_add_word(message, state):  
await state.set_state(AddWordStates.waiting_for_german)  
await message.answer("Enter the German word:")

@router.message(AddWordStates.waiting_for_german)  
async def got_german_word(message, state):  
await state.update_data(german_word=message.text)  
await state.set_state(AddWordStates.waiting_for_translation)  
await message.answer("Enter the translation:")

@router.message(AddWordStates.waiting_for_translation)  
async def got_translation(message, state):  
data = await state.get_data()  
result = await agents.german_validator.validate_translation(  
data['german_word'], message.text  
)  
# Save to DB, show feedback, etc.
```


---

## Requirements

See the attached `requirements.txt` (Stage 2) for all dependencies.

---

## Acceptance Criteria

- [ ] User can add a German word/translation manually via chat
- [ ] OpenAI Agent validates the translation, gives feedback
- [ ] User always gets a clear response (correct/wrong/explanation)
- [ ] All words and validation results are saved in the database and linked to the user
- [ ] All main flows handle errors gracefully (no crashes)
- [ ] All environment/config requirements are documented and .env.example updated

---

## Additional Recommendations

- Add tests for agent validation logic and DB writing/reading
- Use async programming (no blocking!)
- Keep handler/service/agent/repository layers clearly separated
- All error cases (service unavailable, API limits, etc.) must log clear messages and fail without blocking the bot

---

# Feature improvement: words adding

## Objective

Update the vocabulary bot’s logic so that:
- When a user adds a new German word, only the word itself is required.
- The translation field in the database remains empty or placeholder until the first time the user attempts to translate it during a quiz.
- Upon a first time agent got a translation from LLM during a quiz, the translation field is updated.
- No changes are made to the schema, repository classes, or database fields — the translation column still exists and is required for every word, but is filled lazily.

## Acceptance Criteria

- [ ] User can add a new German word without providing translation.
- [ ] Words are stored with translation field unset at creation.
- [ ] During quiz, if the translation is missing, user answer is validated by LLM and translation from LLM saved.
- [ ] Subsequent quizzes use the stored translation for that word.
- [ ] No changes are required to DB schema, ORM models, or repository interfaces.
- [ ] All DB and agent/API errors are logged and do not crash the bot.

---

**Documentation/README notes should be updated to clarify that users add only the German word, and translations are filled when first guessed or checked.**


---

## Features and Flow Details

### 1. Add Word

- User initiates word addition via `/addword` or equivalent UI.
- Bot prompts user: “Enter a German word to add to your vocabulary.”
- User submits only the German word (e.g. [translate:Apfel]).
- New word is created in the database with:
    - user_id: current user
    - german_word: user input
    - translation: NULL, empty string, or placeholder value (must be allowed by ORM & DB constraints)
    - status, date_added, as before
- Bot confirms addition: “Word accepted!” (No request for translation during the add step.)

### 2. Quiz/Check Translation

- When the user is quizzed on a word whose translation is not yet filled:
    - Bot prompts: “How do you translate [translate:Apfel]?”
    - User responds (e.g. “apple”).
    - LLM agent (OpenAI or equivalent) validates the translation:
        - If it’s correct or nearly correct:
            - Bot responds with positive feedback (“Correct!”) or gentle correction (“Almost! The best translation is ‘apple’. Saved.”).
            - **The accepted/correct translation is immediately saved in the database for this word.**
        - If it’s wrong:
            - Bot gives correction/feedback but does not save the incorrect answer as translation.
    - For subsequent quiz rounds, the translation is now present and can be used for further review.

- If translation field is already filled:
    - Logic remains as before (compare user answer to stored value via agent/algorithm).

### 3. Consistency

- The words table, ORM models, and repository methods are not changed. All “translation” writes are handled in service logic during quiz validation.
- All old and new words remain compatible.

### 4. Error Handling

- If the agent cannot validate or generate a translation (e.g. API error), bot should log a warning and skip saving the field, retrying in the next quiz.
- If DB translation field is required (not nullable), use a safe placeholder until the first quiz guess, then update with the correct answer.

---


# Stage 3: Add Words via Image Recognition

## Objective

Implement the ability for users to add German words to their vocabulary by sending a photo/image (e.g. textbook page, handwritten notes). The bot extracts words from the image via OCR, presents the results for user review and correction, and then saves the selected words to the database in the same format as manual text additions.

---

## Features & User Stories

### 1. Image Upload and OCR Flow

- User sends a photo or image to the Telegram bot (as a file, media, or document).
- Bot receives and preprocesses the image (e.g. resizing, grayscale, binarization for best OCR accuracy).
- The image is sent to the MCP OCR server (or Tesseract) for text recognition, using the German language model.
- Bot receives a list of candidate German words (optionally with confidence scores from OCR service).
- Bot presents the list to the user for review and correction:
    - User can deselect/fix items, confirm misspellings, and/or add missed words manually.
    - The UI can be a message with a numbered list and buttons or simple text commands (“Remove 3”, “Edit 2: Wörterbuch”).
- After review, user confirms the final word list.
- Bot saves all confirmed words into the database, in the same way as words added manually:
    - Each word saved with the current user and translation as NULL/placeholder.
    - All subsequent flows (quiz, translation validation, etc.) work identically as with manual input.

### 2. OCR Service Integration

- MCP OCR server endpoint configured via environment (`MCP_OCR_ENDPOINT`).
- Service should handle common errors:
    - Invalid file format, unsupported image type.
    - Low OCR confidence (let user decide: accept or skip).
    - Network/API errors — log and notify user.
- Use `deu.traineddata` for Tesseract or “German mode” in MCP.
- Preprocessing can use Pillow & OpenCV tools (resize, grayscale).

### 3. User Experience

- Bot replies to image upload promptly (“Processing image, please wait…”).
- Presents results for user confirmation as a message or interactive buttons.
- Allows user to edit the extracted word list before final save.
- Confirms successful addition and how to access new words (e.g. “10 words added to your vocabulary!”).

### 4. Data Handling

- Added words stored just like manual entries: with translation empty to be filled later during quiz.
- All words link to user/telegram_id, and source marked as “ocr”.
- Any duplicates (by word/user) are ignored or flagged during save (optional).

---

## Minimal Example Flow (Pseudo-code - not mandatory to follow)

## Handler for photo/image upload

``` python
@router.message(F.photo | F.document)  
async def handle_image_upload(message, state, ocr_service):  
await message.answer("Processing image, please wait…")  
words, confidences = await ocr_service.extract_german_words(message.photo.file_id)  
if not words:  
await message.answer("Could not extract any words. Try a clearer image!")  
return  
```

## Show user result, allow corrections  
``` python
await message.answer(f"Found the following German words:\n" +  
"\n".join(f"{i+1}. {w}" for i, w in enumerate(words)) +  
"\nReply with changes or type 'OK' to confirm.")  
``` 
## (Wait for user corrections; skipped for brevity)  
``` python
final_list = <after review>  
# Save words in DB  
for word in final_list:  
await repo.add_word(user_id=..., german_word=word, translation=None, source='ocr')  
await message.answer(f"{len(final_list)} words added!")
``` 

---

## Requirements

- All OCR server calls must use the German language model.
- Image file handling must be robust (support typical Telegram image/document types).
- User review/correction step required for quality.
- Logging for API errors, OCR errors, and unsupported cases.
- All new words are saved with translation as empty or placeholder; translation is filled later, as in Stage 2.

---

## Environment

- Ensure `MCP_OCR_ENDPOINT` is in `.env` and used in service.
- No changes to DB schema/classes required.

---

## Acceptance Criteria

- [ ] User can add vocabulary by sending an image/photo to the bot.
- [ ] Bot extracts German words with OCR and presents list for user confirmation and correction.
- [ ] Confirmed words are stored in DB (with translation empty and source marked “ocr”).
- [ ] Every word added via image works exactly the same as manual word (participates in quiz, translation filled lazily).
- [ ] All errors and edge cases are logged; user notified of issues.
- [ ] README and code comments updated for usage.

---

**User workflow and database handling for image-based word addition should remain completely consistent with manual word workflow developed in Stage 2.**
