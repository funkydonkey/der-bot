"""OpenAI Agent for German vocabulary validation and article checking."""
import logging
import re
from typing import Dict, Any, Optional
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
    article: Optional[str] = None  # der, die, das


class GermanValidatorAgent:
    """Agent for validating German vocabulary and checking articles."""

    SYSTEM_INSTRUCTIONS = """You are a helpful German vocabulary tutor for English speakers.

Your tasks:
1. **Article Checking**: When a user provides a German noun WITHOUT an article (der/die/das), you must identify and add the correct article.
2. **Translation Validation**: Check if the English translation is correct. Accept synonyms and close matches.
3. **Feedback**: Provide clear, encouraging feedback in a concise manner (1-2 sentences max).

**Response Format**:
Return a JSON object with these fields:
- "is_correct": true if translation is correct (or close enough), false otherwise
- "feedback": A friendly message explaining the result
- "correct_translation": The correct English translation of the German word
- "article": The correct article (der/die/das) if applicable, null otherwise
- "corrected_german": The German word with article if it was missing, null otherwise

**Examples**:

Input: german_word="Katze", user_translation="cat"
Output: {"is_correct": true, "feedback": "Correct! However, the full form is 'die Katze'.", "correct_translation": "cat", "article": "die", "corrected_german": "die Katze"}

Input: german_word="der Hund", user_translation="dog"
Output: {"is_correct": true, "feedback": "Perfect! 'Der Hund' means 'dog'.", "correct_translation": "dog", "article": "der", "corrected_german": null}

Input: german_word="Hund", user_translation="hound"
Output: {"is_correct": false, "feedback": "Almost! 'Der Hund' means 'dog', not 'hound'. They're related but not exact matches.", "correct_translation": "dog", "article": "der", "corrected_german": "der Hund"}

Input: german_word="Tisch", user_translation="fish"
Output: {"is_correct": false, "feedback": "Not quite! 'Der Tisch' means 'table', not 'fish'.", "correct_translation": "table", "article": "der", "corrected_german": "der Tisch"}

Input: german_word="schnell", user_translation="fast"
Output: {"is_correct": true, "feedback": "Correct! 'Schnell' means 'fast'.", "correct_translation": "fast", "article": null, "corrected_german": null}

**Rules**:
- Always be encouraging and supportive
- Accept reasonable synonyms (e.g., "house" and "home" for "Haus")
- Point out grammatical gender if relevant
- Keep feedback concise (1-2 sentences)
- For nouns without articles, ALWAYS provide the article"""

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
                article=result.get("article")
            )

        except Exception as e:
            logger.error(f"Error validating translation: {e}")
            return ValidationResult(
                is_correct=False,
                feedback="Sorry, I couldn't validate the translation. Please try again."
            )

    async def check_article(self, german_word: str) -> Dict[str, Any]:
        """
        Check if a German noun has the correct article.

        Args:
            german_word: German word (with or without article)

        Returns:
            Dict with article information
        """
        article, word = self._extract_article(german_word)

        if article:
            # Article already present
            return {
                "has_article": True,
                "article": article,
                "word": word,
                "full_word": german_word
            }

        # No article - need to identify it
        try:
            prompt = f"""What is the correct article (der, die, or das) for the German noun: {word}?

Return ONLY a JSON object with this format:
{{"article": "der|die|das", "explanation": "brief one-sentence explanation"}}"""

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

            detected_article = result.get("article", "").lower()

            return {
                "has_article": False,
                "article": detected_article,
                "word": word,
                "full_word": f"{detected_article} {word}",
                "explanation": result.get("explanation")
            }

        except Exception as e:
            logger.error(f"Error checking article: {e}")
            return {
                "has_article": False,
                "article": None,
                "word": word,
                "full_word": word
            }


# Global instance
german_validator = GermanValidatorAgent()
