"""Unit tests for the PubMed E-utilities HTTP client.

Uses pytest-httpx to mock all HTTP calls — no real network access.
"""

import pytest
from pytest_httpx import HTTPXMock

from pubmed_mcp.client.pubmed import PubMedAPIError, PubMedClient

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


ESEARCH_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
  <Count>2</Count>
  <IdList>
    <Id>12345678</Id>
    <Id>87654321</Id>
  </IdList>
</eSearchResult>"""

EFETCH_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Metformin reduces glucose in type 2 diabetes</ArticleTitle>
        <Abstract>
          <AbstractText>Metformin is a first-line treatment for type 2 diabetes.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <Initials>J</Initials>
          </Author>
        </AuthorList>
        <Journal>
          <Title>Diabetes Care</Title>
          <JournalIssue>
            <PubDate><Year>2023</Year></PubDate>
          </JournalIssue>
        </Journal>
        <ELocationID EIdType="doi">10.1234/dc.2023.001</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

ESEARCH_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult><Count>0</Count><IdList></IdList></eSearchResult>"""


class TestSearch:
    async def test_search_returns_pmids(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(text=ESEARCH_RESPONSE)
        client = PubMedClient()
        result = await client.search("diabetes metformin", max_results=2)
        assert result.total_found == 2

    async def test_search_empty_result(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(text=ESEARCH_EMPTY)
        client = PubMedClient()
        result = await client.search("xyzzy impossible query")
        assert result.is_empty
        assert result.total_found == 0

    async def test_search_raises_on_http_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500)
        client = PubMedClient()
        with pytest.raises(PubMedAPIError):
            await client.search("query")


class TestFetch:
    async def test_fetch_returns_article(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(text=EFETCH_RESPONSE)
        client = PubMedClient()
        article = await client.fetch_abstract("12345678")
        assert article.pmid == "12345678"
        assert "Metformin" in article.title
        assert article.journal == "Diabetes Care"
        assert article.year == 2023
        assert article.doi == "10.1234/dc.2023.001"

    async def test_fetch_raises_on_http_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404)
        client = PubMedClient()
        with pytest.raises(PubMedAPIError):
            await client.fetch_abstract("00000000")

    async def test_fetch_raises_on_missing_pmid(self, httpx_mock: HTTPXMock) -> None:
        empty_xml = """<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>"""
        httpx_mock.add_response(text=empty_xml)
        client = PubMedClient()
        with pytest.raises(PubMedAPIError, match="not found"):
            await client.fetch_abstract("00000000")
