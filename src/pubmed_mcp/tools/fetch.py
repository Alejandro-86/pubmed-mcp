"""MCP tool: fetch_abstract — retrieve a full abstract by PMID with citation."""

from pubmed_mcp.client.pubmed import PubMedClient
from pubmed_mcp.models import Citation


async def handle_fetch(client: PubMedClient, pmid: str) -> str:
    """Handle the fetch_abstract MCP tool call.

    Fetches the full abstract for a PubMed article by PMID.  The response
    always ends with a mandatory citation — this server never returns content
    without a verifiable source.

    Args:
        client: PubMed API client.
        pmid: PubMed identifier (numeric string).

    Returns:
        Formatted string containing the abstract text followed by a full
        citation including the PubMed URL.

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

    return (
        f"**{article.title}**\n\n"
        f"{article.abstract}\n\n"
        f"---\n"
        f"**Citation:** {citation.format()}"
    )
