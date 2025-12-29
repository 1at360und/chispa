"""AnkiConnect client for adding cards to Anki."""

import requests
from dataclasses import dataclass

from .config import ANKI_CONNECT_URL, ANKI_DECK_SPANISH, ANKI_NOTE_TYPE, ANKI_FIELDS


@dataclass
class AnkiCard:
    """Data for creating an Anki card."""

    word: str  # The vocabulary word (Back field)
    definition: str  # English definition
    sentence_blank: str  # Sentence with word blanked out (Spanish + English)
    sentence_full: str  # Full sentence (Spanish + English)
    image_ref: str  # Image HTML reference
    audio_ref: str  # Audio reference [sound:file.mp3]


class AnkiConnectError(Exception):
    """Error communicating with AnkiConnect."""

    pass


class AnkiClient:
    """Client for AnkiConnect API."""

    def __init__(self, url: str = ANKI_CONNECT_URL):
        self.url = url

    def _request(self, action: str, params: dict = None) -> dict:
        """Make a request to AnkiConnect."""
        payload = {"action": action, "version": 6}
        if params:
            payload["params"] = params

        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("error"):
                raise AnkiConnectError(result["error"])

            return result.get("result")
        except requests.exceptions.ConnectionError:
            raise AnkiConnectError(
                "Cannot connect to Anki. Make sure Anki is running and AnkiConnect addon is installed."
            )

    def is_available(self) -> bool:
        """Check if AnkiConnect is available."""
        try:
            self._request("version")
            return True
        except AnkiConnectError:
            return False

    def get_deck_names(self) -> list[str]:
        """Get list of deck names."""
        return self._request("deckNames")

    def get_note_types(self) -> list[str]:
        """Get list of note type names."""
        return self._request("modelNames")

    def add_note(self, card: AnkiCard, deck: str = ANKI_DECK_SPANISH) -> int:
        """
        Add a note to Anki.

        Args:
            card: The card data
            deck: The deck name (default: Spanish deck)

        Returns:
            The note ID
        """
        # Build the fields according to user's note type
        fields = {
            ANKI_FIELDS["front_blank"]: card.sentence_blank,
            ANKI_FIELDS["front_picture"]: card.image_ref,
            ANKI_FIELDS["front_definition"]: card.definition,
            ANKI_FIELDS["back_word"]: card.word,
            ANKI_FIELDS["full_sentence"]: card.sentence_full,
            ANKI_FIELDS["extra_info"]: card.audio_ref,
        }

        note = {
            "deckName": deck,
            "modelName": ANKI_NOTE_TYPE,
            "fields": fields,
            "options": {"allowDuplicate": False},
            "tags": ["chispa"],
        }

        result = self._request("addNote", {"note": note})
        return result


def create_blank_for_word(word: str) -> str:
    """
    Create a blank pattern for a word/phrase.

    Single word: "banco" → "___"
    Multi-word: "in the end" → "___ ___ ___"
    Multi-word: "echar de menos" → "___ ___ ___"
    """
    words = word.split()
    return " ".join(["___"] * len(words))


def replace_word_with_blank(sentence: str, word: str, blank: str) -> str:
    """
    Replace word/phrase in sentence with blank, handling case variations.
    """
    import re

    # Escape special regex characters in the word
    escaped_word = re.escape(word)

    # Create pattern that matches the word with case insensitivity
    pattern = re.compile(escaped_word, re.IGNORECASE)

    return pattern.sub(blank, sentence)


def create_card_data(
    word: str,
    definition: str,
    example: str,
    example_blanked: str,
    translation: str,
    image_ref: str,
    audio_ref: str,
    lang: str = "es",
) -> AnkiCard:
    """
    Create AnkiCard data from word lookup results.

    Args:
        word: The vocabulary word (can be multi-word like "echar de menos")
        definition: Translation/definition
        example: Example sentence in target language
        example_blanked: Example sentence with word blanked out (from AI)
        translation: English translation of example (empty for English cards)
        image_ref: Anki image reference
        audio_ref: Anki audio reference
        lang: Language code ("es", "en", "ru", etc.)

    Returns:
        AnkiCard ready to be added
    """
    # Use the AI-provided blanked sentence (handles conjugations properly)
    # Fall back to manual blanking if AI didn't provide it
    if example_blanked:
        sentence_blanked = example_blanked
    else:
        blank = create_blank_for_word(word)
        sentence_blanked = replace_word_with_blank(example, word, blank)

    # Format based on language
    if lang == "en":
        # English: no translation line needed
        sentence_blank = sentence_blanked
        sentence_full = example
    else:
        # Non-English: include English translation
        sentence_blank = f"{sentence_blanked}<br>{translation}"
        sentence_full = f"{example}<br>{translation}"

    return AnkiCard(
        word=word,
        definition=definition,
        sentence_blank=sentence_blank,
        sentence_full=sentence_full,
        image_ref=image_ref,
        audio_ref=audio_ref,
    )


if __name__ == "__main__":
    # Test AnkiConnect connection
    client = AnkiClient()

    if client.is_available():
        print("AnkiConnect is available!")
        print(f"Decks: {client.get_deck_names()}")
        print(f"Note types: {client.get_note_types()}")
    else:
        print("AnkiConnect is not available. Make sure Anki is running.")
