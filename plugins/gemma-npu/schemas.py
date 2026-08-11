"""Tool schemas for gemma-npu plugin — what DeepSeek sees for each tool."""

SUMMARIZE_TEXT = {
    "name": "summarize_text",
    "description": (
        "Summarize, condense, or extract key points from text using Gemma 4 on NPU. "
        "Use this to offload heavy reading from DeepSeek — Gemma4 compresses text to its essence. "
        "Returns the summary plus token counts showing savings vs DeepSeek."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text content to summarize or process.",
            },
            "instruction": {
                "type": "string",
                "description": "What to do with the text. Examples: 'Summarize in 3 bullet points', 'Extract key facts and figures', 'TL;DR in one sentence'. Default: 'Summarize the key points concisely.'",
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response (default: 512, max: 2048). Lower = faster.",
                "default": 512,
            },
        },
        "required": ["text"],
    },
}

SUMMARIZE_DOCUMENT = {
    "name": "summarize_document",
    "description": (
        "Read a file from disk and summarize/extract from it using Gemma 4 on NPU. "
        "Supports text files, logs, code files, markdown. Use this to quickly understand "
        "a file's content without loading it into DeepSeek's context. "
        "Returns the summary plus token savings vs DeepSeek."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file on disk (e.g., '/home/rajat-g14/project/log.txt').",
            },
            "instruction": {
                "type": "string",
                "description": "What to look for or extract. Examples: 'Summarize the error messages', 'What are the main findings?', 'List all function definitions'. Default: 'Summarize the contents concisely.'",
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response (default: 1024, max: 4096). Higher for long documents.",
                "default": 1024,
            },
        },
        "required": ["file_path"],
    },
}

EXTRACT_FROM_WEBPAGE = {
    "name": "extract_from_webpage",
    "description": (
        "Fetch a webpage, extract its text content, and have Gemma 4 on NPU answer "
        "a question or summarize it. Use this for quick web research — Gemma4 reads "
        "the page and returns only what's relevant. "
        "Returns the answer plus token savings vs DeepSeek."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch and analyze.",
            },
            "instruction": {
                "type": "string",
                "description": "What to look for. Examples: 'What are the key features?', 'Summarize this article', 'Find the pricing info', 'Extract all links and their descriptions'. Default: 'Summarize the main content of this page.'",
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response (default: 1024, max: 4096).",
                "default": 1024,
            },
        },
        "required": ["url"],
    },
}

CLASSIFY_TEXT = {
    "name": "classify_text",
    "description": (
        "Classify or analyze text into predefined categories using Gemma 4 on NPU. "
        "Useful for sentiment analysis, topic classification, or any categorization task. "
        "Returns the classification result plus token savings vs DeepSeek."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to classify.",
            },
            "categories": {
                "type": "string",
                "description": "Comma-separated list of categories. Example: 'positive, negative, neutral' or 'bug, feature, docs, question' or 'urgent, normal, low'.",
            },
            "return_confidence": {
                "type": "boolean",
                "description": "If true, Gemma4 will also provide a confidence estimate for its classification.",
                "default": False,
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response (default: 256).",
                "default": 256,
            },
        },
        "required": ["text", "categories"],
    },
}

EXTRACT_JSON = {
    "name": "extract_json",
    "description": (
        "Extract structured JSON data from unstructured text using Gemma 4 on NPU. "
        "Give it a schema description and raw text — Gemma4 returns clean JSON. "
        "Use this for parsing logs, forms, tables, or any semi-structured content. "
        "Returns the JSON data plus token savings vs DeepSeek."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The raw text to extract data from.",
            },
            "schema_description": {
                "type": "string",
                "description": "Description of the structure to extract. Examples: '{name, email, phone}' or 'list of objects with date, title, status fields' or 'extract all error codes with line numbers'. Be specific.",
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response (default: 1024, max: 4096).",
                "default": 1024,
            },
        },
        "required": ["text", "schema_description"],
    },
}

ANALYZE_IMAGE = {
    "name": "analyze_image",
    "description": (
        "Analyze an image using Gemma 4 E4B running locally on the NPU. "
        "Sends ONLY the image + question to the local model — NO conversation context "
        "is leaked. Use this for image understanding, OCR/text extraction from images, "
        "UI/screenshot analysis, object detection, document/PDF page parsing, chart/table "
        "comprehension, or any visual QA. "
        "The model can read text, identify objects/colors, describe scenes, and answer "
        "questions about image content. "
        "Context is MINIMAL — a short system prompt + the image + your question only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": (
                    "Absolute path to the image file on the Windows or WSL filesystem "
                    "(e.g., '/mnt/c/Users/RAJAT/Downloads/screenshot.png' or "
                    "'/home/rajat-g14/image.jpg'). Supports PNG, JPG, JPEG, WebP, BMP."
                ),
            },
            "question": {
                "type": "string",
                "description": (
                    "Question or instruction about the image. Examples: "
                    "'Read all text in this image', 'Describe what you see', "
                    "'What UI elements are on this screen?', 'Extract the table data', "
                    "'What colors are used?' Default: 'Describe this image in detail.'"
                ),
            },
            "detail": {
                "type": "integer",
                "enum": [70, 140, 280, 560, 1120],
                "description": (
                    "Visual token budget. Higher = more detail but slower. "
                    "70 = fast/coarse, 280 = default/good balance, "
                    "560 = detailed text extraction, 1120 = max detail (slowest). "
                    "Default: 280."
                ),
            },
        },
        "required": ["image_path"],
    },
}

CREATE_PLAN = {
    "name": "create_plan",
    "description": (
        "Decompose a complex goal into a structured, ordered plan of tool calls "
        "suitable for multi-step execution. Gemma 4 on NPU analyzes the goal and "
        "context, then produces a plan as a JSON array of sequential steps. Each "
        "step specifies which tool to use (or 'deepseek_reasoning' for steps that "
        "need DeepSeek's reasoning), expected arguments, a complexity rating, "
        "and inter-step dependencies. When a 'correction' is provided, Gemma4 "
        "revises the previous plan incorporating the feedback. "
        "DeepSeek reviews the plan, approves or rejects it, and executes the steps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "The primary goal or task to break down into steps.",
            },
            "context": {
                "type": "string",
                "description": "Background info, constraints, file paths, or any context relevant to planning. Default: ''.",
                "default": "",
            },
            "previous_plan": {
                "type": "string",
                "description": "The previous plan JSON (as string) if this is a revision pass. Include so Gemma4 can see what it generated before and correct it. Default: ''.",
                "default": "",
            },
            "correction": {
                "type": "string",
                "description": "Feedback from DeepSeek on what was wrong with the previous plan and what to fix. Only set on revision passes. Default: ''.",
                "default": "",
            },
        },
        "required": ["goal"],
    },
}
