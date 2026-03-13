# frontend tabs package
# Export tab renderers
from .content_sources import render as render_content_sources
from .search import render as render_search
from .diagnostics import render as render_diagnostics

__all__ = ["render_content_sources", "render_search", "render_diagnostics"]
