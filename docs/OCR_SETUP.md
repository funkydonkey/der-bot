# OCR Setup Guide

This guide explains how to set up the OCR service for the `/addphoto` command.

## What is OCR?

OCR (Optical Character Recognition) allows users to add German vocabulary by taking photos of textbooks, notes, or any text containing German words. The bot extracts the text and lets users review before saving.

## Using OCR.space (Free Tier)

### Step 1: Get Your API Key

1. Visit [https://ocr.space/ocrapi](https://ocr.space/ocrapi)
2. Sign up for a **free account**
3. You'll receive an API key via email
4. Copy your API key

### Step 2: Configure Environment Variables

Add these to your Render service environment variables:

```bash
OCR_API_KEY=your_api_key_here
OCR_API_ENDPOINT=https://api.ocr.space/parse/image
```

**On Render:**
1. Go to your service dashboard
2. Navigate to **Environment** tab
3. Click **Add Environment Variable**
4. Add `OCR_API_KEY` with your key
5. Save changes
6. Render will auto-deploy

### Step 3: Test It

1. Open your Telegram bot
2. Send `/addphoto` command
3. Upload a photo with German text
4. Bot will extract and show the words!

## Free Tier Limits

- **25,000 requests per month**
- **Max file size:** 1MB
- **Rate limit:** 10 requests per 10 seconds

This is more than enough for personal use!

## Without OCR Configured

If you don't configure OCR:
- Bot will work perfectly with all other commands
- `/addphoto` command won't be available
- No errors, just a warning in logs

## Troubleshooting

### "OCR API key not configured"
- Make sure `OCR_API_KEY` is set in environment variables
- Check there are no extra spaces in the key

### "No words found"
- Try a clearer, higher-resolution photo
- Ensure text is in focus and well-lit
- Printed text works better than handwriting

### "Error processing image"
- Check your API key is valid
- Verify you haven't exceeded the free tier limit
- Try a smaller image (< 1MB)

## Alternative: Self-Hosted Tesseract

If you want unlimited OCR with no rate limits, you can deploy your own Tesseract OCR service on Render. Contact support or check the documentation for instructions.
