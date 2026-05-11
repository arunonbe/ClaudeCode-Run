#!/usr/bin/env python3
"""
sync_confluence.py — Sync L3 Codebase analysis pages to Confluence.

Confluence structure created/maintained:
  Haiintel Team (folder, pre-existing, ID from CONFLUENCE_FOLDER_ID)
  └── Run 1                          (page)
      └── L3 Codebase                (page)
          └── <repo-name>            (page, one per repo)
              ├── H2: Business Analyst
              ├── H2: Data Architect
              ├── H2: DevOps and Operations
              ├── H2: Enterprise Architect
              └── H2: Solution Architect

Usage (called by GitHub Actions):
  python sync_confluence.py [changed_file_1 changed_file_2 ...]
  Passing no files triggers a full sync of all repos found in Run 1/L3 Codebase/.
"""

import html
import os
import re
import sys
from pathlib import Path

import markdown as mdlib
import requests

# ---------------------------------------------------------------------------
# Config — all values come from environment (GitHub Secrets)
# ---------------------------------------------------------------------------
DOMAIN    = os.environ["ATLASSIAN_DOMAIN"]       # onbeco.atlassian.net
EMAIL     = os.environ["ATLASSIAN_EMAIL"]         # arun.kumar@onbe.com
TOKEN     = os.environ["ATLASSIAN_API_TOKEN"]
FOLDER_ID = os.environ["CONFLUENCE_FOLDER_ID"]   # 3500736563
SPACE_KEY = "OT"

BASE_URL  = f"https://{DOMAIN}/wiki/api/v2"
AUTH      = (EMAIL, TOKEN)
HEADERS   = {"Accept": "application/json", "Content-Type": "application/json"}

FILES_ROOT = Path("Run 1/L3 Codebase")

SECTIONS = [
    ("01_business_analyst",     "Business Analyst"),
    ("02_data_architect",       "Data Architect"),
    ("03_devops_operations",    "DevOps and Operations"),
    ("04_enterprise_architect", "Enterprise Architect"),
    ("05_solution_architect",   "Solution Architect"),
]

# ---------------------------------------------------------------------------
# Confluence REST API v2 helpers
# ---------------------------------------------------------------------------

def get_space_id() -> str:
    r = requests.get(
        f"{BASE_URL}/spaces",
        params={"keys": SPACE_KEY},
        auth=AUTH, headers=HEADERS
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise SystemExit(f"ERROR: Space '{SPACE_KEY}' not found.")
    return results[0]["id"]


def find_page(title: str, space_id: str, parent_id: str = None) -> dict | None:
    """Search for a page by exact title within the space.
    Optionally filter by parent_id to avoid title collisions."""
    r = requests.get(
        f"{BASE_URL}/pages",
        params={"title": title, "space-id": space_id, "status": "current", "limit": 25},
        auth=AUTH, headers=HEADERS
    )
    r.raise_for_status()
    pages = r.json().get("results", [])
    if parent_id is not None:
        pages = [p for p in pages if str(p.get("parentId")) == str(parent_id)]
    return pages[0] if pages else None


def create_page(title: str, space_id: str, parent_id: str, body: str) -> dict:
    payload = {
        "title":    title,
        "spaceId":  space_id,
        "parentId": str(parent_id),
        "body":     {"representation": "storage", "value": body},
    }
    r = requests.post(f"{BASE_URL}/pages", json=payload, auth=AUTH, headers=HEADERS)
    if not r.ok:
        raise SystemExit(
            f"ERROR creating page '{title}': {r.status_code}\n{r.text[:600]}"
        )
    return r.json()


def update_page(page_id: str, title: str, current_version: int, body: str) -> dict:
    payload = {
        "id":      str(page_id),
        "title":   title,
        "version": {
            "number":  current_version + 1,
            "message": "Synced via GitHub Actions",
        },
        "body": {"representation": "storage", "value": body},
    }
    r = requests.put(
        f"{BASE_URL}/pages/{page_id}", json=payload, auth=AUTH, headers=HEADERS
    )
    if not r.ok:
        raise SystemExit(
            f"ERROR updating page '{title}' (id={page_id}): {r.status_code}\n{r.text[:600]}"
        )
    return r.json()


def ensure_page(title: str, space_id: str, parent_id: str, body: str) -> dict:
    """Find-and-update or create a page. Returns the resulting page dict."""
    existing = find_page(title, space_id, parent_id)
    if existing:
        ver = existing.get("version", {}).get("number", 1)
        page = update_page(existing["id"], title, ver, body)
        print(f"  [updated] {title}")
    else:
        page = create_page(title, space_id, parent_id, body)
        print(f"  [created] {title}")
    return page


# ---------------------------------------------------------------------------
# Markdown → Confluence storage format
# ---------------------------------------------------------------------------

def md_to_storage(text: str) -> str:
    """Convert Markdown text to Confluence-compatible HTML storage format."""
    return mdlib.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )


def build_repo_body(repo: str) -> str:
    """Build the full HTML body for a repo page (5 analyst sections)."""
    parts = []
    for key, label in SECTIONS:
        md_path = FILES_ROOT / f"L3_Code_{repo}_{key}.md"
        label_escaped = html.escape(label)
        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8", errors="replace")
            content = md_to_storage(md_text)
        else:
            content = "<p><em>File not found.</em></p>"
        parts.append(f"<h2>{label_escaped}</h2>\n{content}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Repo name extraction from file paths
# ---------------------------------------------------------------------------

FILE_RE = re.compile(
    r"L3_Code_(.+?)_"
    r"(?:01_business_analyst|02_data_architect|03_devops_operations"
    r"|04_enterprise_architect|05_solution_architect)\.md$"
)


def repos_from_files(file_list: list) -> set:
    repos = set()
    for f in file_list:
        m = FILE_RE.search(Path(f).name)
        if m:
            repos.add(m.group(1))
    return repos


def all_repos_on_disk() -> set:
    """Fall-back: derive repo list from files present in the working tree."""
    repos = set()
    for p in FILES_ROOT.glob("L3_Code_*_01_business_analyst.md"):
        m = FILE_RE.search(p.name)
        if m:
            repos.add(m.group(1))
    return repos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    changed_args = sys.argv[1:]
    repos = repos_from_files(changed_args) if changed_args else all_repos_on_disk()

    if not repos:
        print("No L3 Codebase repos to sync. Exiting.")
        return

    print("=" * 60)
    print(f"Repos to sync : {len(repos)}")
    print(f"Confluence    : https://{DOMAIN}/wiki/spaces/{SPACE_KEY}")
    print("=" * 60)

    space_id = get_space_id()
    print(f"Space ID      : {space_id}\n")

    # Ensure "Run 1" page under the Haiintel Team folder
    run1 = ensure_page(
        title="Run 1",
        space_id=space_id,
        parent_id=FOLDER_ID,
        body=(
            "<p>Analysis output from the Onbe 363-repository technology "
            "estate assessment conducted in May 2026.</p>"
        ),
    )

    # Ensure "L3 Codebase" page under "Run 1"
    l3 = ensure_page(
        title="L3 Codebase",
        space_id=space_id,
        parent_id=run1["id"],
        body=(
            "<p>Per-repository L3 codebase analysis covering all 363 repositories "
            "across 5 specialist viewpoints: Business Analyst, Data Architect, "
            "DevOps and Operations, Enterprise Architect, and Solution Architect.</p>"
        ),
    )

    print()
    synced = 0
    failed = 0
    for repo in sorted(repos):
        try:
            body = build_repo_body(repo)
            ensure_page(
                title=repo,
                space_id=space_id,
                parent_id=l3["id"],
                body=body,
            )
            synced += 1
        except SystemExit as e:
            print(f"  [FAILED]  {repo} — {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Synced : {synced}   Failed : {failed}")
    print("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
