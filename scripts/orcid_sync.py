import os
import re
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


def fetch_json(url, headers=None):
    r = requests.get(url, headers=headers or HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def normalize_doi(doi: str) -> str:
    doi = (doi or "").strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "").strip()
    return doi


def normalize_title(title: str) -> str:
    title = (title or "").strip().lower()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[^\w\s]", "", title)
    return title.strip()


def get_crossref_authors(doi):
    if not doi:
        return []

    url = f"https://api.crossref.org/works/{doi}"

    try:
        data = fetch_json(url, headers={"Accept": "application/json"})
        authors = []

        for a in data.get("message", {}).get("author", []):
            given = (a.get("given") or "").strip()
            family = (a.get("family") or "").strip()
            name = f"{given} {family}".strip()

            if not name:
                name = (a.get("name") or "").strip()

            if name:
                authors.append(name)

        return authors

    except Exception as e:
        print(f"Could not fetch Crossref authors for DOI {doi}: {e}")
        return []


def get_authors(work, doi=""):
    contributors = safe_get(work, "contributors", "contributor") or []
    authors = []

    for c in contributors:
        name = safe_get(c, "credit-name", "value")
        if name:
            authors.append(name)

    # If ORCID returns no authors or only one author, try Crossref
    if len(authors) <= 1 and doi:
        crossref_authors = get_crossref_authors(doi)
        if crossref_authors:
            authors = crossref_authors

    if not authors:
        authors = ["Matthijs Moerkerke"]

    return authors


def get_doi(work):
    ids = safe_get(work, "external-ids", "external-id") or []
    for i in ids:
        if i.get("external-id-type", "").lower() == "doi":
            value = i.get("external-id-value") or ""
            return normalize_doi(value)
    return ""


def read_front_matter(index_path):
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None

    return data if isinstance(data, dict) else None


def collect_existing_publications():
    existing_dois = set()
    existing_titles = set()

    if not os.path.exists(BASE_DIR):
        return existing_dois, existing_titles

    for folder_name in os.listdir(BASE_DIR):
        folder = os.path.join(BASE_DIR, folder_name)

        if not os.path.isdir(folder):
            continue

        index_path = os.path.join(folder, "index.md")
        fm = read_front_matter(index_path)

        if not fm:
            continue

        doi = normalize_doi(fm.get("doi", ""))
        title = normalize_title(fm.get("title", ""))

        if doi:
            existing_dois.add(doi)

        if title:
            existing_titles.add(title)

    return existing_dois, existing_titles


def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    existing_dois, existing_titles = collect_existing_publications()

    works_data = fetch_json(WORKS_URL)
    groups = works_data.get("group", [])

    created = 0
    skipped = 0
    skipped_by_doi = 0
    skipped_by_title = 0

    for g in groups:
        summaries = g.get("work-summary", [])

        if not summaries:
            skipped += 1
            continue

        summary = summaries[0]
        put_code = summary.get("put-code")

        if not put_code:
            skipped += 1
            continue

        detail_url = f"https://pub.orcid.org/v3.0/{ORCID}/work/{put_code}"
        work = fetch_json(detail_url)

        title = safe_get(work, "title", "title", "value")

        if not title:
            skipped += 1
            continue

        year = safe_get(work, "publication-date", "year", "value") or "2024"
        journal = safe_get(work, "journal-title", "value") or ""
        doi = get_doi(work)
        authors = get_authors(work, doi)

        normalized_title = normalize_title(title)

        # Deduplicate by DOI
        if doi and doi in existing_dois:
            skipped += 1
            skipped_by_doi += 1
            print("Skipped by DOI:", title)
            continue

        # Deduplicate by normalized title
        if normalized_title and normalized_title in existing_titles:
            skipped += 1
            skipped_by_title += 1
            print("Skipped by title:", title)
            continue

        title_slug = slugify(title)
        short_title = "-".join(title_slug.split("-")[:6]) if title_slug else "publication"
        slug = f"{year}-{short_title}"
        folder = f"{BASE_DIR}/{slug}"

        if os.path.exists(folder):
            skipped += 1
            print("Skipped existing folder:", slug)
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

        with open(f"{folder}/index.md", "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(frontmatter, f, sort_keys=False, allow_unicode=True)
            f.write("---\n")

        with open(f"{folder}/cite.bib", "w", encoding="utf-8") as f:
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

        # Update dedupe sets
        if doi:
            existing_dois.add(doi)

        if normalized_title:
            existing_titles.add(normalized_title)

        created += 1
        print("Created:", slug)

    print("Created:", created)
    print("Skipped:", skipped)
    print("Skipped by DOI:", skipped_by_doi)
    print("Skipped by title:", skipped_by_title)


if __name__ == "__main__":
    main()
