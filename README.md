# Chispa

A CLI tool that automates Anki flashcard creation for language learning. It looks up words, generates images, generates audio, and adds cards directly to Anki.

---

## Requirements

Before using Chispa, ensure you have:

1. **Anki** running with the **AnkiConnect** addon installed
   - Install AnkiConnect from Anki's addon menu (Tools → Add-ons → Get Add-ons)
   - Addon code: `2055492159`
   - AnkiConnect runs on `localhost:8765`

2. **API Keys** configured in a `.env` file:
   ```
   OPENAI_API_KEY=sk-...
   ELEVENLABS_API_KEY=...
   ELEVENLABS_VOICE_ID=...  # optional
   ```

3. **Python 3.10+**

4. **"All-Purpose" Note Type** from [Fluent Forever](https://blog.fluent-forever.com/gallery/)
   - Download the Model Deck from the link above
   - Double-click to import into Anki
   - Field mappings are hardcoded for this note type

---

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd chispa

# Install in development mode
pip install -e .
```

---

## Commands

### Adding a Single Word

```bash
chispa add "word"
```

This is the primary command. It:
1. Looks up the word using AI
2. Shows you all meanings found
3. Lets you pick the right one
4. Generates an image for the card
5. Generates audio pronunciation
6. Adds the card to Anki

#### Options

| Flag | Description | Example |
|------|-------------|---------|
| `-c`, `--context` | Hint to find the right meaning | `chispa add "banco" -c "sitting"` |
| `-l`, `--lang` | Language (`es` or `en`) | `chispa add "serendipity" --lang en` |

#### Examples

```bash
# Basic Spanish word
chispa add "banco"

# Spanish word with context hint (flag style)
chispa add "banco" -c "sitting in the park"

# Spanish word with context hint (inline style)
chispa add "banco | sitting in the park"

# English word
chispa add "serendipity" --lang en

# Slang or specific meaning
chispa add "coger | vulgar Mexican slang"
```

> **Tip:** Inline hints with `|` are great when you've already looked up the word on SpanishDict and know what meaning you want.

### Batch Processing

```bash
chispa batch words.txt
```

Process multiple words from a file. One word per line.

#### File Format

```
# Comments start with #
banco
mesa
silla

# With context hint (inline)
banco | sitting in the park
coger | vulgar Mexican slang
```

> **Auto-cleanup:** Successfully created cards are automatically removed from the file. Failed or skipped words stay for retry.

#### Options

| Flag | Description | Example |
|------|-------------|---------|
| `-l`, `--lang` | Language (`es` or `en`) | `chispa batch words.txt --lang en` |

#### Examples

```bash
# Process Spanish words
chispa batch spanish_words.txt

# Process English words
chispa batch english_words.txt --lang en
```

---

## Interactive Selection

When a word has multiple meanings, Chispa shows them all:

```
Found 3 meaning(s):

  1. bench (noun)
     Example: Me senté en el banco del parque.
     Translation: I sat on the park bench.

  2. bank (noun)
     Example: Fui al banco a depositar dinero.
     Translation: I went to the bank to deposit money.

  3. school (of fish) (noun)
     Example: Vimos un banco de peces en el mar.
     Translation: We saw a school of fish in the sea.

Select [1-3] or 'r' to retry with hint:
```

### Commands During Selection

| Input | Action |
|-------|--------|
| `1`, `2`, `3`... | Select that meaning |
| `r` | Retry lookup with a new hint |
| `s` | Skip this word (batch mode only) |
| `Ctrl+C` | Cancel |

### Using Retry

If none of the meanings match what you're looking for:

```
Select [1-3] or 'r' to retry with hint: r
Enter hint (e.g., 'vulgar meaning', 'slang', 'formal'): the seafood one
```

The AI will re-lookup the word prioritizing your hint.

---

## Card Structure

Each card Chispa creates contains:

| Field | Content |
|-------|---------|
| **Front** | Blanked sentence + image + definition |
| **Back** | The word + audio |

### Example Card

**Front:**
```
Me senté en el ___ del parque.
I sat on the park bench.

[IMAGE: Park bench scene]

Definition: bench
```

**Back:**
```
banco

[AUDIO: Spanish pronunciation]
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                      You                                │
│              chispa add "banco"                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Word Lookup                            │
│                (OpenAI GPT-4o)                          │
│                                                         │
│  Returns: definitions, examples, blanked sentences      │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               You Pick a Meaning                        │
└─────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │   Image   │  │   Audio   │  │   Card    │
    │  (DALL-E) │  │(ElevenLabs│  │  Builder  │
    │           │  │           │  │           │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │              │              │
          └──────────────┼──────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    AnkiConnect                          │
│                  (localhost:8765)                       │
│                                                         │
│              Card added to your deck!                   │
└─────────────────────────────────────────────────────────┘
```

---

## Language Support

| Language | Code | Status |
|----------|------|--------|
| Spanish | `es` | Default |
| English | `en` | Supported |

### Spanish Mode (default)

- Image prompt uses **English** translation (DALL-E works better with English)
- Audio uses **Spanish** sentence
- Card shows Spanish + English translation

### English Mode

- Image and audio both use **English**
- Card shows English only (no translation line)

---

## Tips & Tricks

### 1. Use Inline Hints from SpanishDict

Already looked up a word? Use inline hints to nudge the AI:

```bash
# You found "banco" means "bench" on SpanishDict
chispa add "banco | bench, sitting"

# Specific slang meaning
chispa add "coger | vulgar Mexican, to have sex"
```

### 2. Batch Workflow with Auto-Cleanup

Create a text file as you encounter new words. Successfully processed words are automatically removed:

```bash
# Throughout the day, add words with hints
echo "desvelado | staying up late" >> today.txt
echo "madrugada | early morning" >> today.txt

# Process them - successful ones are removed automatically
chispa batch today.txt

# Only failed/skipped words remain in today.txt for retry
```

### 3. Handle Vulgar/Slang Words

Chispa handles explicit content appropriately:
- Definitions are direct (for learning purposes)
- Images are automatically sanitized (focuses on context, not explicit content)

```bash
chispa add "cabrón | the insult"
```

---

## Troubleshooting

### "Cannot connect to Anki"

1. Make sure Anki is running
2. Check AnkiConnect addon is installed
3. Verify AnkiConnect is enabled (Tools → Add-ons → AnkiConnect → Config)

### "No meanings found"

- Check spelling
- Try with/without accents (Chispa auto-corrects: `vispera` → `víspera`)
- Add context: `chispa add "word" -c "some context"`

### Image Generation Failed

- Check your OpenAI API key has DALL-E access
- Some prompts may be filtered; Chispa auto-sanitizes but edge cases exist

### Audio Generation Failed

- Check your ElevenLabs API key
- Verify you haven't exceeded your monthly quota

---

## File Locations

| File | Location |
|------|----------|
| Generated images | `<Anki Media Folder>/chispa_<word>.png` |
| Generated audio | `<Anki Media Folder>/chispa_<word>.mp3` |
| Configuration | `.env` in project root |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For word lookup and image generation |
| `ELEVENLABS_API_KEY` | Yes | For audio generation |
| `ELEVENLABS_VOICE_ID` | No | Custom voice (defaults to Spanish voice) |
| `ANKI_DECK_SPANISH` | No | Spanish deck name (default: `esp`) |
| `ANKI_DECK_ENGLISH` | No | English deck name (default: `en`) |
| `ANKI_NOTE_TYPE` | No | Note type name (default: `All-Purpose`) |
| `IMAGE_MODEL` | No | Image model (default: `gpt-image-1`) |

---

## Quick Reference

```bash
# Spanish word (default)
chispa add "palabra"

# Spanish with context (two ways)
chispa add "palabra" -c "hint"
chispa add "palabra | hint"

# English word
chispa add "word" --lang en

# Batch processing
chispa batch file.txt
chispa batch file.txt --lang en
```

### Batch File Syntax

```
word                    # Plain
word | hint             # With context hint
```
