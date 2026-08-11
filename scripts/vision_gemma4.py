#!/usr/bin/env python3
"""
Gemma 4 E4B IT — Image Understanding via FLM NPU

Usage:
  python3 ~/.hermes/scripts/vision_gemma4.py --image /path/to/image.jpg [--question "What is this?"] [--detail 280]

Context is kept MINIMAL — only the system prompt + image + question.
No conversation history is injected. Stateless single-turn.
"""

import argparse
import base64
import json
import os
import sys
import time
from openai import OpenAI

# FLM server config — uses port 50001 as configured
FLM_HOST = os.environ.get("FLM_HOST", "172.29.192.1")  # WSL gateway IP
FLM_PORT = os.environ.get("FLM_PORT", "50001")
FLM_MODEL = "gemma4-it:e4b"

# Token budgets for images (70, 140, 280, 560, 1120 — more tokens = more detail)
# Default 280 is a good balance for most images
IMAGE_TOKEN_BUDGETS = [70, 140, 280, 560, 1120]


def encode_image(image_path: str) -> str:
    """Read and base64-encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def infer_image_mime(image_path: str) -> str:
    """Guess MIME type from file extension."""
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }
    return mime_map.get(ext, "image/png")


def analyze_image(
    image_path: str,
    question: str = "Describe this image in detail.",
    detail_tokens: int = 280,
    stream: bool = False,
    temperature: float = 0.3,
) -> str:
    """
    Send image + question to Gemma 4 E4B via FLM.
    Returns the model's text response.
    Context is ONLY: system prompt + image + question. Nothing else.
    """
    if not os.path.isfile(image_path):
        return f"ERROR: Image file not found: {image_path}"

    mime = infer_image_mime(image_path)
    b64 = encode_image(image_path)

    client = OpenAI(
        base_url=f"http://{FLM_HOST}:{FLM_PORT}/v1",
        api_key="dummykey",
    )

    # Minimal system prompt — just sets the role
    system_prompt = (
        "You are a vision assistant. Analyze images and respond concisely. "
        "Answer the user's question about the image directly without preamble."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64}",
                    },
                },
                {"type": "text", "text": question},
            ],
        },
    ]

    kwargs = {
        "model": FLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }

    if stream:
        kwargs["stream"] = True

    try:
        response = client.chat.completions.create(**kwargs)

        if stream:
            collected = []
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    collected.append(content)
                    print(content, end="", flush=True)
            print()
            return "".join(collected)
        else:
            return response.choices[0].message.content.strip()

    except Exception as e:
        return f"ERROR: FLM request failed: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze an image using Gemma 4 E4B on the NPU"
    )
    parser.add_argument(
        "--image", "-i", required=True, help="Path to the image file"
    )
    parser.add_argument(
        "--question", "-q",
        default="Describe this image in detail.",
        help="Question about the image (default: describe)",
    )
    parser.add_argument(
        "--detail", "-d",
        type=int,
        default=280,
        choices=IMAGE_TOKEN_BUDGETS,
        help="Visual token budget: 70(fast/coarse) to 1120(slow/detailed). Default: 280",
    )
    parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Stream the response as it's generated",
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.3,
        help="Sampling temperature (default: 0.3 for factual answers)",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output result as JSON (for programmatic use)",
    )

    args = parser.parse_args()

    start = time.time()
    result = analyze_image(
        image_path=args.image,
        question=args.question,
        detail_tokens=args.detail,
        stream=args.stream,
        temperature=args.temperature,
    )
    elapsed = time.time() - start

    if args.json:
        output = {
            "image": args.image,
            "question": args.question,
            "response": result,
            "elapsed_seconds": round(elapsed, 2),
            "model": FLM_MODEL,
        }
        print(json.dumps(output, indent=2))
    else:
        if not args.stream:
            print(result)
        # Timing info on stderr so it doesn't pollute the response
        print(f"\n[⚡ Analyzed in {elapsed:.1f}s via {FLM_MODEL} on NPU]",
              file=sys.stderr)


if __name__ == "__main__":
    main()
