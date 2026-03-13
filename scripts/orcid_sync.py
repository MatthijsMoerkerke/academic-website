import os
import requests
import yaml
from slugify import slugify

ORCID = "0000-0002-7133-8418"
BASE_DIR = "content/publications"

URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"
HEADERS = {"Accept": "application/json"}


def get_title(summary):
    return (
        summary.get("title", {})
        .get("title", {})
        .get("value", "")
        .strip()
    )


def get_year(summary):
    year = (
        summary.get("publication-date", {})
        .get("year", {})
        .get("value", "")
        .strip()
    )
    return year if year else "2024"


def get_journal(summary):
    return summary.get("journal-title", {}).get("value", "").strip()


def get_external_ids(summary):
    return summary.get("external-ids", {}).get("external-id", [])


def get_doi(summary):
    for item in get_external_ids(summary):
        if item.get("external-id-type", "").lower() == "doi":
            return item.get("external-id-value", "").strip()
    return ""


def get_work_type(summary):
    work_type = summary.get("type", "").lower()

    mapping = {
        "journal-article": ("article-journal", "article"),
        "book-chapter": ("chapter", "incollection"),
        "conference-paper": ("paper-conference", "inproceedings"),
        "working-paper": ("manuscript", "misc"),
        "preprint": ("preprint", "misc"),
    }

    return mapping.get(work_type, ("article-journal", "article"))


def build_bibtex_key(title, year):
    first_word = slugify(title.split()[0]) if title.split() else "paper"
    return f"moerkerke{year}{first_word}"


def write_index_md(path, frontmatter):
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(frontmatter, f, sort_keys=False, allow_unicode=True)
        f.write("---\n")


def write_bib(path, entry_type, key, title, journal, year, doi):
    lines = [
        f"@{entry_type}{{{key},",
        f"  title = {{{title}}},",
        f"  author = {{Moerkerke, Matthijs}},",
    ]

    if journal:
        if entry_type == "incollection":
            lines.append(f"  booktitle = {{{journal}}},")
        else:
            lines.append(f"  journal = {{{journal}}},")

    lines.append(f"  year = {{{year}}},")

    if doi:
        lines.append(f"  doi = {{{doi}}},")

    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()

    works = data.get("group", [])
    created = 0
    skipped = 0

    for group in works:
        summaries = group.get("work-summary", [])
        if not summaries:
            skipped += 1
            continue

        summary = summaries[0]

        title = get_title(summary)
        if not title:
            skipped += 1
            continue

        year = get_year(summary)
        journal = get_journal(summary)
        doi = get_doi(summary)
        publication_type, bib_entry_type = get_work_type(summary)

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
            "publication_types": [publication_type],
            "publication": journal if journal else "",
            "doi": doi,
            "featured": False,
            "draft": False,
            "summary": "",
            "tags": [],
        }

        write_index_md(index_path, frontmatter)

        bibtex_key = build_bibtex_key(title, year)
        write_bib(
            bib_path,
            bib_entry_type,
            bibtex_key,
            title,
            journal,
            year,
            doi,
        )

        created += 1

    print(f"Created {created} publication folders, skipped {skipped} existing or invalid works.")


if __name__ == "__main__":
    main()
