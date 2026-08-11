"""Gemma NPU plugin — wires all NPU-accelerated text tools into Hermes."""

import logging

from . import schemas, tools

logger = logging.getLogger(__name__)

TOOLS = [
    ("summarize_text", schemas.SUMMARIZE_TEXT, tools.summarize_text),
    ("summarize_document", schemas.SUMMARIZE_DOCUMENT, tools.summarize_document),
    ("extract_from_webpage", schemas.EXTRACT_FROM_WEBPAGE, tools.extract_from_webpage),
    ("classify_text", schemas.CLASSIFY_TEXT, tools.classify_text),
    ("extract_json", schemas.EXTRACT_JSON, tools.extract_json),
    ("analyze_image", schemas.ANALYZE_IMAGE, tools.analyze_image),
    ("create_plan", schemas.CREATE_PLAN, tools.create_plan),
]


def register(ctx):
    """Register all NPU text tools with Hermes."""
    for name, schema, handler in TOOLS:
        ctx.register_tool(
            name=name,
            toolset="npu",
            schema=schema,
            handler=handler,
        )
    logger.info(
        "gemma-npu plugin registered: %d tools on toolset 'npu'",
        len(TOOLS),
    )
