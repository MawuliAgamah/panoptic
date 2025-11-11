"""Compatibility shim for legacy imports.

Re-export shared tabular CSV tools from the central module so agent code
and pipeline use the same implementation.
"""

from knowledge_graph.document_ingestion.tabular.agents_tools import (
    sniff_csv,
    read_rows,
    read_headers_and_sample,
)

__all__ = ["sniff_csv", "read_rows", "read_headers_and_sample"]
