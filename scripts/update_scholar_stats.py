"""Fetch Google Scholar stats and update badges in about.md."""

import re
import os
from scholarly import scholarly, ProxyGenerator

SCHOLAR_ID = "lVn0bHUAAAAJ"
ABOUT_MD_PATH = os.path.join(os.path.dirname(__file__), "..", "_pages", "about.md")

# Papers whose citation counts should be updated dynamically.
# Key: a substring of the paper title (for matching); Value: not used, just for readability.
TRACKED_PAPERS = [
    "Can ChatGPT replace traditional KBQA models",
]


def setup_proxy():
    """Enable free proxy for scholarly."""
    pg = ProxyGenerator()
    pg.FreeProxies()
    scholarly.use_proxy(pg)


def get_scholar_stats(scholar_id):
    """Fetch author-level citation stats and per-paper citation counts."""
    try:
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=["indices", "publications"])
    except Exception as e:
        print(f"Direct fetch failed ({e}), retrying with free proxy...")
        setup_proxy()
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=["indices", "publications"])

    stats = {
        "citations": author["citedby"],
        "hindex": author["hindex"],
        "i10index": author["i10index"],
    }

    # Collect citation counts for tracked papers
    paper_citations = {}
    for pub in author.get("publications", []):
        title = pub.get("bib", {}).get("title", "")
        for tracked in TRACKED_PAPERS:
            if tracked.lower() in title.lower():
                num_citations = pub.get("num_citations", None)
                if isinstance(num_citations, int) and num_citations > 0:
                    paper_citations[tracked] = num_citations
                break

    return stats, paper_citations


def validate_stats(stats):
    """Sanity check: all values must be positive integers."""
    for key, val in stats.items():
        if not isinstance(val, int) or val <= 0:
            return False
    return True


def update_file(file_path, stats, paper_citations):
    """Replace badge numbers and paper citation counts in the markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Update author-level badges
    content = re.sub(r"citations-\d+", f"citations-{stats['citations']}", content)
    content = re.sub(r"h--index-\d+", f"h--index-{stats['hindex']}", content)
    content = re.sub(r"i10--index-\d+", f"i10--index-{stats['i10index']}", content)

    # Update per-paper citation counts: **NNN Citations**
    for tracked, count in paper_citations.items():
        # Match the line containing the tracked paper title and replace **N Citations**
        content = re.sub(
            r"(Can ChatGPT replace traditional KBQA models.*?\*\*)\d+( Citations\*\*)",
            rf"\g<1>{count}\2",
            content,
        )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated badges: citations={stats['citations']}, h-index={stats['hindex']}, i10-index={stats['i10index']}")
        for tracked, count in paper_citations.items():
            print(f"Updated paper: '{tracked}' -> {count} citations")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    print("Fetching Google Scholar stats...")
    try:
        stats, paper_citations = get_scholar_stats(SCHOLAR_ID)
    except Exception as e:
        print(f"Failed to fetch stats: {e}. Keeping original values.")
        raise SystemExit(0)

    print(f"Fetched stats: {stats}")
    print(f"Fetched paper citations: {paper_citations}")

    if not validate_stats(stats):
        print(f"Invalid stats: {stats}. Keeping original values.")
        raise SystemExit(0)

    update_file(ABOUT_MD_PATH, stats, paper_citations)
