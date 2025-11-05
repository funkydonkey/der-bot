# Database Migration Instructions

## Issue
The `word_type` column needs to be added to the `words` table in your production PostgreSQL database.

## Error You're Seeing
```
column "word_type" of relation "words" does not exist
```

## Solution Options

### Option 1: Run Migration Locally Against Production Database (Recommended)

1. **Get your PostgreSQL connection string from Render.com:**
   - Go to https://dashboard.render.com
   - Find your PostgreSQL database
   - Copy the "External Database URL"

2. **Temporarily set it in your .env file:**
   ```bash
   # Backup your current DATABASE_URL
   # Then replace with production URL:
   DATABASE_URL=postgresql+asyncpg://user:password@hostname:port/database
   ```

3. **Run the migration:**
   ```bash
   source venv/bin/activate
   python migrate_add_word_type.py
   ```

4. **Restore your local database URL in .env**

### Option 2: Run Migration via Render Shell

1. **Go to your web service on Render.com**

2. **Open Shell tab** (in the service dashboard)

3. **Run the migration:**
   ```bash
   python migrate_add_word_type.py
   ```

### Option 3: Manual SQL (Quickest)

1. **Go to your PostgreSQL database on Render.com**

2. **Click "Connect" → "External Connection"** or use the Render dashboard SQL console

3. **Run this SQL:**
   ```sql
   ALTER TABLE words ADD COLUMN word_type VARCHAR(50);

   UPDATE words SET word_type = 'other' WHERE word_type IS NULL;
   ```

## Verification

After running the migration, restart your bot and try adding a word. It should work without errors.

## What This Migration Does

- Adds a `word_type` column to store: noun, verb, adjective, adverb, phrase, other
- Sets existing words to `word_type='other'` as a default
- Makes the column nullable so it's backward compatible

## Rollback (if needed)

If something goes wrong:
```sql
ALTER TABLE words DROP COLUMN word_type;
```

Then restart the bot with the old code.
