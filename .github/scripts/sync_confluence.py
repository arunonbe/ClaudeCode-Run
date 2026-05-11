#!/usr/bin/env python3
"""
sync_confluence.py — Sync all 3 analysis layers to Confluence.

Confluence structure created/maintained:
  Haiintel Team (folder, pre-existing)
  └── Run 1
      ├── L1 Organism
      │   └── FINAL_COMBINED_REPORT       (1 page)
      ├── L2 Molecule
      │   ├── MASTER_BUSINESS_ANALYST
      │   ├── MASTER_DATA_ARCHITECT
      │   ├── MASTER_DEVOPS
      │   ├── MASTER_ENTERPRISE_ARCHITECT
      │   └── MASTER_SOLUTION_ARCHITECT   (5 pages)
      └── L3 Codebase
          └── <repo-name>                 (363 pages, 5 sections each)

Usage:
  python sync_confluence.py [changed_file_1 changed_file_2 ...]
  No args = full sync of all layers.
  With args = only layers that have changed files are synced.
"""

import html
import os
import re
import sys
from pathlib import Path

import markdown as mdlib
import requests

# ---------------------------------------------------------------------------
# Config from environment (GitHub Secrets)
# ---------------------------------------------------------------------------
DOMAIN    = os.environ["ATLASSIAN_DOMAIN"]
EMAIL     = os.environ["ATLASSIAN_EMAIL"]
TOKEN     = os.environ["ATLASSIAN_API_TOKEN"]
FOLDER_ID = os.environ["CONFLUENCE_FOLDER_ID"]
SPACE_KEY = "OT"

BASE_URL = f"https://{DOMAIN}/wiki/api/v2"
AUTH     = (EMAIL, TOKEN)
HEADERS  = {"Accept": "application/json", "Content-Type": "application/json"}

# Layer roots
L1_ROOT = Path("Run 1/L1 Organism")
L2_ROOT = Path("Run 1/L2 Molecule")
L3_ROOT = Path("Run 1/L3 Codebase")

# L2 master files (title → filename stem)
L2_PAGES = [
    ("MASTER_BUSINESS_ANALYST",     "Master Business Analyst"),
    ("MASTER_DATA_ARCHITECT",       "Master Data Architect"),
    ("MASTER_DEVOPS",               "Master DevOps"),
    ("MASTER_ENTERPRISE_ARCHITECT", "Master Enterprise Architect"),
    ("MASTER_SOLUTION_ARCHITECT",   "Master Solution Architect"),
]

# L3 analyst section keys
L3_SECTIONS = [
    ("01_business_analyst",     "Business Analyst"),
    ("02_data_architect",       "Data Architect"),
    ("03_devops_operations",    "DevOps and Operations"),
    ("04_enterprise_architect", "Enterprise Architect"),
    ("05_solution_architect",   "Solution Architect"),
]

L3_FILE_RE = re.compile(
    r"L3_Code_(.+?)_"
    r"(?:01_business_analyst|02_data_architect|03_devops_operations"
    r"|04_enterprise_architect|05_solution_architect)\.md$"
)

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
        "status":   "current",
        "spaceId":  space_id,
        "parentId": str(parent_id),
        "body":     {"representation": "storage", "value": body},
    }
    r = requests.post(f"{BASE_URL}/pages", json=payload, auth=AUTH, headers=HEADERS)
    if not r.ok:
        raise SystemExit(f"ERROR creating '{title}': {r.status_code}\n{r.text[:600]}")
    return r.json()


def update_page(page_id: str, title: str, current_version: int, body: str,
                parent_id: str = None) -> dict:
    payload = {
        "id":      str(page_id),
        "title":   title,
        "status":  "current",
        "version": {"number": current_version + 1, "message": "Synced via GitHub Actions"},
        "body":    {"representation": "storage", "value": body},
    }
    if parent_id is not None:
        payload["parentId"] = str(parent_id)
    r = requests.put(f"{BASE_URL}/pages/{page_id}", json=payload, auth=AUTH, headers=HEADERS)
    if not r.ok:
        raise SystemExit(f"ERROR updating '{title}': {r.status_code}\n{r.text[:600]}")
    return r.json()


def ensure_page(title: str, space_id: str, parent_id: str, body: str) -> dict:
    existing = find_page(title, space_id, parent_id)
    if existing:
        ver = existing.get("version", {}).get("number", 1)
        page = update_page(existing["id"], title, ver, body)
        print(f"  [updated] {title}")
        return page

    # Page not found under the expected parent — try to create it.
    r = requests.post(
        f"{BASE_URL}/pages",
        json={
            "title":    title,
            "status":   "current",
            "spaceId":  space_id,
            "parentId": str(parent_id),
            "body":     {"representation": "storage", "value": body},
        },
        auth=AUTH, headers=HEADERS,
    )

    if r.ok:
        print(f"  [created] {title}")
        return r.json()

    err_text = r.text
    # Handle: page exists but under a different parent (orphaned from a prior run)
    if r.status_code == 400 and "already exists" in err_text:
        orphan = find_page(title, space_id)  # search without parent filter
        if orphan:
            ver = orphan.get("version", {}).get("number", 1)
            page = update_page(orphan["id"], title, ver, body, parent_id)
            print(f"  [moved+updated] {title}")
            return page

    # Handle: content rejected — retry with sanitized HTML
    if r.status_code == 400 and "unsupported" in err_text.lower():
        clean_body = sanitize_storage(body)
        r2 = requests.post(
            f"{BASE_URL}/pages",
            json={
                "title":    title,
                "status":   "current",
                "spaceId":  space_id,
                "parentId": str(parent_id),
                "body":     {"representation": "storage", "value": clean_body},
            },
            auth=AUTH, headers=HEADERS,
        )
        if r2.ok:
            print(f"  [created-sanitized] {title}")
            return r2.json()
        raise SystemExit(f"ERROR creating '{title}' (sanitized): {r2.status_code}\n{r2.text[:600]}")

    raise SystemExit(f"ERROR creating '{title}': {r.status_code}\n{err_text[:600]}")


# ---------------------------------------------------------------------------
# Markdown → Confluence storage format
# ---------------------------------------------------------------------------

# Regex to strip class/lang attributes that some Confluence editors reject
_CODE_CLASS_RE = re.compile(r'<code\s+class="[^"]*">', re.IGNORECASE)


def sanitize_storage(html_body: str) -> str:
    """Remove attributes from <code> tags, replace box-drawing / arrow characters,
    and escape ALL curly braces so Confluence does not treat {macro} syntax as macros."""
    # Strip class attribute from <code class="..."> tags
    cleaned = _CODE_CLASS_RE.sub("<code>", html_body)
    # Replace Unicode box-drawing characters with ASCII equivalents.
    # Note: ← is handled via str.replace below because "<-" is invalid XML in text content.
    box_map = str.maketrans({
        "─": "-", "│": "|", "┌": "+", "┐": "+",
        "└": "+", "┘": "+", "├": "+", "┤": "+",
        "┬": "+", "┴": "+", "┼": "+",
        "═": "=", "║": "|", "╔": "+", "╗": "+",
        "╚": "+", "╝": "+", "╠": "+", "╣": "+",
        "╦": "+", "╩": "+", "╬": "+",
        "→": "->", "⇒": "=>",
        "–": "-", "•": "*",
    })
    cleaned = cleaned.translate(box_map)
    cleaned = cleaned.replace("←", "&lt;-")
    # Escape ALL curly braces globally — prevents Confluence wiki macro detection
    # regardless of whether they are in code spans, code blocks, or paragraph text.
    cleaned = cleaned.replace("{", "&#123;").replace("}", "&#125;")
    return cleaned


def md_to_storage(text: str) -> str:
    raw = mdlib.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    return sanitize_storage(raw)


def read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


# ---------------------------------------------------------------------------
# Layer sync functions
# ---------------------------------------------------------------------------

def sync_l1(space_id: str, run1_id: str):
    print("\n── L1 Organism ──────────────────────────────────────")
    l1 = ensure_page(
        "L1 Organism", space_id, run1_id,
        "<p>Single authoritative synthesis of the full Onbe 363-repository "
        "technology estate assessment (May 2026).</p>"
    )
    path = L1_ROOT / "FINAL_COMBINED_REPORT.md"
    if path.exists():
        ensure_page(
            "FINAL_COMBINED_REPORT", space_id, l1["id"],
            md_to_storage(read_md(path))
        )
    else:
        print(f"  [skip] FINAL_COMBINED_REPORT.md not found at {path}")


def sync_l2(space_id: str, run1_id: str):
    print("\n── L2 Molecule ──────────────────────────────────────")
    l2 = ensure_page(
        "L2 Molecule", space_id, run1_id,
        "<p>Master synthesis documents across 5 specialist viewpoints "
        "covering all 363 repositories (May 2026).</p>"
    )
    for stem, title in L2_PAGES:
        path = L2_ROOT / f"{stem}.md"
        if path.exists():
            ensure_page(title, space_id, l2["id"], md_to_storage(read_md(path)))
        else:
            print(f"  [skip] {stem}.md not found")


def sync_l3(space_id: str, run1_id: str, repos: set):
    print(f"\n── L3 Codebase ({len(repos)} repos) ──────────────────────────")
    l3 = ensure_page(
        "L3 Codebase", space_id, run1_id,
        "<p>Per-repository L3 codebase analysis — 363 repositories, "
        "5 specialist viewpoints each (May 2026).</p>"
    )
    ok, failed = 0, 0
    for repo in sorted(repos):
        try:
            parts = []
            for key, label in L3_SECTIONS:
                path = L3_ROOT / f"L3_Code_{repo}_{key}.md"
                label_safe = html.escape(label)
                content = md_to_storage(read_md(path)) if path.exists() \
                    else "<p><em>File not found.</em></p>"
                parts.append(f"<h2>{label_safe}</h2>\n{content}")
            ensure_page(repo, space_id, l3["id"], "\n".join(parts))
            ok += 1
        except SystemExit as e:
            print(f"  [FAILED] {repo} — {e}")
            failed += 1
    print(f"  L3 result: {ok} synced, {failed} failed")
    return failed


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def detect_layers(changed_files: list) -> tuple:
    """Return (sync_l1, sync_l2, repos_l3) based on changed file list.
    Empty file list means full sync."""
    if not changed_files:
        repos = {
            m.group(1)
            for p in L3_ROOT.glob("L3_Code_*_01_business_analyst.md")
            if (m := L3_FILE_RE.search(p.name))
        }
        return True, True, repos

    do_l1 = any("L1 Organism" in f for f in changed_files)
    do_l2 = any("L2 Molecule" in f for f in changed_files)
    repos  = {
        m.group(1)
        for f in changed_files
        if (m := L3_FILE_RE.search(Path(f).name))
    }
    return do_l1, do_l2, repos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    changed = sys.argv[1:]
    do_l1, do_l2, repos_l3 = detect_layers(changed)

    if not do_l1 and not do_l2 and not repos_l3:
        print("No relevant changes detected. Nothing to sync.")
        return

    print("=" * 60)
    print(f"L1 Organism : {'YES' if do_l1 else 'skip'}")
    print(f"L2 Molecule : {'YES' if do_l2 else 'skip'}")
    print(f"L3 Codebase : {len(repos_l3)} repo(s)")
    print("=" * 60)

    space_id = get_space_id()
    print(f"Space ID    : {space_id}")

    # Ensure root "Run 1" page under Haiintel Team folder
    run1 = ensure_page(
        "Run 1", space_id, FOLDER_ID,
        "<p>Analysis output from the Onbe 363-repository technology "
        "estate assessment conducted in May 2026.</p>"
    )

    total_failures = 0

    if do_l1:
        sync_l1(space_id, run1["id"])

    if do_l2:
        sync_l2(space_id, run1["id"])

    if repos_l3:
        total_failures += sync_l3(space_id, run1["id"], repos_l3)

    print("\n" + "=" * 60)
    print("Sync complete." if total_failures == 0 else f"Sync finished with {total_failures} failure(s).")
    print("=" * 60)

    if total_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
