"""File processing pipeline for different content types."""
import io
import json
from typing import Dict, Any, Optional, Tuple
from PIL import Image
from io import BytesIO
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, get_all_lexers
from pygments.formatters import HtmlFormatter
import csv


class ProcessorBase:
    """Base class for content processors."""

    @staticmethod
    async def extract_metadata(content: bytes, content_type: str) -> Dict[str, Any]:
        """Extract metadata from content."""
        raise NotImplementedError

    @staticmethod
    async def generate_preview(content: bytes, content_type: str) -> Optional[Dict[str, Any]]:
        """Generate preview data."""
        return None


class TextProcessor(ProcessorBase):
    """Processor for text files."""

    @staticmethod
    async def extract_metadata(content: bytes, content_type: str) -> Dict[str, Any]:
        """Extract text metadata."""
        try:
            text = content.decode('utf-8', errors='replace')
            lines = text.split('\n')
            return {
                "line_count": len(lines),
                "char_count": len(text),
                "word_count": len(text.split()),
                "encoding": "utf-8"
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def generate_preview(content: bytes, content_type: str) -> Optional[Dict[str, Any]]:
        """Generate text preview."""
        try:
            text = content.decode('utf-8', errors='replace')
            preview_text = text[:500]
            return {
                "type": "text",
                "preview": preview_text,
                "truncated": len(text) > 500
            }
        except Exception:
            return None


class CodeProcessor(ProcessorBase):
    """Processor for code files."""

    @staticmethod
    async def extract_metadata(content: bytes, content_type: str, language_hint: Optional[str] = None) -> Dict[str, Any]:
        """Extract code metadata."""
        try:
            text = content.decode('utf-8', errors='replace')
            lines = text.split('\n')

            # Try to detect language
            language = language_hint
            if not language or language == "auto":
                try:
                    lexer = guess_lexer(text)
                    language = lexer.name
                except Exception:
                    language = "Text"

            return {
                "line_count": len(lines),
                "language": language,
                "char_count": len(text),
                "encoding": "utf-8"
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def generate_preview(content: bytes, content_type: str, language_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generate syntax-highlighted code preview."""
        try:
            text = content.decode('utf-8', errors='replace')

            # Get lexer
            lexer = None
            if language_hint and language_hint != "auto":
                try:
                    lexer = get_lexer_by_name(language_hint.lower())
                except Exception:
                    pass

            if not lexer:
                try:
                    lexer = guess_lexer(text)
                except Exception:
                    from pygments.lexers import get_lexer_by_name
                    lexer = get_lexer_by_name("text")

            formatter = HtmlFormatter(style="monokai", linenos=True, full=False)
            highlighted = highlight(text, lexer, formatter)

            return {
                "type": "code",
                "language": lexer.name if lexer else "Text",
                "highlighted_html": highlighted,
                "line_count": len(text.split('\n')),
                "css": formatter.get_style_defs('.highlight')
            }
        except Exception as e:
            return {"error": str(e)}


class ImageProcessor(ProcessorBase):
    """Processor for images."""

    @staticmethod
    async def extract_metadata(content: bytes, content_type: str) -> Dict[str, Any]:
        """Extract image metadata."""
        try:
            img = Image.open(BytesIO(content))
            metadata = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode
            }

            # Try to get EXIF data if available
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    metadata["exif"] = str(exif)

            return metadata
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def generate_preview(content: bytes, content_type: str) -> Optional[Dict[str, Any]]:
        """Generate image thumbnail."""
        try:
            img = Image.open(BytesIO(content))

            # Create thumbnail
            img.thumbnail((200, 200))
            thumb_io = BytesIO()
            img.save(thumb_io, format=img.format or 'PNG')
            thumb_data = thumb_io.getvalue()

            return {
                "type": "image",
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "thumbnail_base64": f"data:image/png;base64,{__import__('base64').b64encode(thumb_data).decode()}"
            }
        except Exception as e:
            return {"error": str(e)}


class CSVProcessor(ProcessorBase):
    """Processor for CSV files."""

    @staticmethod
    async def extract_metadata(content: bytes, content_type: str) -> Dict[str, Any]:
        """Extract CSV metadata."""
        try:
            text = content.decode('utf-8', errors='replace')
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)

            if not rows:
                return {"error": "Empty CSV"}

            headers = rows[0] if rows else []
            return {
                "columns": headers,
                "row_count": len(rows) - 1,  # Exclude header
                "column_count": len(headers)
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def generate_preview(content: bytes, content_type: str) -> Optional[Dict[str, Any]]:
        """Generate CSV preview."""
        try:
            text = content.decode('utf-8', errors='replace')
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)[:10]  # First 10 rows

            return {
                "type": "csv",
                "rows": rows,
                "preview_row_count": len(rows),
                "has_more": len(rows) >= 10
            }
        except Exception as e:
            return {"error": str(e)}


async def get_processor(content_type: str, content: bytes = None) -> ProcessorBase:
    """Get appropriate processor for content type."""
    content_type_lower = content_type.lower()

    if "image" in content_type_lower:
        return ImageProcessor()
    elif "csv" in content_type_lower or content_type_lower == "text/csv":
        return CSVProcessor()
    elif "code" in content_type_lower or any(lang in content_type_lower for lang in ["python", "javascript", "java", "c++"]):
        return CodeProcessor()
    else:
        return TextProcessor()


async def process_content(content: bytes, content_type: str, language_hint: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Process content and extract metadata and preview.

    Returns:
        Tuple of (metadata, preview)
    """
    processor = await get_processor(content_type, content)

    metadata = await processor.extract_metadata(content, content_type)
    if language_hint and hasattr(processor, 'generate_preview'):
        # Pass language hint for code processor
        if isinstance(processor, CodeProcessor):
            preview = await processor.generate_preview(content, content_type, language_hint)
        else:
            preview = await processor.generate_preview(content, content_type)
    else:
        preview = await processor.generate_preview(content, content_type) if hasattr(processor, 'generate_preview') else None

    return metadata, preview
