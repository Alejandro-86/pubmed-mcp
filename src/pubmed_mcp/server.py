"""MCP server entry point.

Registers three read-only tools over the PubMed E-utilities API:
  - search_pubmed
  - fetch_abstract
  - format_citation

Security properties:
  - Only retrieval tools are exposed — no write, delete or modify tools
  - Every response includes a mandatory citation with PubMed URL
  - Prompt injection in fetched content cannot trigger side effects
    because no side-effecting tools exist
"""

import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from pubmed_mcp.client.pubmed import PubMedClient, PubMedAPIError
from pubmed_mcp.config import settings
from pubmed_mcp.tools.search import handle_search
from pubmed_mcp.tools.fetch import handle_fetch
from pubmed_mcp.tools.cite import handle_cite

logger = logging.getLogger(__name__)

server = Server("pubmed-mcp")

_client = PubMedClient(
    api_key=settings.ncbi_api_key or None,
    timeout=settings.http_timeout,
)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return the list of available read-only tools."""
    return [
        types.Tool(
            name="search_pubmed",
            description=(
                "Search PubMed for biomedical articles. "
                "Returns article titles and PMIDs with source URLs. "
                "Use fetch_abstract to get the full abstract."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "PubMed query (supports MeSH terms, Boolean operators)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="fetch_abstract",
            description=(
                "Fetch the full abstract and metadata for a PubMed article by PMID. "
                "Response always includes a mandatory citation with the PubMed source URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {
                        "type": "string",
                        "description": "PubMed identifier (numeric string, e.g. '12345678')",
                    },
                },
                "required": ["pmid"],
            },
        ),
        types.Tool(
            name="format_citation",
            description=(
                "Return a formatted citation for a PubMed article by PMID. "
                "Includes authors, year, title, journal, DOI (if available), "
                "and always the PubMed URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pmid": {
                        "type": "string",
                        "description": "PubMed identifier",
                    },
                },
                "required": ["pmid"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, object],
) -> list[types.TextContent]:
    """Dispatch a tool call to the appropriate handler.

    Args:
        name: Tool name — one of search_pubmed, fetch_abstract, format_citation.
        arguments: Tool arguments as a dict.

    Returns:
        List containing a single TextContent with the result.

    Raises:
        ValueError: If the tool name is not recognised.
    """
    try:
        match name:
            case "search_pubmed":
                query = str(arguments["query"])
                max_results = int(arguments.get("max_results", settings.max_search_results))
                text = await handle_search(_client, query=query, max_results=max_results)

            case "fetch_abstract":
                pmid = str(arguments["pmid"])
                text = await handle_fetch(_client, pmid=pmid)

            case "format_citation":
                pmid = str(arguments["pmid"])
                text = await handle_cite(_client, pmid=pmid)

            case _:
                raise ValueError(f"unknown tool: '{name}'")

    except PubMedAPIError as exc:
        text = f"PubMed API error: {exc}"
        logger.warning("tool %s failed: %s", name, exc)

    return [types.TextContent(type="text", text=text)]


def main() -> None:
    """Start the MCP server over stdio."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_serve())


async def _serve() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    main()
