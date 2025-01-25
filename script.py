from fastapi import FastAPI, Form, UploadFile, File
import pymupdf
from typing import List, Tuple
from io import BytesIO
import re
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import parsers

app = FastAPI()


def find_underline_segments(page, span):
    """
    Find all underline segments within a span's bbox.
    Returns list of (start_x, end_x) coordinates of underlines.
    """
    x0, y0, x1, y1 = span["bbox"]
    text_height = y1 - y0

    segments = []
    paths = page.get_drawings()

    for path in paths:
        path_rect = path.get("rect")
        if not path_rect:
            continue

        px0, py0, px1, py1 = path_rect
        path_height = py1 - py0

        # Basic filtering
        is_thin = path_height < text_height * 0.1
        is_at_bottom = abs(py0 - y1) < text_height * 0.2

        if is_thin and is_at_bottom:
            # Find overlap with span
            overlap_start = max(x0, px0)
            overlap_end = min(x1, px1)

            if overlap_end > overlap_start:
                segments.append((overlap_start, overlap_end))

    return segments


def process_span_with_underlines(text, underline_segments):
    """
    Process a span of text, applying underline tags to appropriate portions.
    """
    if not underline_segments:
        return "".join(char["c"] for char in text)

    # Create a list of characters with their x-positions
    chars = []
    for char in text:
        bbox = char["bbox"]
        char_x = (bbox[0] + bbox[2]) / 2.0
        chars.append((char["c"], char_x))

    # Mark which characters should be underlined
    underlined = [False] * len(chars)
    for start_x, end_x in underline_segments:
        for i, (ch, char_x) in enumerate(chars):
            if start_x <= char_x <= end_x:
                underlined[i] = True

    # Build result with appropriate tags
    result = []
    current_text = []
    current_underlined = underlined[0] if underlined else False

    for i, (char, _) in enumerate(chars):
        if i > 0 and underlined[i] != current_underlined:
            # Format changes, output accumulated text
            text_segment = "".join(current_text)
            if current_underlined:
                text_segment = f"<u>{text_segment}</u>"
            result.append(text_segment)
            current_text = []
            current_underlined = underlined[i]
        current_text.append(char)

    # Handle last segment
    if current_text:
        text_segment = "".join(current_text)
        if current_underlined:
            text_segment = f"<u>{text_segment}</u>"
        result.append(text_segment)

    return "".join(result)


def extract_text_blocks(page):
    """
    Extract text blocks with formatting from a single page.
    Maintains newline separation between blocks.
    """
    blocks = []
    current_block = []
    last_y = None
    line_height_threshold = 2

    text_dict = page.get_text("rawdict", sort=False)

    for block in text_dict["blocks"]:
        if block.get("type") == 0:
            for line in block.get("lines", []):
                current_y = line["bbox"][1]

                if last_y is not None and abs(current_y - last_y) > line_height_threshold:
                    if current_block:
                        blocks.append(" ".join(current_block))
                        current_block = []

                line_text = []
                for span in line.get("spans", []):
                    text = span.get("chars", "")

                    if text:
                        flags = span.get("flags", 0)

                        # Find underline segments for this span
                        underline_segments = find_underline_segments(page, span)

                        # Process text with underline segments
                        text = process_span_with_underlines(text, underline_segments)

                        # Apply other formatting
                        if bool(flags & 2 ** 4):  # bold
                            text = f"<b>{text}</b>"
                        if bool(flags & 2 ** 1):  # italic
                            text = f"<i>{text}</i>"

                        line_text.append(text)

                if line_text:
                    current_block.append("".join(line_text).strip())
                last_y = current_y

    if current_block:
        blocks.append(" ".join(current_block))

    return blocks


@app.post("/parse")
async def parse_packet(packet_type: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "File must be a PDF"}

    try:
        contents = await file.read()
        all_blocks = []

        doc = pymupdf.open(stream=contents, filetype="pdf")

        for page in doc:
            page_blocks = extract_text_blocks(page)
            all_blocks.extend(page_blocks)

        doc.close()

        all_text = "\n".join(all_blocks)

        packet_data = ""
        if packet_type == "history_bowl":
            packet_data = parsers.parse_history_bowl(all_text)

        return packet_data

    except Exception as e:
        logger.exception(e)
        return {"error": f"Error processing PDF: {str(e)}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)