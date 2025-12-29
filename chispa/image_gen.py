"""Image generation using OpenAI."""

import base64
from pathlib import Path

import requests
from openai import OpenAI

from .config import OPENAI_API_KEY, IMAGE_MODEL, get_anki_media_folder


def generate_safe_image_prompt(sentence: str) -> str:
    """
    Generate a safe, illustratable prompt from a sentence.
    Handles vulgar/explicit content by focusing on context.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You convert sentences into safe image prompts for educational flashcards. Focus on the SCENE and CONTEXT, not explicit content. Output only the image prompt, nothing else."
            },
            {
                "role": "user",
                "content": f"Create a safe, non-explicit image prompt that captures the context/scene of this sentence: \"{sentence}\"\n\nIf the sentence is explicit, focus on the setting, emotions, or non-explicit elements. The image should help remember the sentence without showing anything inappropriate."
            }
        ],
        temperature=0.3,
        max_tokens=100,
    )

    return response.choices[0].message.content.strip()


def generate_image(prompt: str, word: str) -> Path:
    """
    Generate an image based on the prompt and save it to Anki media folder.

    Args:
        prompt: The English sentence to visualize (use English for better results)
        word: The vocabulary word (used for filename)

    Returns:
        Path to the saved image file
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Generate a safe image prompt (handles vulgar/explicit content)
    safe_prompt = generate_safe_image_prompt(prompt)

    # Enhance the prompt for better image generation
    enhanced_prompt = f"Create a clear, simple illustration that depicts: {safe_prompt}. Style: clean, educational, suitable for a flashcard. No text in the image."

    response = client.images.generate(
        model=IMAGE_MODEL,
        prompt=enhanced_prompt,
        size="1024x1024",
        quality="auto",
        n=1,
    )

    # Get the image URL or base64 data
    image_data = response.data[0]

    # Determine output path
    media_folder = get_anki_media_folder()
    output_path = media_folder / f"chispa_{word}.png"

    if hasattr(image_data, "b64_json") and image_data.b64_json:
        # Save base64 encoded image
        image_bytes = base64.b64decode(image_data.b64_json)
        output_path.write_bytes(image_bytes)
    elif hasattr(image_data, "url") and image_data.url:
        # Download from URL
        response = requests.get(image_data.url, timeout=30)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    else:
        raise ValueError("No image data received from OpenAI")

    return output_path


def get_image_reference(word: str) -> str:
    """Get the Anki-compatible image reference for a word."""
    return f'<img src="chispa_{word}.png">'


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    prompt = sys.argv[1] if len(sys.argv) > 1 else "A person sitting on a bench in a park"
    word = sys.argv[2] if len(sys.argv) > 2 else "test"

    print(f"Generating image for: {prompt}")
    path = generate_image(prompt, word)
    print(f"Saved to: {path}")
    print(f"Anki reference: {get_image_reference(word)}")
