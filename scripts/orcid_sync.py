import os
import re
import requests
import yaml
from slugify import slugify

ORCID = "0000-0002-7133-8418"
BASE_DIR = "content/publications"

url = f"https://pub.orcid.org/v3.0/{ORCID}/works"
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()
data = response.json()

works = data.get("group", [])


def safe_get_title(work):
    summary = work["work-summary"][0]
    title = (
        summary.get("title", {})
        .get("title", {})
        .get("value", "")
        .strip()
    )
    return title


def safe_get_year(work):
    summary = work["work-summary"][0]
    year = (
        summary.get("publication-date", {})
        .get("year", {})
        .get("value")
    )
    if year and year.isdigit():
        return year
    return "2024"


def safe_get_journal(work):
    summary = work["work-summary"][0]
    journal = summary.get("journal-title", {}).get("value", "")
    return journal.strip()


def safe_get_doi(work):
    summary = work["work-summary"][0]
    external_ids = summary.get("external-ids", {}).get("external-id", [])
    for item in external_ids:
        if item.get("external-id-type", "").lower() == "doi":
            return item.get("external-id-value", "").strip()
    return ""


def build_bibtex_key(title, year):
    first_word = re.sub(r"[^a-zA-Z0-9]", "", title.split()[0].lower()) if title.split() else "paper"
    return f"moerkerke{year}{first_word}"


os.makedirs(BASE_DIR, exist_ok=True)

created = 0
skipped = 0

for work in works:
    title = safe_get_title(work)
    if not title:
        skipped += 1
        continue

    year = safe_get_year(work)
    journal = safe_get_journal(work)
    doi = safe_get_doi(work)

    slug = slugify(title)
    folder = os.path.join(BASE_DIR, slug)
    index_path = os.path.join(folder, "index.md")
    bib_path = os.path.join(folder, "cite.bib")

    if os.path.exists(folder):
        skipped += 1
        continue

    os.makedirs(folder, exist_ok=True)

    frontmatter = {
        "title": title,
        "authors": ["Matthijs Moerkerke"],
        "date": f"{year}-01-01",
        "publication_types": ["article-journal"],
        "publication": journal if journal else "Unknown journal",
        "doi": doi,
        "featured": False,
        "draft": False,
        "summary": "",
        "tags": [],
    }

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(frontmatter, f, sort_keys=False, allow_unicode=True)
        f.write("---\n")

    bibtex_key = build_bibtex_key(title, year)
    bibtex = (
        f"@article{{{bibtex_key},\n"
        f"  title = {{{title}}},\n"
        f"  author = {{Moerkerke, Matthijs}},\n"
        f"  journal = {{{journal if journal else 'Unknown journal'}}},\n"
        f"  year = {{{year}}},\n"
    )
    if doi:
        bibtex += f"  doi = {{{doi}}},\n"
    bibtex += "}\n"

    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(bibtex)

    created += 1

print(f"Created {created} new publication folders, skipped {skipped} existing/invalid works.")
