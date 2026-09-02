# pubmed-mcp

A read-only MCP (Model Context Protocol) server over the PubMed E-utilities API.
Designed for safe, grounded retrieval of biomedical literature inside LLM and
agentic workflows.

## Security design

```
┌─────────────────────────────────────────────────────┐
│                  pubmed-mcp server                  │
│                                                     │
│  Exposed tools (READ-ONLY):                         │
│    search_pubmed   → query PubMed, return PMIDs     │
│    fetch_abstract  → fetch abstract + metadata      │
│    format_citation → return formatted citation      │
│                                                     │
│  NOT exposed: any write, delete, or modify tool     │
│                                                     │
│  Every response includes a mandatory citation       │
│  Refuses when no supporting article exists          │
│  Prompt-injection in fetched content cannot         │
│  trigger write operations (no write tools exist)    │
└─────────────────────────────────────────────────────┘
```

This design means injected instructions in fetched PubMed abstracts can never
trigger side effects — there are no side-effecting tools to call.

## Tools

| Tool | Description |
|---|---|
| `search_pubmed` | Search PubMed by query string, returns list of articles with PMIDs |
| `fetch_abstract` | Fetch full abstract and metadata for a PMID, always cites source |
| `format_citation` | Return a formatted citation string for a PMID |

## Quickstart

```bash
pip install -e ".[dev]"
python -m pubmed_mcp.server     # starts stdio MCP server
```

### Connect from Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pubmed": {
      "command": "python",
      "args": ["-m", "pubmed_mcp.server"],
      "env": {
        "NCBI_API_KEY": "your_key_here"
      }
    }
  }
}
```

### Docker

```bash
docker build -t pubmed-mcp .
docker run -e NCBI_API_KEY=your_key pubmed-mcp
```

## Rate limits

Without an NCBI API key: 3 requests/second.
With a key (`NCBI_API_KEY` env var): 10 requests/second.
Register free at https://www.ncbi.nlm.nih.gov/account/
