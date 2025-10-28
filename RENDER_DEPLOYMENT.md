# Render.com Deployment Guide

## ✅ Fix Applied

The deployment error has been fixed! The following changes were made:

1. **Optional Environment Variables**: `mcp_ocr_endpoint` and `database_url` now have sensible defaults
2. **Minimal Required Env Vars**: Only `TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY` are required
3. **Auto Database Connection**: Render will automatically set `DATABASE_URL` from your PostgreSQL database

## 🚀 Deployment Steps

### 1. Configure Environment Variables in Render

Go to your Render dashboard → Your service → Environment

**Required Variables:**
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
OPENAI_API_KEY=your_openai_api_key_here
```

> **Note**: Get your actual values from your `.env` file or:
> - Telegram token from [@BotFather](https://t.me/BotFather)
> - OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)

**Optional Variables** (already set by render.yaml):
```
APP_ENV=production
LOG_LEVEL=INFO
```

**Auto-Set by Render** (from database):
```
DATABASE_URL=(automatically connected from your PostgreSQL database)
```

**Optional - Set if you have OCR server:**
```
MCP_OCR_ENDPOINT=https://your-ocr-server.com
```

### 2. Redeploy

After adding the environment variables:

1. Go to your service page
2. Click "Manual Deploy" → "Deploy latest commit"
3. Or push new changes and Render will auto-deploy

The bot should now start successfully!

## 📊 Expected Startup Logs

When the deployment succeeds, you should see:

```
============================================================
Starting Telegram Bot - Performing Service Checks
============================================================
Checking database connection...
✓ Database connection successful
Checking OpenAI API connection...
✓ OpenAI client initialized
✓ OpenAI API connection successful
Checking MCP OCR server connection...
⚠ MCP OCR server health check failed (non-blocking)
============================================================
All critical service checks passed!
============================================================
✓ Telegram bot authorized successfully
Bot is starting polling...
```

## 🔍 Troubleshooting

### Error: "Field required" for telegram_bot_token

**Solution**: Add `TELEGRAM_BOT_TOKEN` in Render Environment variables

### Error: "Field required" for openai_api_key

**Solution**: Add `OPENAI_API_KEY` in Render Environment variables

### Error: Database connection failed

**Solution**:
- Ensure PostgreSQL database is created in Render
- Check that `DATABASE_URL` is linked in render.yaml (already configured)
- Wait a few seconds for database to initialize

### Bot starts but doesn't respond

**Solution**:
- Check bot token is correct
- Verify bot is not running elsewhere (only one instance can poll Telegram)
- Check Render logs for any errors

## 🎯 Environment Variables Summary

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | None | Get from @BotFather |
| `OPENAI_API_KEY` | ✅ Yes | None | From OpenAI platform |
| `DATABASE_URL` | Auto | SQLite | Render sets from PostgreSQL |
| `MCP_OCR_ENDPOINT` | No | Placeholder | Optional OCR service |
| `APP_ENV` | No | production | Set by render.yaml |
| `LOG_LEVEL` | No | INFO | Set by render.yaml |

## 📝 Post-Deployment Checklist

- [ ] Service shows "Live" status in Render
- [ ] Logs show "Bot is starting polling..."
- [ ] No error messages in logs
- [ ] Bot responds to `/start` command in Telegram
- [ ] Bot responds to any message with "Message received"

## 🔗 Useful Links

- **GitHub Repo**: https://github.com/funkydonkey/der-bot
- **Render Dashboard**: https://dashboard.render.com
- **Telegram Bot**: Search for your bot in Telegram app

## 💡 Next Steps After Successful Deployment

1. Test the bot in Telegram
2. Monitor logs for any issues
3. Set up error notifications in Render
4. Plan Stage 2 features (FSM, advanced handlers, etc.)
