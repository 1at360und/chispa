"""Dictionary lookup using OpenAI for reliable, structured results."""

import json
import re
from dataclasses import dataclass
from openai import OpenAI

from .config import OPENAI_API_KEY


def parse_marked_sentence(marked: str) -> tuple[str, str]:
    """
    Parse a sentence with **marked** word(s) into full and blanked versions.

    Example:
        "El **cajero** fue amable." -> ("El cajero fue amable.", "El ___ fue amable.")
        "El **golpe de estado** fue rápido." -> ("El golpe de estado fue rápido.", "El ___ ___ ___ fue rápido.")

    Returns (full_sentence, blanked_sentence). If no markers found, returns (marked, marked).
    """
    pattern = re.compile(r"\*\*(.+?)\*\*")
    matches = pattern.findall(marked)

    if not matches:
        return marked, marked

    full = pattern.sub(r"\1", marked)

    def blank_replacement(match: re.Match) -> str:
        word = match.group(1)
        word_count = len(word.split())
        return " ".join(["___"] * word_count)

    blanked = pattern.sub(blank_replacement, marked)

    return full, blanked


@dataclass
class WordMeaning:
    """A single meaning/definition of a word."""

    definition: str  # English translation
    part_of_speech: str  # noun, verb, adjective, etc.
    example: str  # Example sentence in target language
    example_blanked: str  # Sentence with word blanked out
    translation: str  # English translation of the example

    def __str__(self) -> str:
        pos = f" ({self.part_of_speech})" if self.part_of_speech else ""
        return f"{self.definition}{pos}"


@dataclass
class WordLookupResult:
    """Result of looking up a word."""

    word: str
    meanings: list[WordMeaning]

    @property
    def is_ambiguous(self) -> bool:
        """Returns True if the word has multiple meanings."""
        return len(self.meanings) > 1

    def get_meaning(self, index: int) -> WordMeaning:
        """Get a specific meaning by index (1-based for user-friendliness)."""
        return self.meanings[index - 1]


def lookup_word(word: str, context: str | None = None, lang: str = "es") -> WordLookupResult:
    """
    Look up a word using OpenAI.

    Args:
        word: The word to look up
        context: Optional context (e.g., "I saw this in a sentence about cooking")
                 If provided, relevant meanings are prioritized
        lang: Language code - "es" for Spanish, "en" for English
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build context-aware prompt
    if context:
        context_instruction = f"""
The user encountered this word in the following context: "{context}"
PRIORITIZE meanings that match this context. Put the most relevant meaning first.
If the context clearly points to one meaning, you can return just that one meaning.
"""
    else:
        context_instruction = """
Return the most common/useful meanings (up to 5, but fewer if the word has limited meanings).
Order by frequency of use (most common first).
"""

    if lang == "en":
        prompt = f"""Look up the English word/phrase "{word}" and provide its meanings.

{context_instruction}

For each meaning, provide:
1. The definition (clear explanation of the meaning)
2. Part of speech (noun, verb, adjective, etc.)
3. An example sentence with the word/phrase wrapped in **double asterisks**

Return as JSON with this exact structure:
{{
    "word": "correctly spelled word",
    "meanings": [
        {{
            "definition": "Clear definition/explanation",
            "part_of_speech": "noun",
            "example": "The **word** appears in this sentence."
        }}
    ]
}}

IMPORTANT - Word normalization:
- The "word" field must contain the CORRECTLY SPELLED word
- Fix any typos or missing accents in borrowed words (e.g., "naive" → "naïve", "cafe" → "café")

CRITICAL - Marking the word:
- Wrap the word/phrase with **double asterisks** in the example sentence
- For verbs, mark the CONJUGATED form (e.g., "She **ran** to the store" not "She **run** to the store")
- For multi-word phrases, wrap the entire phrase (e.g., "**in the end**")

Important:
- Definition should explain the meaning clearly, not just give a synonym
- Include slang, vulgar, or colloquial meanings if commonly used (this is for educational purposes)
- For vulgar/slang words, be DIRECT - say "pussy" not "vulgar term for female genitalia". Learners need exact meanings.
- SENTENCE COMPLEXITY SHOULD MATCH THE WORD: basic vocabulary can have simple sentences, but advanced vocabulary (GRE-level), idioms, and literary words should have sophisticated, contextually rich sentences
- Handle idioms, phrasal verbs, and multi-word expressions naturally (e.g., "in the end", "break down", "get away with")
- Example sentences should demonstrate authentic usage, not oversimplified textbook sentences
- Only return the JSON, no other text"""
    else:
        # Spanish (default)
        prompt = f"""Look up the Spanish word/phrase "{word}" and provide its meanings.

{context_instruction}

For each meaning, provide:
1. The English translation/definition
2. Part of speech (noun, verb, adjective, etc.)
3. An example sentence in Spanish with the word/phrase wrapped in **double asterisks**
4. The English translation of that example sentence

Return as JSON with this exact structure:
{{
    "word": "correctly spelled word with proper accents",
    "meanings": [
        {{
            "definition": "English translation",
            "part_of_speech": "noun",
            "example_spanish": "La **palabra** aparece en esta oración.",
            "example_english": "The word appears in this sentence."
        }}
    ]
}}

IMPORTANT - Word normalization:
- The "word" field must contain the CORRECTLY SPELLED word with proper accent marks
- Example: if user looks up "vispera", return "word": "víspera"
- Example: if user looks up "cafe", return "word": "café"
- Always use proper Spanish orthography with tildes, accents, ñ, etc.

CRITICAL - Marking the word:
- Wrap the word/phrase with **double asterisks** in the Spanish example sentence
- For verbs, mark the CONJUGATED form (e.g., "Ella **corrió** a la tienda" not "Ella **correr** a la tienda")
- For multi-word phrases, wrap the entire phrase (e.g., "**echar de menos**")

Important:
- Definition length should match complexity: simple nouns can be 1-2 words ("bench", "bank"), but verbs, idioms, or nuanced words may need a short phrase or explanation
- Include slang, vulgar, or colloquial meanings if commonly used (this is for educational purposes)
- For vulgar/slang words, be DIRECT - say "pussy" not "vulgar term for female genitalia". Learners need exact meanings.
- SENTENCE COMPLEXITY SHOULD MATCH THE WORD: basic vocabulary (A1-A2) can have simple sentences, but advanced vocabulary (B2-C2), idioms, and literary words should have sophisticated, contextually rich sentences
- Handle idioms, phrasal verbs, and multi-word expressions naturally (e.g., "echar de menos", "in the end", "dar a luz")
- Example sentences should demonstrate authentic usage, not oversimplified textbook sentences
- Only return the JSON, no other text"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a Spanish-English dictionary. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    # Get normalized word (with proper accents), fallback to original
    normalized_word = data.get("word", word)

    meanings = []
    for m in data.get("meanings", []):
        if lang == "en":
            marked = m.get("example", "")
            translation = ""
        else:
            marked = m.get("example_spanish", "")
            translation = m.get("example_english", "")
            # Strip any accidental markers from translation
            translation = re.sub(r"\*\*(.+?)\*\*", r"\1", translation)

        example, example_blanked = parse_marked_sentence(marked)

        meanings.append(
            WordMeaning(
                definition=m.get("definition", ""),
                part_of_speech=m.get("part_of_speech", ""),
                example=example,
                example_blanked=example_blanked,
                translation=translation,
            )
        )

    return WordLookupResult(word=normalized_word, meanings=meanings)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    word = sys.argv[1] if len(sys.argv) > 1 else "banco"
    result = lookup_word(word)

    print(f"Word: {result.word}")
    print(f"Ambiguous: {result.is_ambiguous}")
    print(f"\nMeanings ({len(result.meanings)}):")

    for i, meaning in enumerate(result.meanings, 1):
        print(f"\n{i}. {meaning.definition} ({meaning.part_of_speech})")
        print(f"   Example: {meaning.example}")
        print(f"   Translation: {meaning.translation}")
