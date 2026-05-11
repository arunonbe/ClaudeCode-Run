#!/usr/bin/env python3
"""
delete_confluence.py — Delete all pages under 'Run 1' in the OT Confluence space.

Pages are moved to Confluence trash (soft-delete). They can be recovered from
Confluence Trash if needed within the retention window.

Usage:
  python delete_confluence.py          # prompts for confirmation
  python delete_confluence.py --yes    # skip confirmation (for CI/CD)
"""

import os
import sys
import requests

DOMAIN    = os.environ["ATLASSIAN_DOMAIN"]
EMAIL     = os.environ["ATLASSIAN_EMAIL"]
TOKEN     = os.environ["ATLASSIAN_API_TOKEN"]
FOLDER_ID = os.environ["CONFLUENCE_FOLDER_ID"]
SPACE_KEY = "OT"

BASE_URL = f"https://{DOMAIN}/wiki/api/v2"
AUTH     = (EMAIL, TOKEN)
HEADERS  = {"Accept": "application/json", "Content-Type": "application/json"}


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


def delete_page(page_id: str, title: str):
    r = requests.delete(
        f"{BASE_URL}/pages/{page_id}",
        auth=AUTH, headers=HEADERS
    )
    if r.ok or r.status_code == 404:
        print(f"  [deleted] {title}")
    else:
        print(f"  [FAILED]  {title} — {r.status_code}: {r.text[:200]}")


def delete_tree(page_id: str, title: str, depth: int = 0):
    """Delete all children recursively (leaves first), then delete this page."""
    children = get_children(page_id)
    for child in children:
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


def main():
    auto_yes = "--yes" in sys.argv

    space_id = get_space_id()
    print(f"Space ID : {space_id}")

    run1 = find_run1(space_id)
    if not run1:
        print("'Run 1' page not found under the configured folder. Nothing to delete.")
        return

    print(f"Found    : 'Run 1' (ID: {run1['id']})")
    print()

    if not auto_yes:
        confirm = input(
            "WARNING: This will permanently move 'Run 1' and ALL its child pages "
            "(L1, L2, L3 — all 363 repos) to the Confluence trash.\n"
            "Type 'yes' to confirm: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted — no pages were deleted.")
            return

    print("\nDeleting pages (children first, then parents)...\n")
    delete_tree(run1["id"], run1["title"])

    print("\n" + "=" * 50)
    print("Delete complete. Pages are in Confluence Trash.")
    print("=" * 50)


if __name__ == "__main__":
    main()
