"""Validation for teacher-authored structured note content.

Two content formats are supported as an alternative to a Google Drive link:
- "json": a block list following the schema documented below, rendered by
  templates/materials/view.html.
- "html": free-form HTML, sanitized here before storage so it can be
  rendered with `|safe` later without re-checking it.
"""
import json

import bleach

ALLOWED_BLOCK_TYPES = {"heading", "paragraph", "list", "table", "qa", "code", "image"}

ALLOWED_HTML_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4",
    "strong", "b", "em", "i", "u",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "code", "pre",
    "a", "img", "span", "div",
]
ALLOWED_HTML_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt"],
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _is_nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def validate_content_blocks(raw_json):
    """Parse and validate teacher-submitted block JSON.

    Returns the parsed list of blocks on success. Raises ValueError with a
    human-readable message (safe to flash to the user) on any problem.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).")

    _require(isinstance(data, dict) and isinstance(data.get("blocks"), list),
              'JSON must be an object with a "blocks" array, e.g. {"blocks": [...]}.')
    blocks = data["blocks"]
    _require(len(blocks) > 0, "At least one block is required.")

    for i, block in enumerate(blocks, start=1):
        _require(isinstance(block, dict) and "type" in block, f'Block {i} is missing a "type".')
        block_type = block["type"]
        _require(block_type in ALLOWED_BLOCK_TYPES,
                  f'Block {i} has unknown type "{block_type}". '
                  f"Allowed types: {', '.join(sorted(ALLOWED_BLOCK_TYPES))}.")

        if block_type == "heading":
            _require(_is_nonempty_str(block.get("text")), f"Block {i} (heading) needs non-empty \"text\".")
            level = block.get("level", 2)
            _require(isinstance(level, int) and 1 <= level <= 4, f"Block {i} (heading) \"level\" must be an integer 1-4.")
        elif block_type == "paragraph":
            _require(_is_nonempty_str(block.get("text")), f"Block {i} (paragraph) needs non-empty \"text\".")
        elif block_type == "list":
            items = block.get("items")
            _require(isinstance(items, list) and len(items) > 0, f"Block {i} (list) needs a non-empty \"items\" array.")
            _require(all(_is_nonempty_str(item) for item in items), f"Block {i} (list) items must all be non-empty strings.")
            style = block.get("style", "bullet")
            _require(style in ("bullet", "number"), f'Block {i} (list) "style" must be "bullet" or "number".')
        elif block_type == "table":
            headers = block.get("headers")
            rows = block.get("rows")
            _require(isinstance(headers, list) and len(headers) > 0, f"Block {i} (table) needs a non-empty \"headers\" array.")
            _require(isinstance(rows, list) and len(rows) > 0, f"Block {i} (table) needs a non-empty \"rows\" array.")
            for r, row in enumerate(rows, start=1):
                _require(isinstance(row, list) and len(row) == len(headers),
                          f"Block {i} (table) row {r} must have {len(headers)} cell(s) to match the headers.")
        elif block_type == "qa":
            _require(_is_nonempty_str(block.get("question")), f"Block {i} (qa) needs non-empty \"question\".")
            _require(_is_nonempty_str(block.get("answer")), f"Block {i} (qa) needs non-empty \"answer\".")
        elif block_type == "code":
            _require(_is_nonempty_str(block.get("text")), f"Block {i} (code) needs non-empty \"text\".")
        elif block_type == "image":
            url = block.get("url")
            _require(_is_nonempty_str(url) and url.strip().startswith(("http://", "https://")),
                      f"Block {i} (image) needs a \"url\" starting with http:// or https://.")

    return blocks


def sanitize_note_html(raw_html):
    """Strip any tag/attribute not on the allowlist. Safe to store and later render with |safe."""
    return bleach.clean(raw_html, tags=ALLOWED_HTML_TAGS, attributes=ALLOWED_HTML_ATTRS, strip=True)
