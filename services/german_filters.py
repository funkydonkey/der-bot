"""German language filters for articles, pronouns, and other non-vocabulary words."""

# German articles (definite and indefinite)
GERMAN_ARTICLES = {
    "der", "die", "das",  # Definite articles
    "den", "dem", "des",  # Definite articles (declined)
    "ein", "eine", "einer", "einen", "einem", "eines",  # Indefinite articles
}

# German pronouns
GERMAN_PRONOUNS = {
    # Personal pronouns
    "ich", "du", "er", "sie", "es", "wir", "ihr",
    # Possessive pronouns
    "mein", "meine", "meiner", "meinen", "meinem", "meines",
    "dein", "deine", "deiner", "deinen", "deinem", "deines",
    "sein", "seine", "seiner", "seinen", "seinem", "seines",
    "ihr", "ihre", "ihrer", "ihren", "ihrem", "ihres",
    "unser", "unsere", "unserer", "unseren", "unserem", "unseres",
    "euer", "eure", "eurer", "euren", "eurem", "eures",
    # Demonstrative pronouns
    "dieser", "diese", "dieses", "diesen", "diesem",
    "jener", "jene", "jenes", "jenen", "jenem",
    # Interrogative pronouns
    "wer", "was", "welcher", "welche", "welches",
    # Reflexive pronouns
    "mich", "mir", "dich", "dir", "sich", "uns", "euch",
}

# Common German prepositions (usually not vocabulary targets)
GERMAN_PREPOSITIONS = {
    "an", "auf", "aus", "bei", "durch", "für", "gegen", "hinter",
    "in", "mit", "nach", "neben", "ohne", "über", "um", "unter",
    "von", "vor", "zu", "zwischen",
}

# Conjunctions and other particles (not vocabulary targets)
GERMAN_CONJUNCTIONS = {
    "und", "oder", "aber", "denn", "sondern", "dass", "weil", "wenn",
    "als", "wie", "ob", "bis", "seit", "während", "bevor", "nachdem",
}

# Combined set of all words to filter out
WORDS_TO_FILTER = (
    GERMAN_ARTICLES |
    GERMAN_PRONOUNS |
    GERMAN_PREPOSITIONS |
    GERMAN_CONJUNCTIONS
)


def should_filter_word(word: str) -> bool:
    """
    Check if a word should be filtered out (not saved as vocabulary).

    Args:
        word: German word to check (case-insensitive)

    Returns:
        True if word should be filtered out, False otherwise
    """
    return word.lower() in WORDS_TO_FILTER


def is_phrase(text: str) -> bool:
    """
    Check if text is a multi-word phrase.

    Args:
        text: Text to check

    Returns:
        True if text contains multiple words
    """
    # Remove leading articles and split
    words = text.split()

    # Filter out articles from the beginning
    filtered_words = []
    for word in words:
        if word.lower() not in GERMAN_ARTICLES:
            filtered_words.append(word)

    # A phrase has 2+ content words (excluding articles)
    return len(filtered_words) >= 2
