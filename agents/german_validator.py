"""OpenAI Agent for German vocabulary validation and article checking."""
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of translation validation."""
    is_correct: bool
    feedback: str
    correct_translation: Optional[str] = None  # The correct English translation
    corrected_german: Optional[str] = None  # With article if missing
    article: Optional[str] = None  # der, die, das (only for nouns)
    word_type: Optional[str] = None  # noun, verb, adjective, phrase, etc.


class GermanValidatorAgent:
    """Agent for validating German vocabulary and checking articles."""

    SYSTEM_INSTRUCTIONS = """You are a helpful German vocabulary tutor for English speakers.

Your tasks:
1. **Word Type Detection**: Identify the part of speech (noun, verb, adjective, adverb, phrase, etc.)
2. **Article Checking**: ONLY for nouns - when a user provides a German noun WITHOUT an article (der/die/das), you must identify and add the correct article
3. **Translation Validation**: Check if the English translation is correct. Accept synonyms and close matches.
4. **Feedback**: Provide clear, encouraging feedback in a concise manner (1-2 sentences max).

**Response Format**:
Return a JSON object with these fields:
- "is_correct": true if translation is correct (or close enough), false otherwise
- "feedback": A friendly message explaining the result
- "correct_translation": The correct English translation of the German word
- "word_type": The part of speech - one of: "noun", "verb", "adjective", "adverb", "phrase", "other"
- "article": The correct article (der/die/das) ONLY if word_type is "noun", null otherwise
- "corrected_german": The German word with article if it was missing (ONLY for nouns), null otherwise

**Examples**:

Input: german_word="Katze", user_translation="cat"
Output: {"is_correct": true, "feedback": "Correct! However, the full form is 'die Katze'.", "correct_translation": "cat", "word_type": "noun", "article": "die", "corrected_german": "die Katze"}

Input: german_word="der Hund", user_translation="dog"
Output: {"is_correct": true, "feedback": "Perfect! 'Der Hund' means 'dog'.", "correct_translation": "dog", "word_type": "noun", "article": "der", "corrected_german": null}

Input: german_word="schnell", user_translation="fast"
Output: {"is_correct": true, "feedback": "Correct! 'Schnell' means 'fast'.", "correct_translation": "fast", "word_type": "adjective", "article": null, "corrected_german": null}

Input: german_word="laufen", user_translation="to run"
Output: {"is_correct": true, "feedback": "Correct! 'Laufen' means 'to run'.", "correct_translation": "to run", "word_type": "verb", "article": null, "corrected_german": null}

Input: german_word="sich kümmern um", user_translation="to take care of"
Output: {"is_correct": true, "feedback": "Perfect! 'Sich kümmern um' means 'to take care of'.", "correct_translation": "to take care of", "word_type": "phrase", "article": null, "corrected_german": null}

**Rules**:
- Always be encouraging and supportive
- Accept reasonable synonyms (e.g., "house" and "home" for "Haus")
- Identify word type BEFORE checking articles
- For nouns without articles, ALWAYS provide the article
- For non-nouns (verbs, adjectives, phrases), article should be null
- Multi-word expressions should have word_type="phrase"
- Keep feedback concise (1-2 sentences)"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective

    def _extract_article(self, german_word: str) -> tuple[Optional[str], str]:
        """Extract article from German word if present."""
        articles = ["der", "die", "das", "Der", "Die", "Das"]

        for article in articles:
            if german_word.startswith(f"{article} "):
                word_without_article = german_word[len(article) + 1:]
                return article.lower(), word_without_article

        return None, german_word

    async def validate_translation(
        self,
        german_word: str,
        user_translation: str
    ) -> ValidationResult:
        """
        Validate a German-English translation and check article.

        Args:
            german_word: The German word (with or without article)
            user_translation: The user's English translation

        Returns:
            ValidationResult with validation details
        """
        try:
            # Create prompt for the agent
            user_prompt = f"""German word: {german_word}
User's translation: {user_translation}

Validate the translation and provide feedback. If the German word is a noun without an article, identify and add the correct article."""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Low temperature for consistent validation
            )

            # Parse response
            import json
            result = json.loads(response.choices[0].message.content)

            logger.info(f"Validation result for '{german_word}': {result['is_correct']}")

            return ValidationResult(
                is_correct=result.get("is_correct", False),
                feedback=result.get("feedback", "Unable to validate"),
                correct_translation=result.get("correct_translation"),
                corrected_german=result.get("corrected_german"),
                article=result.get("article"),
                word_type=result.get("word_type", "other")
            )

        except Exception as e:
            logger.error(f"Error validating translation: {e}")
            return ValidationResult(
                is_correct=False,
                feedback="Sorry, I couldn't validate the translation. Please try again."
            )

    async def detect_word_type_and_article(self, german_word: str) -> Dict[str, Any]:
        """
        Detect the word type and article (for nouns only) of a German word/phrase.

        Args:
            german_word: German word or phrase

        Returns:
            Dict with word_type and article information
        """
        article, word = self._extract_article(german_word)

        try:
            prompt = f"""Analyze this German word/phrase: {german_word}

Identify:
1. Word type (noun, verb, adjective, adverb, phrase, other)
2. If it's a noun, provide the article (der, die, das)

Return ONLY a JSON object with this format:
{{"word_type": "noun|verb|adjective|adverb|phrase|other", "article": "der|die|das|null", "explanation": "brief explanation"}}

Examples:
- "Hund" → {{"word_type": "noun", "article": "der", "explanation": "masculine noun"}}
- "arbeiten" → {{"word_type": "verb", "article": null, "explanation": "infinitive verb (to work)"}}
- "laufen" → {{"word_type": "verb", "article": null, "explanation": "infinitive verb (to run)"}}
- "schnell" → {{"word_type": "adjective", "article": null, "explanation": "adjective/adverb"}}
- "sich kümmern um" → {{"word_type": "phrase", "article": null, "explanation": "reflexive verb phrase"}}

IMPORTANT: Verbs NEVER have articles. Only nouns have articles (der/die/das)."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a German language expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            word_type = result.get("word_type", "other")
            detected_article = result.get("article")

            # Only use article for nouns
            if word_type != "noun":
                detected_article = None

            # If article was already in the input, use it
            if article:
                detected_article = article
                word_to_store = word
                full_word = german_word
            else:
                word_to_store = word
                if detected_article and word_type == "noun":
                    full_word = f"{detected_article} {word}"
                else:
                    full_word = word

            return {
                "word_type": word_type,
                "article": detected_article,
                "word": word_to_store,
                "full_word": full_word,
                "explanation": result.get("explanation")
            }

        except Exception as e:
            logger.error(f"Error detecting word type: {e}")
            return {
                "word_type": "other",
                "article": article if article else None,
                "word": word,
                "full_word": german_word
            }

    async def detect_batch_word_types(
        self,
        german_words: List[str],
        batch_size: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Batch detect word types and articles for multiple words efficiently.
        Processes words in batches to optimize API calls and reduce latency.

        Args:
            german_words: List of German words/phrases to analyze
            batch_size: Number of words per batch (default 30)

        Returns:
            List of dicts with word_type and article information for each word
        """
        if not german_words:
            return []

        all_results = []

        # Process in batches to avoid token limits
        for i in range(0, len(german_words), batch_size):
            batch = german_words[i:i + batch_size]

            try:
                # Create numbered list for the prompt
                words_list = "\n".join([f"{idx+1}. {word}" for idx, word in enumerate(batch)])

                prompt = f"""Analyze these German words/phrases and identify their word types and articles (for nouns only).

Words to analyze:
{words_list}

For each word, identify:
1. Word type: noun, verb, adjective, adverb, phrase, or other
2. Article (ONLY for nouns): der, die, das, or null

Return ONLY a JSON array with this exact format:
[
  {{"index": 1, "word": "original word", "word_type": "noun|verb|adjective|adverb|phrase|other", "article": "der|die|das|null"}},
  {{"index": 2, "word": "original word", "word_type": "...", "article": "..."}},
  ...
]

Rules:
- Article should ONLY be provided for word_type="noun", otherwise null
- Verbs NEVER have articles (arbeiten, laufen, sein, etc. → article: null)
- Adjectives NEVER have articles (schnell, gut, schön, etc. → article: null)
- Multi-word expressions are word_type="phrase"
- Return results in the same order as input
- Include all {len(batch)} words in the response

IMPORTANT: Only nouns (like Hund, Haus, Katze) get articles. Verbs, adjectives, and adverbs never get articles!"""

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a German language expert. Return only valid JSON arrays."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )

                import json
                response_data = json.loads(response.choices[0].message.content)

                # Handle both direct array and wrapped in "results" key
                batch_results = response_data if isinstance(response_data, list) else response_data.get("results", [])

                # Process each result and add to all_results
                for idx, result in enumerate(batch_results):
                    original_word = batch[idx] if idx < len(batch) else result.get("word", "")
                    article, word_without_article = self._extract_article(original_word)

                    word_type = result.get("word_type", "other")
                    detected_article = result.get("article")

                    # Only use article for nouns
                    if word_type != "noun" or detected_article == "null":
                        detected_article = None

                    # If article was already in input, use it
                    if article:
                        detected_article = article

                    word_info = {
                        "word": word_without_article or original_word,
                        "word_type": word_type,
                        "article": detected_article,
                        "full_word": f"{detected_article} {word_without_article}" if detected_article and word_type == "noun" else (word_without_article or original_word)
                    }

                    all_results.append(word_info)

                logger.info(f"Batch processed {len(batch_results)} words")

            except Exception as e:
                logger.error(f"Error in batch word type detection: {e}")
                # Fallback: process individually for this batch
                logger.info(f"Falling back to individual processing for {len(batch)} words")
                for word in batch:
                    try:
                        result = await self.detect_word_type_and_article(word)
                        all_results.append(result)
                    except Exception as e2:
                        logger.error(f"Error processing word '{word}': {e2}")
                        # Add placeholder result
                        all_results.append({
                            "word": word,
                            "word_type": "other",
                            "article": None,
                            "full_word": word
                        })

        return all_results

    async def check_article(self, german_word: str) -> Dict[str, Any]:
        """
        Check if a German noun has the correct article.
        DEPRECATED: Use detect_word_type_and_article() instead.

        Args:
            german_word: German word (with or without article)

        Returns:
            Dict with article information
        """
        # Use new method and adapt response format for backward compatibility
        result = await self.detect_word_type_and_article(german_word)

        return {
            "has_article": bool(self._extract_article(german_word)[0]),
            "article": result.get("article"),
            "word": result.get("word"),
            "full_word": result.get("full_word"),
            "word_type": result.get("word_type")
        }


# Global instance
german_validator = GermanValidatorAgent()
