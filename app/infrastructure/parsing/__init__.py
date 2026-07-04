"""Parsing adapters."""

from app.infrastructure.parsing.interfaces import DocumentParser, ParserRegistry
from app.infrastructure.parsing.markdown_parser import MarkdownParser
from app.infrastructure.parsing.txt_parser import TxtParser

__all__ = ["DocumentParser", "MarkdownParser", "ParserRegistry", "TxtParser"]

