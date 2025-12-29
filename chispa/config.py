"""Configuration management for Chispa."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or current directory
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "iLNdboCfbjKNDLRgl0GZ")

# Image generation settings
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-1")  # or "dall-e-3"

# Anki settings
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")
ANKI_DECK_SPANISH = os.getenv("ANKI_DECK_SPANISH", "esp")
ANKI_DECK_ENGLISH = os.getenv("ANKI_DECK_ENGLISH", "en")
ANKI_NOTE_TYPE = os.getenv("ANKI_NOTE_TYPE", "All-Purpose")

# Anki field names (matching user's note type)
ANKI_FIELDS = {
    "front_blank": "Front (Example with word blanked out or missing)",
    "front_picture": "Front (Picture)",
    "front_definition": "Front (Definitions, base word, etc.)",
    "back_word": "Back (a single word/phrase, no context)",
    "full_sentence": "- The full sentence (no words blanked out)",
    "extra_info": "- Extra Info (Pronunciation, personal connections, conjugations, etc)",
}

# Anki media folder (macOS default)
def get_anki_media_folder() -> Path:
    """Get the Anki media folder path."""
    # macOS path
    mac_path = Path.home() / "Library" / "Application Support" / "Anki2"

    if mac_path.exists():
        # Find the user profile folder (usually "User 1" or custom name)
        for profile in mac_path.iterdir():
            if profile.is_dir() and not profile.name.startswith("."):
                media_folder = profile / "collection.media"
                if media_folder.exists():
                    return media_folder

    # Fallback: create a local media folder
    local_media = Path.cwd() / "anki_media"
    local_media.mkdir(exist_ok=True)
    return local_media


def validate_config() -> list[str]:
    """Validate that required configuration is present. Returns list of errors."""
    errors = []

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not set in environment")

    if not ELEVENLABS_API_KEY:
        errors.append("ELEVENLABS_API_KEY not set in environment")

    return errors
