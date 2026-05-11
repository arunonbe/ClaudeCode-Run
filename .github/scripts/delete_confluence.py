#!/usr/bin/env python3
"""
delete_confluence.py — Delete all analysis pages from the OT Confluence space.

Supports two modes:
  1. --by-parent  (default) : Delete 'Run 1' page and all children recursively.
  2. --by-creator           : Delete ALL pages created by the configured account
                              on or after 2026-05-11 (handles orphaned pages after
                              parent folders have already been manually deleted).

Pages are moved to Confluence trash (soft-delete). They can be recovered from
Confluence Trash if needed within the retention window.

Usage:
  python delete_confluence.py                   # by-parent mode, prompts confirm
  python delete_confluence.py --by-creator      # orphan cleanup mode, prompts confirm
  python delete_confluence.py --by-creator --yes  # skip confirmation (CI/CD)
"""

import os
import sys
import requests

DOMAIN    = os.environ["ATLASSIAN_DOMAIN"]
EMAIL     = os.environ["ATLASSIAN_EMAIL"]
TOKEN     = os.environ["ATLASSIAN_API_TOKEN"]
FOLDER_ID = os.environ.get("CONFLUENCE_FOLDER_ID", "")
SPACE_KEY = "OT"
CREATOR_ACCOUNT_ID = "712020:33194315-7530-42e5-9263-95eb904f0f8e"

BASE_URL  = f"https://{DOMAIN}/wiki/api/v2"
WIKI_BASE = f"https://{DOMAIN}/wiki"
AUTH      = (EMAIL, TOKEN)
HEADERS   = {"Accept": "application/json", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Helpers
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


def delete_page(page_id: str, title: str):
    r = requests.delete(
        f"{BASE_URL}/pages/{page_id}",
        auth=AUTH, headers=HEADERS
    )
    if r.ok or r.status_code == 404:
        print(f"  [deleted] {title}")
    else:
        print(f"  [FAILED]  {title} — {r.status_code}: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Mode 1: by-parent — delete Run 1 tree
# ---------------------------------------------------------------------------

def get_children(page_id: str) -> list:
    children, cursor = [], None
    while True:
        params = {"limit": 250}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(
            f"{BASE_URL}/pages/{page_id}/children",
            params=params, auth=AUTH, headers=HEADERS
        )
        r.raise_for_status()
        data = r.json()
        children.extend(data.get("results", []))
        next_url = data.get("_links", {}).get("next")
        if not next_url:
            break
        cursor = next_url.split("cursor=")[-1].split("&")[0]
    return children


def delete_tree(page_id: str, title: str, depth: int = 0):
    """Delete all children recursively (leaves first), then this page."""
    for child in get_children(page_id):
        delete_tree(child["id"], child["title"], depth + 1)
    delete_page(page_id, ("  " * depth) + title)


def find_run1(space_id: str) -> dict | None:
    r = requests.get(
        f"{BASE_URL}/pages",
        params={"title": "Run 1", "space-id": space_id, "status": "current", "limit": 25},
        auth=AUTH, headers=HEADERS
    )
    r.raise_for_status()
    pages = [
        p for p in r.json().get("results", [])
        if str(p.get("parentId")) == str(FOLDER_ID)
    ]
    return pages[0] if pages else None


def run_by_parent(space_id: str, auto_yes: bool):
    run1 = find_run1(space_id)
    if not run1:
        print("'Run 1' page not found. Nothing to delete via parent mode.")
        return

    print(f"Found : 'Run 1' (ID: {run1['id']})")
    if not auto_yes:
        confirm = input(
            "\nWARNING: This will move 'Run 1' and ALL its child pages to Confluence trash.\n"
            "Type 'yes' to confirm: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return

    print("\nDeleting (children first, then parents)...\n")
    delete_tree(run1["id"], run1["title"])


# ---------------------------------------------------------------------------
# Mode 2: by-creator — delete all orphaned pages by creator + date
# ---------------------------------------------------------------------------

def find_all_by_creator(space_id: str) -> list:
    """Return all pages created by CREATOR_ACCOUNT_ID on/after CREATED_FROM."""
    pages, start = [], 0
    cql = (
        f'space.key = "{SPACE_KEY}" '
        f'AND creator = "{CREATOR_ACCOUNT_ID}" '
        f'AND type = "page"'
    )
    while True:
        r = requests.get(
            f"{WIKI_BASE}/rest/api/search",
            params={"cql": cql, "limit": 200, "start": start,
                    "expand": "content.id,content.title"},
            auth=AUTH, headers=HEADERS
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        for item in results:
            c = item.get("content", {})
            if c.get("id") and c.get("title"):
                pages.append({"id": c["id"], "title": c["title"]})
        total = data.get("totalSize", 0)
        start += len(results)
        print(f"  Fetched {start}/{total} pages...")
        if start >= total or not results:
            break
    return pages


def run_by_creator(auto_yes: bool):
    print("Searching for all analysis pages by creator...\n")
    pages = find_all_by_creator(None)

    if not pages:
        print("No pages found. Nothing to delete.")
        return

    print(f"\nFound {len(pages)} page(s) to delete.")
    if not auto_yes:
        confirm = input(
            f"\nWARNING: This will move all {len(pages)} pages to Confluence trash.\n"
            "Type 'yes' to confirm: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return

    print("\nDeleting...\n")
    ok, failed = 0, 0
    for p in pages:
        r = requests.delete(
            f"{BASE_URL}/pages/{p['id']}",
            auth=AUTH, headers=HEADERS
        )
        if r.ok or r.status_code == 404:
            print(f"  [deleted] {p['title']}")
            ok += 1
        else:
            print(f"  [FAILED]  {p['title']} — {r.status_code}: {r.text[:200]}")
            failed += 1

    print(f"\nResult: {ok} deleted, {failed} failed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    auto_yes   = "--yes"        in sys.argv
    by_creator = "--by-creator" in sys.argv

    print("=" * 55)
    print(f"Mode     : {'by-creator (orphan cleanup)' if by_creator else 'by-parent (Run 1 tree)'}")
    print("=" * 55)

    if by_creator:
        run_by_creator(auto_yes)
    else:
        space_id = get_space_id()
        print(f"Space ID : {space_id}\n")
        run_by_parent(space_id, auto_yes)

    print("\n" + "=" * 55)
    print("Done. Deleted pages are in Confluence Trash.")
    print("=" * 55)


if __name__ == "__main__":
    main()
