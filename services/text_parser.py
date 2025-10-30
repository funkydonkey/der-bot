"""Text parser for extracting German words from bulk pasted text."""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class GermanTextParser:
    """Parser for extracting German vocabulary from unstructured text."""

    # Common German articles, prepositions, and reflexive pronouns
    GERMAN_PARTICLES = {
        "der", "die", "das",  # Articles
        "sich",  # Reflexive pronoun
        "an", "bei", "über", "um", "von", "auf", "für", "mit", "zu"  # Prepositions
    }

    # Cyrillic pattern for Russian text
    CYRILLIC_PATTERN = re.compile(r'[а-яА-ЯёЁ]+')

    # English words pattern (common words to filter out)
    ENGLISH_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "should",
        "could", "may", "might", "can", "to", "of", "in", "on", "at", "by"
    }

    def parse_bulk_text(self, text: str) -> List[str]:
        """
        Parse bulk pasted text and extract German words/phrases.

        Args:
            text: Bulk pasted text containing German vocabulary

        Returns:
            List of extracted German words/phrases
        """
        lines = text.strip().split('\n')
        extracted_words = []
        seen = set()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Extract German word from line
            german_word = self._extract_german_from_line(line)

            if german_word:
                # Deduplicate (case-insensitive)
                word_lower = german_word.lower()
                if word_lower not in seen:
                    seen.add(word_lower)
                    extracted_words.append(german_word)
                    logger.debug(f"Line {line_num}: '{line}' → '{german_word}'")
                else:
                    logger.debug(f"Line {line_num}: '{line}' → DUPLICATE (skipped)")
            else:
                logger.debug(f"Line {line_num}: '{line}' → NO MATCH (skipped)")

        logger.info(f"Extracted {len(extracted_words)} German words from {len(lines)} lines")
        return extracted_words

    def _extract_german_from_line(self, line: str) -> str:
        """
        Extract German word/phrase from a single line.

        Handles various formats:
        - Pure German: "Anfang Oktober"
        - German + translation: "sich entwickeln развиваться"
        - Verb forms: "anfangen fing an angefangen начинаться"
        - With grammar: "der Eigentümer,-= der Besitzer,/ владелец"

        Args:
            line: Single line of text

        Returns:
            Extracted German word/phrase or empty string
        """
        # Remove Cyrillic text (Russian translations)
        line = self.CYRILLIC_PATTERN.sub('', line).strip()

        if not line:
            return ""

        # Split by common delimiters (tabs, multiple spaces, =)
        # This separates German from English translations
        parts = re.split(r'[\t]{2,}|[ ]{3,}|=', line)

        # Take first part (usually the German word/phrase)
        if parts:
            german_part = parts[0].strip()
        else:
            german_part = line.strip()

        # Clean up the German part
        german_word = self._clean_german_word(german_part)

        # Validate it looks like German
        if german_word and self._is_likely_german(german_word):
            return german_word

        return ""

    def _clean_german_word(self, text: str) -> str:
        """
        Clean and format extracted German word.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned German word/phrase
        """
        # Remove common grammar notations
        # ,- (gender marker)
        # ,/e (plural marker)
        # / (alternative forms)
        text = re.sub(r',[-/][a-z]*', '', text)
        text = re.sub(r',[/-]', '', text)

        # Remove single letter abbreviations (A, D, G for grammatical cases)
        text = re.sub(r'\b[ADG]\b', '', text)

        # Split into words
        words = text.split()

        # Handle verb forms with conjugations: "anfangen fing an angefangen"
        # or "bitten bat gebeten просить"
        # Keep only infinitive (first word)
        if len(words) >= 3:
            # Check if it looks like verb conjugations
            # Typically: infinitive + past + past participle
            first_word = words[0].strip('.,;:!?"\'()[]{}')
            second_word = words[1].strip('.,;:!?"\'()[]{}')

            # If second word doesn't start with capital and isn't a preposition,
            # likely verb conjugation - take only first word
            if (second_word.lower() not in self.GERMAN_PARTICLES and
                not second_word[0].isupper() and
                len(second_word) > 2):
                # Check if first word is infinitive (ends with -en typically)
                if first_word.endswith(('en', 'eln', 'ern', 'n')):
                    words = [first_word]

        # Keep prepositions and reflexive pronouns with the main word
        # Example: "sich entwickeln" or "an teilnehmen"
        cleaned_words = []
        for word in words:
            word_clean = word.strip('.,;:!?"\'()[]{}')
            if word_clean:
                # Keep articles, reflexive pronouns, and actual content words
                if (word_clean.lower() in self.GERMAN_PARTICLES or
                    word_clean[0].isupper() or
                    word_clean.endswith(('en', 'eln', 'ern', 'n')) or
                    len(word_clean) > 3):
                    cleaned_words.append(word_clean)

        # Join and remove extra whitespace
        text = ' '.join(cleaned_words)
        text = ' '.join(text.split())

        return text.strip()

    def _is_likely_german(self, text: str) -> bool:
        """
        Check if text is likely a German word/phrase.

        Args:
            text: Text to check

        Returns:
            True if likely German
        """
        if not text or len(text) < 2:
            return False

        # Must contain at least one letter
        if not re.search(r'[a-zA-ZäöüÄÖÜß]', text):
            return False

        # Check if it's just an English word
        text_lower = text.lower().split()[0]  # First word
        if text_lower in self.ENGLISH_WORDS:
            return False

        # Must start with a letter
        if not text[0].isalpha():
            return False

        # Should contain German letters or common German patterns
        # German nouns start with capital
        # German verbs often end with -en, -eln, -ern
        # German has umlauts
        has_german_patterns = (
            bool(re.search(r'[äöüÄÖÜß]', text)) or  # Has umlauts
            bool(re.search(r'(?:^|\s)[A-ZÄÖÜ][a-zäöüß]+', text)) or  # Capitalized noun
            text.endswith(('en', 'eln', 'ern', 'chen', 'lein')) or  # Verb/noun endings
            any(word in text.lower() for word in ['sich', 'der', 'die', 'das'])  # German particles
        )

        return has_german_patterns


# Global instance
text_parser = GermanTextParser()
