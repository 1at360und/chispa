"""CLI interface for Chispa."""

import argparse
import re
import sys
from pathlib import Path

# Pattern to detect blank placeholders (2+ underscores)
BLANK_PATTERN = re.compile(r"_{2,}")

from .config import validate_config, ANKI_DECK_SPANISH, ANKI_DECK_ENGLISH
from .dictionary import lookup_word, WordMeaning
from .image_gen import generate_image, get_image_reference
from .audio_gen import generate_audio, get_audio_reference
from .anki_client import AnkiClient, create_card_data, AnkiConnectError
from .spinner import Spinner


def create_card_for_meaning(word: str, meaning: WordMeaning, client: AnkiClient, lang: str = "es") -> bool:
    """Create a complete Anki card for a word meaning."""
    print(f"\n  Creating card for: {word} = {meaning.definition}")

    # Language determines image/audio source:
    # - English: use English example for both
    # - Non-English: use English translation for image (DALL-E works better), target language for audio
    if lang == "en":
        image_prompt = meaning.example
        audio_text = meaning.example
        deck = ANKI_DECK_ENGLISH
    else:
        image_prompt = meaning.translation
        audio_text = meaning.example
        deck = ANKI_DECK_SPANISH

    image_ref = ""
    audio_ref = ""

    spinner = Spinner("Generating image...")
    spinner.start()
    try:
        generate_image(image_prompt, word)
        image_ref = get_image_reference(word)
        spinner.stop()
        print(f"  ✓ Image generated")
    except Exception as e:
        spinner.stop()
        print(f"  ⚠ Image failed: {e}")

    if BLANK_PATTERN.search(audio_text):
        print(f"  ⚠ Audio skipped: sentence contains blanks")
    else:
        try:
            generate_audio(audio_text, word)
            audio_ref = get_audio_reference(word)
            print(f"  ✓ Audio generated")
        except Exception as e:
            print(f"  ⚠ Audio failed: {e}")

    print("  Adding to Anki...")
    card = create_card_data(
        word=word,
        definition=meaning.definition,
        example=meaning.example,
        example_blanked=meaning.example_blanked,
        translation=meaning.translation,
        image_ref=image_ref,
        audio_ref=audio_ref,
        lang=lang,
    )

    try:
        note_id = client.add_note(card, deck=deck)
        print(f"  ✓ Card created (Note ID: {note_id})")
        return True
    except AnkiConnectError as e:
        print(f"  ✗ Error adding card: {e}")
        return False


def cmd_add(word: str, context: str | None = None, lang: str = "es") -> int:
    """Add a single word interactively."""
    lang_name = "English" if lang == "en" else "Spanish"

    if "|" in word:
        parts = word.split("|", 1)
        word = parts[0].strip()
        inline_hint = parts[1].strip()
        if context:
            current_context = f"{context}; {inline_hint}"
        else:
            current_context = inline_hint
    else:
        current_context = context

    selected: WordMeaning | None = None

    while True:
        if current_context:
            print(f"Looking up ({lang_name}): {word} (context: {current_context})")
        else:
            print(f"Looking up ({lang_name}): {word}")

        try:
            result = lookup_word(word, context=current_context, lang=lang)
        except Exception as e:
            print(f"Error looking up word: {e}")
            return 1

        if not result.meanings:
            print(f"No meanings found for '{word}'")
            return 1

        print(f"\nFound {len(result.meanings)} meaning(s):\n")
        for i, meaning in enumerate(result.meanings, 1):
            print(f"  {i}. {meaning.definition} ({meaning.part_of_speech})")
            print(f"     Example: {meaning.example}")
            if lang != "en":
                print(f"     Translation: {meaning.translation}")
            print()

        if len(result.meanings) == 1:
            print("Only one meaning found.")
            while True:
                try:
                    choice = input("Press Enter to use it, or 'r' to retry with hint: ").strip()
                    if choice == '':
                        selected = result.meanings[0]
                        break
                    elif choice.lower() == 'r':
                        hint = input("Enter hint (e.g., 'vulgar meaning', 'slang', 'formal'): ").strip()
                        if hint:
                            current_context = f"{current_context}; {hint}" if current_context else hint
                        break
                    else:
                        print("Press Enter or 'r'")
                except KeyboardInterrupt:
                    print("\nCancelled")
                    return 1
            if choice.lower() == 'r':
                print()
                continue
            break
        else:
            while True:
                try:
                    choice = input(f"Select [1-{len(result.meanings)}] or 'r' to retry with hint: ").strip()
                    if choice.lower() == 'r':
                        hint = input("Enter hint (e.g., 'vulgar meaning', 'slang', 'the seafood one'): ").strip()
                        if hint:
                            current_context = f"{current_context}; {hint}" if current_context else hint
                        break
                    idx = int(choice)
                    if 1 <= idx <= len(result.meanings):
                        selected = result.meanings[idx - 1]
                        break
                    else:
                        print(f"Please enter 1-{len(result.meanings)} or 'r' to retry")
                except ValueError:
                    print("Please enter a number or 'r' to retry")
                except KeyboardInterrupt:
                    print("\nCancelled")
                    return 1
            if choice.lower() == 'r':
                print()
                continue
            break

    client = AnkiClient()
    if not client.is_available():
        print("\nError: Cannot connect to Anki. Make sure Anki is running and AnkiConnect is installed.")
        return 1

    normalized_word = result.word
    if normalized_word != word:
        print(f"\n  Normalized: {word} → {normalized_word}")

    deck = ANKI_DECK_ENGLISH if lang == "en" else ANKI_DECK_SPANISH
    if selected and create_card_for_meaning(normalized_word, selected, client, lang=lang):
        print(f"\nSuccess! Card for '{normalized_word}' added to deck '{deck}'")
        return 0
    else:
        return 1


def cmd_batch(filepath: str, lang: str = "es") -> int:
    """Process a batch of words from a file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        return 1

    lang_name = "English" if lang == "en" else "Spanish"
    print(f"Processing {lang_name} words...")

    client = AnkiClient()
    if not client.is_available():
        print("Error: Cannot connect to Anki. Make sure Anki is running and AnkiConnect is installed.")
        return 1

    lines = path.read_text().strip().split("\n")
    words_to_process = []
    words_with_hint: dict[str, str] = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        word = line
        hint = None

        if "|" in word:
            parts = word.split("|", 1)
            word = parts[0].strip()
            hint = parts[1].strip()

        words_to_process.append(word)
        if hint:
            words_with_hint[word] = hint

    if not words_to_process:
        print("No words to process in file.")
        return 1

    print(f"Processing {len(words_to_process)} word(s)...\n")

    created = []
    failed = []

    for word in words_to_process:
        hint = words_with_hint.get(word)
        if hint:
            print(f"--- {word} (hint: {hint}) ---")
        else:
            print(f"--- {word} ---")

        try:
            result = lookup_word(word, context=hint, lang=lang)
        except Exception as e:
            print(f"  Error looking up: {e}")
            failed.append(word)
            continue

        if not result.meanings:
            print(f"  No meanings found")
            failed.append(word)
            continue

        current_context = hint
        selected: WordMeaning | None = None
        while True:
            print(f"  Found {len(result.meanings)} meaning(s):\n")
            for i, meaning in enumerate(result.meanings, 1):
                print(f"    {i}. {meaning.definition} ({meaning.part_of_speech})")
                print(f"       Example: {meaning.example}")
                if lang != "en":
                    print(f"       Translation: {meaning.translation}")
                print()

            if len(result.meanings) == 1:
                prompt = "  Press Enter to use it, 's' skip, 'r' retry: "
            else:
                prompt = f"  Select [1-{len(result.meanings)}], 's' skip, 'r' retry: "

            while True:
                try:
                    choice = input(prompt).strip()
                    if choice == '' and len(result.meanings) == 1:
                        selected = result.meanings[0]
                        break
                    elif choice.lower() == 's':
                        print(f"  Skipped")
                        failed.append(word)
                        break
                    elif choice.lower() == 'r':
                        retry_hint = input("  Hint (e.g., 'vulgar', 'slang', 'formal'): ").strip()
                        if retry_hint:
                            current_context = f"{current_context}; {retry_hint}" if current_context else retry_hint
                        break
                    elif len(result.meanings) > 1:
                        idx = int(choice)
                        if 1 <= idx <= len(result.meanings):
                            selected = result.meanings[idx - 1]
                            break
                        else:
                            print(f"  Enter 1-{len(result.meanings)}, 's', or 'r'")
                    else:
                        print("  Press Enter, 's', or 'r'")
                except ValueError:
                    print(f"  Enter a number, 's', or 'r'")
                except KeyboardInterrupt:
                    print("\n  Cancelled batch")
                    return 1

            if choice.lower() == 's':
                break
            elif choice.lower() == 'r':
                print(f"  Retrying with hint: {current_context}")
                try:
                    result = lookup_word(word, context=current_context, lang=lang)
                    if not result.meanings:
                        print(f"  No meanings found")
                        failed.append(word)
                        break
                except Exception as e:
                    print(f"  Error: {e}")
                    failed.append(word)
                    break
                continue
            else:
                break

        if selected is None:
            continue

        normalized_word = result.word
        if normalized_word != word:
            print(f"  Normalized: {word} → {normalized_word}")

        if create_card_for_meaning(normalized_word, selected, client, lang=lang):
            created.append(word)
        else:
            failed.append(word)

    print(f"\n--- Summary ---")
    print(f"Created: {len(created)}")
    print(f"Skipped/Failed: {len(failed)}")

    if failed:
        print(f"\nFailed words: {', '.join(failed)}")

    if created:
        created_set = set(created)
        remaining_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                remaining_lines.append(line)
                continue
            word = stripped.split("|")[0].strip() if "|" in stripped else stripped
            if word not in created_set:
                remaining_lines.append(line)

        if remaining_lines:
            path.write_text("\n".join(remaining_lines) + "\n")
        else:
            path.write_text("")
        print(f"\nUpdated {filepath}: {len(created)} word(s) removed")

    return 0 if not failed else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Chispa - Automated Anki card creator for language learning",
        epilog="""
Examples:
  chispa add "banco"                     Add Spanish word
  chispa add "banco" -c "sitting"        Add with context hint
  chispa add "serendipity" --lang en     Add English word
  chispa batch words.txt                 Process Spanish words
  chispa batch words.txt --lang en       Process English words

Batch workflow for multiple languages:
  chispa batch spanish_words.txt
  chispa batch english_words.txt --lang en
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    add_parser = subparsers.add_parser("add", help="Add a single word")
    add_parser.add_argument("word", help="The word to add")
    add_parser.add_argument(
        "-c", "--context",
        help="Context to help pick the right meaning (e.g., 'sentence about sitting in a park')",
        default=None
    )
    add_parser.add_argument(
        "-l", "--lang",
        help="Language: 'es' for Spanish (default), 'en' for English",
        choices=["es", "en"],
        default="es"
    )

    batch_parser = subparsers.add_parser("batch", help="Process words from a file")
    batch_parser.add_argument("file", help="Path to file with words (one per line)")
    batch_parser.add_argument(
        "-l", "--lang",
        help="Language: 'es' for Spanish (default), 'en' for English",
        choices=["es", "en"],
        default="es"
    )

    args = parser.parse_args()

    errors = validate_config()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease set up your .env file. See .env.example for reference.")
        return 1

    if args.command == "add":
        return cmd_add(args.word, context=args.context, lang=args.lang)
    elif args.command == "batch":
        return cmd_batch(args.file, lang=args.lang)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
