"""Pydantic data models for PubMed articles, citations and search results."""

from pydantic import BaseModel, field_validator


class Article(BaseModel):
    """A single PubMed article record.

    Args:
        pmid: PubMed identifier — a numeric string (e.g. '12345678').
        title: Article title.
        abstract: Full abstract text.
        authors: List of author names in 'Surname Initial' format.
        journal: Journal name.
        year: Publication year.
        doi: Digital Object Identifier, if available.
    """

    pmid: str
    title: str
    abstract: str
    authors: list[str]
    journal: str
    year: int
    doi: str | None = None

    @field_validator("pmid")
    @classmethod
    def pmid_must_be_numeric(cls, v: str) -> str:
        """Ensure PMID contains only digits."""
        if not v.isdigit():
            raise ValueError(f"pmid must be a numeric string, got '{v}'")
        return v

    @field_validator("abstract")
    @classmethod
    def abstract_not_empty(cls, v: str) -> str:
        """Reject blank abstracts."""
        if not v.strip():
            raise ValueError("abstract cannot be empty")
        return v

    @field_validator("year")
    @classmethod
    def year_must_be_reasonable(cls, v: int) -> int:
        """Reject years before PubMed data begins."""
        if v < 1800:
            raise ValueError(f"year {v} is not plausible for a biomedical article")
        return v

    @property
    def pubmed_url(self) -> str:
        """Canonical PubMed URL for this article."""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class Citation(BaseModel):
    """A formatted citation for a PubMed article.

    Used to ensure every response from the MCP server is traceable to a
    source document — responses must include a citation and refuse when
    no supporting article exists.

    Args:
        pmid: PubMed identifier.
        authors: Author list.
        title: Article title.
        journal: Journal name.
        year: Publication year.
        doi: DOI if available.
    """

    pmid: str
    authors: list[str]
    title: str
    journal: str
    year: int
    doi: str | None = None

    def format(self) -> str:
        """Return a human-readable citation string with source URL.

        Returns:
            Formatted citation always ending with the PubMed URL so
            every server response is verifiable.
        """
        author_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += " et al."

        parts = [f"{author_str} ({self.year}). {self.title}. {self.journal}."]
        if self.doi:
            parts.append(f"DOI: {self.doi}.")
        parts.append(f"PMID: {self.pmid}. https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/")

        return " ".join(parts)


class SearchResult(BaseModel):
    """The result of a PubMed search query.

    Args:
        query: The search string submitted to PubMed.
        articles: Articles returned (may be a subset of total_found).
        total_found: Total number of matching records in PubMed.
    """

    query: str
    articles: list[Article]
    total_found: int

    @property
    def is_empty(self) -> bool:
        """True when no articles were returned."""
        return len(self.articles) == 0
