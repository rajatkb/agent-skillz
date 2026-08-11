# Gemma NPU Tools — Reference

The `gemma-npu` plugin (toolset `npu`) provides 5 tools that run Gemma4-on-NPU for text processing, offloading work from DeepSeek to save API costs.

All tools require FLM to be running (`bash ~/.hermes/scripts/flm-up.sh`).

## Common Response Structure

Every tool returns JSON with these keys:

```
response          — the Gemma4 output text
input_tokens      — tokens consumed by Gemma4
output_tokens     — tokens produced by Gemma4
elapsed_seconds   — wall-clock time
deepseek_input_cost   — $ this input would cost on DeepSeek
deepseek_output_cost  — $ this output would cost on DeepSeek
deepseek_total_cost   — $ total if run on DeepSeek
model                 — the FLM model used
```

DeepSeek pricing: $0.14/M input, $0.28/M output.

---

## When to offload (routing heuristic)

Gemma4-on-NPU is an **output optimizer**: use it for responses that are mostly
re-rendering content that is ALREADY in the input — extraction, summarization,
structured parsing, document/page reading, image description. These
retrieval-style long outputs would otherwise be long DeepSeek output tokens at
$0.28/M; locally they're nearly free. Rule of thumb: if the correct answer is
present in the input and the model only needs to find and restate it, the NPU
model will do fine.

Do NOT route: deep reasoning, multi-step synthesis, coding, or factual recall
from the model's own knowledge — those need DeepSeek. Small NPU models
hallucinate and are poor at long-form generation from memory (see the
amd-npu size table: <1B is bad at long-form writing and factual recall).

---

## 1. `summarize_text`

Condense or extract from a block of text.

**Parameters:**
- `text` (required): The content to analyze.
- `instruction` (optional, default `"Summarize the key points concisely."`): What to extract.
- `max_output_tokens` (optional, default 512, max 2048): Output length cap.

**Example:**
```
summarize_text(
  text="Long article text...",
  instruction="Extract all technical specifications mentioned"
)
```

**Pitfalls:**
- Input is truncated at ~30K chars. If the text is larger, chunk it or use `summarize_document`.
- For data that's already in DeepSeek's context, call this BEFORE DeepSeek writes a long response — the summary replaces the raw text.

---

## 2. `summarize_document`

Read a file from disk and have Gemma4 analyze it.

**Parameters:**
- `file_path` (required): Absolute path to the file.
- `instruction` (optional, default `"Summarize the contents concisely."`).
- `max_output_tokens` (optional, default 1024, max 4096).

**Example:**
```
summarize_document(
  file_path="/home/<user>/project/debug.log",
  instruction="List all error messages with their timestamps"
)
```

**Pitfalls:**
- Only text files (auto-fallback from UTF-8 to latin-1). For PDFs, extract text first.
- Input truncated at ~30K chars. For larger files, the head and tail are preserved with a truncation notice in the middle.

---

## 3. `extract_from_webpage`

Fetch a URL, strip HTML, and have Gemma4 answer a question about the content.

**Parameters:**
- `url` (required): The URL to fetch.
- `instruction` (optional, default `"Summarize the main content of this page."`).
- `max_output_tokens` (optional, default 1024, max 4096).

**Example:**
```
extract_from_webpage(
  url="https://fastflowlm.com/docs/models/gemma/",
  instruction="What models are listed and which have vision support?"
)
```

**Pitfalls:**
- Uses `urllib` (stdlib) — no JavaScript rendering. For SPAs or JS-heavy pages, use `browser_navigate` first, then feed the visible text to `summarize_text`.
- HTML stripping is basic (regex-based). May leave partial entities or navigation text.
- 15s timeout on fetch. Slow pages may fail.

---

## 4. `classify_text`

Classify text into one or more predefined categories.

**Parameters:**
- `text` (required): Content to classify.
- `categories` (required): Comma-separated list. e.g. `"bug, feature, docs, question"`.
- `return_confidence` (optional, default false): Ask Gemma4 for confidence %.
- `max_output_tokens` (optional, default 256, max 1024).

**Example:**
```
classify_text(
  text="The login button doesn't work when clicking rapidly",
  categories="bug, feature, question, other"
)
```

---

## 5. `extract_json`

Extract structured JSON from unstructured text.

**Parameters:**
- `text` (required): Raw text to parse.
- `schema_description` (required): Describe what to extract.
- `max_output_tokens` (optional, default 1024, max 4096).

**Example:**
```
extract_json(
  text="Name: John, Email: john@example.com, Phone: 555-0100",
  schema_description="Extract {name, email, phone} as JSON"
)
```

**Response includes:**
- `valid_json` (bool): whether Gemma4's output parsed as valid JSON.
- If Gemma4 wraps the output in markdown code fences, the handler strips them.
