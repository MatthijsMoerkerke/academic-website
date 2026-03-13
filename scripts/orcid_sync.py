import os
import requests
import yaml
from slugify import slugify

ORCID = "0000-0002-7133-8418"
BASE_DIR = "content/publications"

HEADERS = {"Accept": "application/json"}
WORKS_URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"


def safe_get(obj, *keys):
    for key in keys:
        if obj is None:
            return None
        obj = obj.get(key)
    return obj


def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_authors(work):
    contributors = safe_get(work, "contributors", "contributor") or []
    authors = []

    for c in contributors:
        name = safe_get(c, "credit-name", "value")
        if name:
            authors.append(name)

    if not authors:
        authors = ["Matthijs Moerkerke"]

    return authors


def get_doi(work):
    ids = safe_get(work, "external-ids", "external-id") or []
    for i in ids:
        if i.get("external-id-type", "").lower() == "doi":
            return i.get("external-id-value")
    return ""


def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    works_data = fetch_json(WORKS_URL)
    groups = works_data.get("group", [])

    created = 0
    skipped = 0

    for g in groups:

        summary = g["work-summary"][0]
        put_code = summary.get("put-code")

        detail_url = f"https://pub.orcid.org/v3.0/{ORCID}/work/{put_code}"
        work = fetch_json(detail_url)

        title = safe_get(work, "title", "title", "value")

        if not title:
            skipped += 1
            continue

        year = safe_get(work, "publication-date", "year", "value") or "2024"
        journal = safe_get(work, "journal-title", "value") or ""
        doi = get_doi(work)
        authors = get_authors(work)

        slug = slugify(title)
        folder = f"{BASE_DIR}/{slug}"

        if os.path.exists(folder):
            skipped += 1
            continue

        os.makedirs(folder)

        frontmatter = {
            "title": title,
            "authors": authors,
            "date": f"{year}-01-01",
            "publication_types": ["article-journal"],
            "publication": journal,
            "doi": doi,
            "featured": False,
            "draft": False,
        }

        with open(f"{folder}/index.md", "w") as f:
            f.write("---\n")
            yaml.safe_dump(frontmatter, f)
            f.write("---\n")

        with open(f"{folder}/cite.bib", "w") as f:
            f.write(
                f"""@article{{{slug},
  title = {{{title}}},
  author = {{{' and '.join(authors)}}},
  journal = {{{journal}}},
  year = {{{year}}},
  doi = {{{doi}}}
}}
"""
            )

        created += 1
        print("Created:", slug)

    print("Created:", created)
    print("Skipped:", skipped)


if __name__ == "__main__":
    main()
