"""Audio generation using ElevenLabs."""

from pathlib import Path
from elevenlabs import ElevenLabs

from .config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, get_anki_media_folder


def generate_audio(text: str, word: str) -> Path:
    """
    Generate audio for the given text and save it to Anki media folder.

    Args:
        text: The Spanish sentence to read aloud
        word: The vocabulary word (used for filename)

    Returns:
        Path to the saved audio file
    """
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Generate audio
    audio_generator = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",  # Best for Spanish
    )

    # Determine output path
    media_folder = get_anki_media_folder()
    output_path = media_folder / f"chispa_{word}.mp3"

    # Save the audio file
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    return output_path


def get_audio_reference(word: str) -> str:
    """Get the Anki-compatible audio reference for a word."""
    return f"[sound:chispa_{word}.mp3]"


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    text = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cómo estás?"
    word = sys.argv[2] if len(sys.argv) > 2 else "test"

    print(f"Generating audio for: {text}")
    path = generate_audio(text, word)
    print(f"Saved to: {path}")
    print(f"Anki reference: {get_audio_reference(word)}")
