"""MCP tool: format_citation — return a formatted citation for a PMID."""

from pubmed_mcp.client.pubmed import PubMedClient
from pubmed_mcp.models import Citation


async def handle_cite(client: PubMedClient, pmid: str) -> str:
    """Handle the format_citation MCP tool call.

    Fetches article metadata and returns a formatted citation string.
    Always includes the PubMed URL so every citation is verifiable.

    Args:
        client: PubMed API client.
        pmid: PubMed identifier (numeric string).

    Returns:
        Formatted citation string with authors, year, title, journal, DOI
        (if available), PMID, and PubMed URL.

    Raises:
        PubMedAPIError: If the PMID is not found or the API errors.
    """
    article = await client.fetch_abstract(pmid)

    citation = Citation(
        pmid=article.pmid,
        authors=article.authors,
        title=article.title,
        journal=article.journal,
        year=article.year,
        doi=article.doi,
    )

    return citation.format()
