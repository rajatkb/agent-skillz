"""Tool handlers for gemma-npu — all NPU-accelerated text processing tools."""

import base64
import json
import logging
import os
import re
import subprocess
import time
import urllib.request
import urllib.error

from openai import OpenAI

logger = logging.getLogger(__name__)

# ── FLM server config ───────────────────────────────────────
FLM_HOST = os.environ.get("FLM_HOST", "localhost")
FLM_PORT = os.environ.get("FLM_PORT", "50001")
FLM_MODEL = os.environ.get("FLM_MODEL", "gemma4-it:e2b")
FLM_BASE = f"http://{FLM_HOST}:{FLM_PORT}"

# DeepSeek pricing (v4 Flash)
DS_INPUT_COST_PER_M = 0.14   # $0.14 per 1M input tokens
DS_OUTPUT_COST_PER_M = 0.28  # $0.28 per 1M output tokens

# Max input chars to send to Gemma4 per call. Above this, we truncate.
MAX_INPUT_CHARS = 30_000


# ── Shared helpers ───────────────────────────────────────────

def _build_client() -> OpenAI:
    return OpenAI(base_url=f"{FLM_BASE}/v1", api_key="dummykey")


def _compute_costs(in_tokens: int, out_tokens: int) -> dict:
    """Return what this would have cost on DeepSeek."""
    return {
        "deepseek_input_cost": round((in_tokens / 1_000_000) * DS_INPUT_COST_PER_M, 6),
        "deepseek_output_cost": round((out_tokens / 1_000_000) * DS_OUTPUT_COST_PER_M, 6),
        "deepseek_total_cost": round(
            (in_tokens / 1_000_000) * DS_INPUT_COST_PER_M +
            (out_tokens / 1_000_000) * DS_OUTPUT_COST_PER_M, 6
        ),
        "model": FLM_MODEL,
    }


def _call_flm(messages: list, max_tokens: int, temperature: float = 0.3) -> dict:
    """Send messages to FLM, return response + token stats.

    Returns dict with keys: response, input_tokens, output_tokens,
    elapsed_seconds, plus cost breakdown.
    """
    client = _build_client()
    start = time.time()
    resp = client.chat.completions.create(
        model=FLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.time() - start

    result = resp.choices[0].message.content.strip()
    usage = resp.usage
    in_tokens = usage.prompt_tokens if usage else 0
    out_tokens = usage.completion_tokens if usage else 0

    data = {
        "response": result,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "elapsed_seconds": round(elapsed, 1),
    }
    data.update(_compute_costs(in_tokens, out_tokens))
    return data


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to stay within Gemma4's context window."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + f"\n\n[... {len(text) - max_chars} chars truncated ...]\n\n"
        + text[-half:]
    )


def _read_file(path: str) -> str:
    """Read a text file, return content."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    # Try UTF-8 first, fall back to latin-1 for binary-ish files
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return f.read()


def _fetch_url(url: str) -> str:
    """Fetch a URL and return the text content (HTML stripped minimally)."""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            # Try to decode based on content-type charset, default utf-8
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            else:
                charset = "utf-8"
            try:
                text = raw.decode(charset)
            except (UnicodeDecodeError, LookupError):
                text = raw.decode("utf-8", errors="replace")
            return text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}")


# ── Tool handlers ────────────────────────────────────────────

def summarize_text(args: dict, **kwargs) -> str:
    """Summarize or process a block of text using Gemma4 on NPU."""
    text = args.get("text", "").strip()
    instruction = args.get("instruction", "Summarize the key points concisely.")
    max_tokens = min(args.get("max_output_tokens", 512), 2048)

    if not text:
        return json.dumps({"error": "No text provided"})

    truncated = _truncate(text)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a text analysis assistant running on-device (NPU). "
                "Analyze the given text and follow the user's instruction precisely. "
                "Be concise and accurate. Do not add preamble or meta-commentary."
            ),
        },
        {
            "role": "user",
            "content": f"# Instruction\n{instruction}\n\n# Text\n{truncated}",
        },
    ]

    try:
        result = _call_flm(messages, max_tokens)
        result["text_original_chars"] = len(text)
        result["text_processed_chars"] = len(truncated)
        logger.info(
            "summarize_text: %d chars → %d out tokens in %.1fs | input_tokens=%d output_tokens=%d",
            len(text), result["output_tokens"], result["elapsed_seconds"],
            result["input_tokens"], result["output_tokens"],
        )
        return json.dumps(result)
    except Exception as e:
        logger.error("summarize_text failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


def summarize_document(args: dict, **kwargs) -> str:
    """Read a file and summarize/extract from it using Gemma4 on NPU."""
    file_path = args.get("file_path", "").strip()
    instruction = args.get("instruction", "Summarize the contents concisely.")
    max_tokens = min(args.get("max_output_tokens", 1024), 4096)

    if not file_path:
        return json.dumps({"error": "No file_path provided"})

    try:
        content = _read_file(file_path)
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to read file: {e}"})

    truncated = _truncate(content)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a document analysis assistant running on-device (NPU). "
                "Read the provided document and follow the user's instruction. "
                "Be concise and focus on what was asked. Do not add preamble."
            ),
        },
        {
            "role": "user",
            "content": f"# Instruction\n{instruction}\n\n# Document ({file_path})\n{truncated}",
        },
    ]

    try:
        result = _call_flm(messages, max_tokens)
        result["file"] = file_path
        result["file_size_chars"] = len(content)
        logger.info(
            "summarize_document: %s (%d chars) → %d out tokens in %.1fs",
            file_path, len(content), result["output_tokens"], result["elapsed_seconds"],
        )
        return json.dumps(result)
    except Exception as e:
        logger.error("summarize_document failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


def extract_from_webpage(args: dict, **kwargs) -> str:
    """Fetch a URL and analyze the content using Gemma4 on NPU."""
    url = args.get("url", "").strip()
    instruction = args.get("instruction", "Summarize the main content of this page.")
    max_tokens = min(args.get("max_output_tokens", 1024), 4096)

    if not url:
        return json.dumps({"error": "No url provided"})

    try:
        raw_html = _fetch_url(url)
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Crude HTML-to-text: strip tags, collapse whitespace
    # This is intentionally simple — Gemma4 can handle the rest
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Decode HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")

    if not text.strip():
        return json.dumps({"error": "No text content extracted from URL"})

    truncated = _truncate(text)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a web research assistant running on-device (NPU). "
                "Analyze the webpage content below and follow the user's instruction. "
                "Be concise and cite specific details from the page. Do not add preamble."
            ),
        },
        {
            "role": "user",
            "content": f"# URL\n{url}\n\n# Instruction\n{instruction}\n\n# Page Content\n{truncated}",
        },
    ]

    try:
        result = _call_flm(messages, max_tokens)
        result["url"] = url
        result["page_text_chars"] = len(text)
        logger.info(
            "extract_from_webpage: %s (%d chars) → %d out tokens in %.1fs",
            url, len(text), result["output_tokens"], result["elapsed_seconds"],
        )
        return json.dumps(result)
    except Exception as e:
        logger.error("extract_from_webpage failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


def classify_text(args: dict, **kwargs) -> str:
    """Classify text into categories using Gemma4 on NPU."""
    text = args.get("text", "").strip()
    categories = args.get("categories", "").strip()
    return_confidence = args.get("return_confidence", False)
    max_tokens = min(args.get("max_output_tokens", 256), 1024)

    if not text:
        return json.dumps({"error": "No text provided"})
    if not categories:
        return json.dumps({"error": "No categories provided"})

    confidence_instruction = (
        " For each category, also provide a confidence estimate (0-100%)."
        if return_confidence else ""
    )

    truncated = _truncate(text)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a text classification assistant running on-device (NPU). "
                "Classify the given text into the provided categories. "
                "Respond with the category label(s) only, unless instructed otherwise."
                f"{confidence_instruction}"
            ),
        },
        {
            "role": "user",
            "content": f"# Categories\n{categories}\n\n# Text\n{truncated}",
        },
    ]

    try:
        result = _call_flm(messages, max_tokens)
        result["categories"] = categories
        result["text_chars"] = len(text)
        logger.info(
            "classify_text: %d chars → %d out tokens in %.1fs",
            len(text), result["output_tokens"], result["elapsed_seconds"],
        )
        return json.dumps(result)
    except Exception as e:
        logger.error("classify_text failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


def extract_json(args: dict, **kwargs) -> str:
    """Extract structured JSON from unstructured text using Gemma4 on NPU."""
    text = args.get("text", "").strip()
    schema_desc = args.get("schema_description", "").strip()
    max_tokens = min(args.get("max_output_tokens", 1024), 4096)

    if not text:
        return json.dumps({"error": "No text provided"})
    if not schema_desc:
        return json.dumps({"error": "No schema_description provided"})

    truncated = _truncate(text)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a data extraction assistant running on-device (NPU). "
                "Extract structured JSON data from the provided text. "
                "Follow the schema description precisely. "
                "Respond with ONLY valid JSON — no explanatory text, no markdown fences."
            ),
        },
        {
            "role": "user",
            "content": f"# Schema\n{schema_desc}\n\n# Text to extract from\n{truncated}",
        },
    ]

    try:
        result = _call_flm(messages, max_tokens)
        result["schema"] = schema_desc
        result["text_chars"] = len(text)
        # Try to validate JSON was actually returned
        try:
            # Strip markdown fences if Gemma4 ignored instructions
            cleaned = result["response"]
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            json.loads(cleaned)
            result["valid_json"] = True
        except (json.JSONDecodeError, IndexError):
            result["valid_json"] = False
        logger.info(
            "extract_json: %d chars → %d out tokens in %.1fs (valid_json=%s)",
            len(text), result["output_tokens"], result["elapsed_seconds"],
            result["valid_json"],
        )
        return json.dumps(result)
    except Exception as e:
        logger.error("extract_json failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


# ── Image analysis (formerly gemma-vision) ───────────────────

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _encode_image(image_path: str) -> tuple[str, str]:
    """Read image, return (base64_data, mime_type)."""
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {ext}. Supported: {', '.join(ALLOWED_EXTENSIONS)}")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    mime = MIME_MAP.get(ext, "image/png")
    return b64, mime


def analyze_image(args: dict, **kwargs) -> str:
    """Analyze an image using Gemma 4 E4B on the NPU."""
    image_path = args.get("image_path", "").strip()
    question = args.get("question", "Describe this image in detail.")
    detail = args.get("detail", 280)

    if not image_path:
        return json.dumps({"error": "No image_path provided"})

    if not os.path.isfile(image_path):
        return json.dumps({"error": f"Image not found: {image_path}"})

    try:
        b64, mime = _encode_image(image_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to read image: {e}"})

    if detail not in (70, 140, 280, 560, 1120):
        detail = 280

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

    try:
        client = OpenAI(
            base_url=f"http://{FLM_HOST}:{FLM_PORT}/v1",
            api_key="dummykey",
        )
        start = time.time()
        response = client.chat.completions.create(
            model=FLM_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        elapsed = time.time() - start
        result = response.choices[0].message.content.strip()

        # Count tokens from response metadata
        usage = response.usage
        in_tokens = usage.prompt_tokens if usage else 0
        out_tokens = usage.completion_tokens if usage else 0

        data = {
            "response": result,
            "image": image_path,
            "question": question,
            "elapsed_seconds": round(elapsed, 1),
            "model": FLM_MODEL,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
        }
        data.update(_compute_costs(in_tokens, out_tokens))

        logger.info(
            "analyze_image: %s — %d chars in %.1fs | tokens=%d/%d",
            image_path, len(result), elapsed, in_tokens, out_tokens,
        )
        return json.dumps(data)

    except Exception as e:
        logger.error("analyze_image FLM call failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})


# ── Planning mode ────────────────────────────────────────────

_PLANNER_PROMPT = """You are a planning assistant running on-device (NPU). Your job is to decompose a user's goal into a structured, actionable plan.

The plan is a JSON object with this schema:
{
  "plan_name": "short descriptive name",
  "summary": "one-line summary of the approach",
  "steps": [
    {
      "step_id": 1,
      "description": "what this step does",
      "tool": "tool_name or 'self' for steps requiring DeepSeek's own reasoning",
      "expected_args": {"param": "what to pass"},
      "complexity": "simple" | "complex",
      "recommended_executor": "npu" | "deepseek",
      "depends_on": []
    }
  ],
  "estimated_complexity": "low" | "medium" | "high",
  "reasoning": "why you chose this decomposition"
}

Rules:
1. Break the goal into the SMALLEST reasonable steps. Each step should do ONE thing.
2. Mark steps as "simple" if they can be done by a local NPU tool (summarize_text, summarize_document, extract_from_webpage, classify_text, extract_json, analyze_image, web_search, read_file, terminal, browser_navigate, etc).
3. Mark steps as "complex" if they need reasoning, judgment, conditional logic, multi-step synthesis, or creative problem-solving — those should be executed by DeepSeek (recommended_executor = "deepseek", tool = "self").
4. Set depends_on to the step_ids that must complete before this step can run. Use [] for independent steps.
5. If the goal is very simple (1-2 steps), just produce a minimal plan.
6. If context is provided, incorporate those details (file paths, constraints, etc.) into the step args.
7. Respond with ONLY the JSON plan — no preamble, no markdown fences, no commentary."""


def create_plan(args: dict, **kwargs) -> str:
    """Decompose a goal into a structured tool-call plan using Gemma4 on NPU."""
    goal = args.get("goal", "").strip()
    context = args.get("context", "").strip()
    previous_plan = args.get("previous_plan", "").strip()
    correction = args.get("correction", "").strip()

    if not goal:
        return json.dumps({"error": "No goal provided"})

    # Build the user message
    parts = [f"# Goal\n{goal}"]
    if context:
        parts.append(f"# Context\n{context}")
    if previous_plan and correction:
        parts.append(f"# Previous Plan (to revise)\n{previous_plan}")
        parts.append(f"# Correction Needed\n{correction}")
    elif previous_plan:
        parts.append(f"# Previous Plan (to revise)\n{previous_plan}")
    if correction and not previous_plan:
        parts.append(f"# Correction Needed\n{correction}")

    user_message = "\n\n".join(parts)

    messages = [
        {"role": "system", "content": _PLANNER_PROMPT},
        {"role": "user", "content": user_message},
    ]

    try:
        client = _build_client()
        start = time.time()
        response = client.chat.completions.create(
            model=FLM_MODEL,
            messages=messages,
            temperature=0.2,  # low temp for structured output
            max_tokens=4096,
        )
        elapsed = time.time() - start
        result = response.choices[0].message.content.strip()

        usage = response.usage
        in_tokens = usage.prompt_tokens if usage else 0
        out_tokens = usage.completion_tokens if usage else 0

        # Validate it's parseable JSON
        cleaned = result
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            plan_data = json.loads(cleaned)
            valid = True
        except json.JSONDecodeError:
            plan_data = {"raw_response": result}
            valid = False

        data = {
            "plan": plan_data,
            "valid_json": valid,
            "model": FLM_MODEL,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "elapsed_seconds": round(elapsed, 1),
        }
        data.update(_compute_costs(in_tokens, out_tokens))

        logger.info(
            "create_plan: goal=%s — %d steps in %.1fs | valid=%s | tokens=%d/%d",
            goal[:80],
            len(plan_data.get("steps", [])) if isinstance(plan_data, dict) else 0,
            elapsed, valid, in_tokens, out_tokens,
        )
        return json.dumps(data)

    except Exception as e:
        logger.error("create_plan FLM call failed: %s", e)
        return json.dumps({"error": f"FLM request failed: {e}"})
