"""Unit tests for MCP tool handler functions.

Tools are pure async functions — tested with a stub PubMedClient,
no real HTTP or MCP server involved.
"""

import pytest
from pubmed_mcp.client.pubmed import PubMedAPIError
from pubmed_mcp.models import Article, Citation, SearchResult
from pubmed_mcp.tools.search import handle_search
from pubmed_mcp.tools.fetch import handle_fetch
from pubmed_mcp.tools.cite import handle_cite


def _make_article(pmid: str = "12345678") -> Article:
    return Article(
        pmid=pmid,
        title="Metformin reduces glucose in type 2 diabetes",
        abstract="Metformin is a biguanide that reduces hepatic glucose production.",
        authors=["Smith J", "Jones A"],
        journal="Diabetes Care",
        year=2023,
        doi="10.1234/dc.2023.001",
    )


class StubPubMedClient:
    """Stub that returns canned responses without HTTP calls."""

    def __init__(
        self,
        search_result: SearchResult | None = None,
        fetch_result: Article | None = None,
        raise_on_search: bool = False,
        raise_on_fetch: bool = False,
    ) -> None:
        self._search = search_result
        self._fetch = fetch_result
        self._raise_search = raise_on_search
        self._raise_fetch = raise_on_fetch

    async def search(self, query: str, max_results: int = 10) -> SearchResult:
        if self._raise_search:
            raise PubMedAPIError("search failed")
        return self._search or SearchResult(query=query, articles=[], total_found=0)

    async def fetch_abstract(self, pmid: str) -> Article:
        if self._raise_fetch:
            raise PubMedAPIError(f"PMID {pmid} not found")
        return self._fetch or _make_article(pmid)


# ─── search tool ─────────────────────────────────────────────────────────────

class TestHandleSearch:
    async def test_returns_formatted_results(self) -> None:
        article = _make_article()
        stub = StubPubMedClient(
            search_result=SearchResult(
                query="metformin diabetes",
                articles=[article],
                total_found=1,
            )
        )
        text = await handle_search(stub, query="metformin diabetes")
        assert "12345678" in text
        assert "Metformin" in text

    async def test_returns_no_results_message_when_empty(self) -> None:
        stub = StubPubMedClient(
            search_result=SearchResult(query="xyzzy", articles=[], total_found=0)
        )
        text = await handle_search(stub, query="xyzzy")
        assert "no" in text.lower() and ("results" in text.lower() or "found" in text.lower())

    async def test_includes_source_note(self) -> None:
        stub = StubPubMedClient(
            search_result=SearchResult(query="q", articles=[_make_article()], total_found=1)
        )
        text = await handle_search(stub, query="q")
        assert "pubmed" in text.lower()

    async def test_propagates_api_error(self) -> None:
        stub = StubPubMedClient(raise_on_search=True)
        with pytest.raises(PubMedAPIError):
            await handle_search(stub, query="query")


# ─── fetch tool ──────────────────────────────────────────────────────────────

class TestHandleFetch:
    async def test_returns_abstract_with_citation(self) -> None:
        stub = StubPubMedClient(fetch_result=_make_article())
        text = await handle_fetch(stub, pmid="12345678")
        assert "Metformin" in text
        assert "pubmed.ncbi.nlm.nih.gov/12345678" in text

    async def test_always_includes_citation(self) -> None:
        stub = StubPubMedClient(fetch_result=_make_article("99999999"))
        text = await handle_fetch(stub, pmid="99999999")
        assert "99999999" in text
        assert "pubmed.ncbi.nlm.nih.gov" in text

    async def test_propagates_not_found_error(self) -> None:
        stub = StubPubMedClient(raise_on_fetch=True)
        with pytest.raises(PubMedAPIError):
            await handle_fetch(stub, pmid="00000000")


# ─── cite tool ───────────────────────────────────────────────────────────────

class TestHandleCite:
    async def test_returns_formatted_citation(self) -> None:
        stub = StubPubMedClient(fetch_result=_make_article())
        text = await handle_cite(stub, pmid="12345678")
        assert "Smith J" in text
        assert "2023" in text
        assert "pubmed.ncbi.nlm.nih.gov/12345678" in text

    async def test_citation_includes_doi_when_available(self) -> None:
        stub = StubPubMedClient(fetch_result=_make_article())
        text = await handle_cite(stub, pmid="12345678")
        assert "10.1234" in text

    async def test_propagates_api_error(self) -> None:
        stub = StubPubMedClient(raise_on_fetch=True)
        with pytest.raises(PubMedAPIError):
            await handle_cite(stub, pmid="00000000")
