"""MCP tool: search_pubmed — query PubMed and return article summaries."""

from pubmed_mcp.client.pubmed import PubMedClient


async def handle_search(
    client: PubMedClient,
    query: str,
    max_results: int = 10,
) -> str:
    """Handle the search_pubmed MCP tool call.

    Searches PubMed for articles matching the query and returns a formatted
    summary.  Always includes the PubMed source URL for every result so the
    caller can verify the grounding.

    Args:
        client: PubMed API client.
        query: Search query string (supports MeSH terms and Boolean operators).
        max_results: Maximum number of results to return.

    Returns:
        Formatted string listing matching articles with PMIDs and titles,
        or a "no results" message if nothing was found.

    Raises:
        PubMedAPIError: If the PubMed API returns an error.
    """
    result = await client.search(query, max_results=max_results)

    if result.is_empty:
        return (
            f"No PubMed results found for query: '{query}'. "
            "Try broader terms or check spelling."
        )

    lines = [
        f"PubMed search: '{query}' — {result.total_found} total results "
        f"(showing {len(result.articles)}):\n"
    ]
    for article in result.articles:
        title = article.title or "(no title)"
        lines.append(
            f"• PMID {article.pmid}: {title}\n"
            f"  Source: https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/"
        )

    lines.append("\nUse fetch_abstract(pmid) to retrieve the full abstract.")
    return "\n".join(lines)
