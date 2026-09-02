"""Unit tests for PubMed data models."""

import pytest
from pubmed_mcp.models import Article, Citation, SearchResult


class TestArticle:
    def test_article_stores_core_fields(self) -> None:
        a = Article(
            pmid="12345678",
            title="Effect of metformin on glucose metabolism",
            abstract="Metformin reduces hepatic glucose production...",
            authors=["Smith J", "Jones A"],
            journal="Diabetes Care",
            year=2023,
            doi="10.1234/dc.2023.001",
        )
        assert a.pmid == "12345678"
        assert a.year == 2023
        assert len(a.authors) == 2

    def test_pmid_must_be_numeric_string(self) -> None:
        with pytest.raises(ValueError, match="pmid"):
            Article(pmid="not-a-number", title="t", abstract="a",
                    authors=[], journal="j", year=2020)

    def test_abstract_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError):
            Article(pmid="12345678", title="t", abstract="",
                    authors=[], journal="j", year=2020)

    def test_doi_is_optional(self) -> None:
        a = Article(pmid="12345678", title="t", abstract="some text",
                    authors=[], journal="j", year=2020)
        assert a.doi is None

    def test_pubmed_url_property(self) -> None:
        a = Article(pmid="12345678", title="t", abstract="text",
                    authors=[], journal="j", year=2020)
        assert a.pubmed_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    def test_year_must_be_reasonable(self) -> None:
        with pytest.raises(ValueError):
            Article(pmid="12345678", title="t", abstract="text",
                    authors=[], journal="j", year=1700)


class TestCitation:
    def test_citation_formats_correctly(self) -> None:
        c = Citation(
            pmid="12345678",
            authors=["Smith J", "Jones A"],
            title="Effect of metformin",
            journal="Diabetes Care",
            year=2023,
            doi="10.1234/dc.2023.001",
        )
        formatted = c.format()
        assert "Smith J" in formatted
        assert "2023" in formatted
        assert "12345678" in formatted

    def test_citation_always_includes_pubmed_url(self) -> None:
        c = Citation(pmid="99999999", authors=["A B"], title="t",
                     journal="j", year=2020)
        assert "pubmed.ncbi.nlm.nih.gov/99999999" in c.format()

    def test_citation_without_doi_still_formats(self) -> None:
        c = Citation(pmid="11111111", authors=["X Y"], title="t",
                     journal="j", year=2021)
        formatted = c.format()
        assert "11111111" in formatted


class TestSearchResult:
    def test_search_result_stores_query_and_articles(self) -> None:
        articles = [
            Article(pmid="11111111", title="t1", abstract="a1",
                    authors=[], journal="j", year=2020),
        ]
        sr = SearchResult(query="diabetes metformin", articles=articles, total_found=42)
        assert sr.query == "diabetes metformin"
        assert sr.total_found == 42
        assert len(sr.articles) == 1

    def test_empty_results_allowed(self) -> None:
        sr = SearchResult(query="obscure query xyz", articles=[], total_found=0)
        assert sr.articles == []
        assert sr.is_empty is True

    def test_is_empty_false_when_results_exist(self) -> None:
        a = Article(pmid="12345678", title="t", abstract="a",
                    authors=[], journal="j", year=2020)
        sr = SearchResult(query="q", articles=[a], total_found=1)
        assert sr.is_empty is False
