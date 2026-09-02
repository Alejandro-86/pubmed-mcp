"""Async HTTP client for the NCBI PubMed E-utilities API.

Covers:
  - esearch: query PubMed, returns list of PMIDs
  - efetch: fetch full article records by PMID

Rate limits:
  - Without API key: 3 req/s
  - With NCBI_API_KEY env var: 10 req/s

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import os
import xml.etree.ElementTree as ET

import httpx

from pubmed_mcp.models import Article, SearchResult

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH = f"{_BASE}/esearch.fcgi"
_EFETCH  = f"{_BASE}/efetch.fcgi"


class PubMedAPIError(RuntimeError):
    """Raised when the PubMed API returns an error or unexpected response."""


class PubMedClient:
    """Async client for PubMed E-utilities.

    Args:
        api_key: Optional NCBI API key for higher rate limits (10 req/s vs 3).
        timeout: HTTP timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key or os.getenv("NCBI_API_KEY")
        self._timeout = timeout

    def _base_params(self) -> dict[str, str]:
        """Common parameters appended to every request."""
        params = {"retmode": "xml"}
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    async def search(self, query: str, max_results: int = 10) -> SearchResult:
        """Search PubMed for articles matching a query.

        Calls esearch to get PMIDs and total count.  Returns a SearchResult
        with stub Article objects (PMID only) — call ``fetch_abstract`` to
        get full records.

        Args:
            query: PubMed query string (supports MeSH terms, Boolean operators).
            max_results: Maximum number of PMIDs to return.

        Returns:
            SearchResult with total_found and a list of stub articles.

        Raises:
            PubMedAPIError: On HTTP errors or XML parse failures.
        """
        params = {
            **self._base_params(),
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
        }

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            try:
                resp = await http.get(_ESEARCH, params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise PubMedAPIError(f"esearch HTTP {exc.response.status_code}") from exc
            except httpx.RequestError as exc:
                raise PubMedAPIError(f"esearch request failed: {exc}") from exc

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise PubMedAPIError(f"failed to parse esearch XML: {exc}") from exc

        total = int(root.findtext("Count") or "0")
        pmids = [id_el.text for id_el in root.findall(".//Id") if id_el.text]

        # Return lightweight stubs — callers can fetch full records as needed
        stubs: list[Article] = []
        for pmid in pmids:
            stubs.append(Article(
                pmid=pmid, title="", abstract="stub",
                authors=[], journal="", year=1900,
            ))

        return SearchResult(query=query, articles=stubs, total_found=total)

    async def fetch_abstract(self, pmid: str) -> Article:
        """Fetch the full article record for a single PMID.

        Args:
            pmid: PubMed identifier (numeric string).

        Returns:
            Article with title, abstract, authors, journal, year, doi.

        Raises:
            PubMedAPIError: If the PMID is not found or the API errors.
        """
        params = {
            **self._base_params(),
            "db": "pubmed",
            "id": pmid,
            "rettype": "abstract",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            try:
                resp = await http.get(_EFETCH, params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise PubMedAPIError(f"efetch HTTP {exc.response.status_code}") from exc
            except httpx.RequestError as exc:
                raise PubMedAPIError(f"efetch request failed: {exc}") from exc

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise PubMedAPIError(f"failed to parse efetch XML: {exc}") from exc

        article_el = root.find(".//PubmedArticle")
        if article_el is None:
            raise PubMedAPIError(f"PMID {pmid} not found in efetch response")

        citation = article_el.find("MedlineCitation")
        if citation is None:
            raise PubMedAPIError(f"malformed record for PMID {pmid}")

        art = citation.find("Article")
        if art is None:
            raise PubMedAPIError(f"no Article element for PMID {pmid}")

        title   = art.findtext("ArticleTitle") or ""
        abstract_parts = [
            el.text or ""
            for el in art.findall(".//AbstractText")
        ]
        abstract = " ".join(p for p in abstract_parts if p).strip() or "No abstract available."

        authors: list[str] = []
        for author_el in art.findall(".//Author"):
            last  = author_el.findtext("LastName") or ""
            init  = author_el.findtext("Initials") or ""
            if last:
                authors.append(f"{last} {init}".strip())

        journal = art.findtext(".//Journal/Title") or ""
        year_str = art.findtext(".//JournalIssue/PubDate/Year") or "1900"
        doi = art.findtext(".//ELocationID[@EIdType='doi']")

        return Article(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=int(year_str),
            doi=doi,
        )
