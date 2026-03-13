import os
import requests
import yaml
from slugify import slugify

ORCID = "0000-0002-7133-8418"
BASE_DIR = "content/publications"
HEADERS = {"Accept": "application/json"}

WORKS_URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"


def fetch_json(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def get_title(work_detail: dict) -> str:
    return (
        work_detail.get("title", {})
        .get("title", {})
        .get("value", "")
        .strip()
    )


def get_year(work_detail: dict) -> str:
    year = (
        work_detail.get("publication-date", {})
        .get("year", {})
        .get("value", "")
        .strip()
    )
    return year if year else "2024"


def get_month(work_detail: dict) -> str:
    month = (
        work_detail.get("publication-date", {})
        .get("month", {})
        .get("value", "")
        .strip()
    )
    return month.zfill(2) if month else "01"


def get_day(work_detail: dict) -> str:
    day = (
        work_detail.get("publication-date", {})
        .get("day", {})
        .get("value", "")
        .strip()
    )
    return day.zfill(2) if day else "01"


def get_journal(work_detail: dict) -> str:
    return work_detail.get("journal-title", {}).get("value", "").strip()


def get_doi(work_detail: dict) -> str:
    external_ids = work_detail.get("external-ids", {}).get("external-id", [])
    for item in external_ids:
        if item.get("external-id-type", "").lower() == "doi":
            return item.get("external-id-value", "").strip()
    return ""


def get_url(work_detail: dict) -> str:
    return work_detail.get("url", {}).get("value", "").strip()


def get_work_type(work_detail: dict):
    work_type = work_detail.get("type", "").lower()

    mapping = {
        "journal-article": ("article-journal", "article"),
        "book-chapter": ("chapter", "incollection"),
        "conference-paper": ("paper-conference", "inproceedings"),
        "working-paper": ("manuscript", "misc"),
        "preprint": ("preprint", "misc"),
        "dissertation-thesis": ("thesis", "phdthesis"),
    }

    return mapping.get(work_type, ("article-journal", "article"))


def get_authors(work_detail: dict) -> list[str]:
    contributors = work_detail.get("contributors", {}).get("contributor", [])
    authors = []

    for contributor in contributors:
        credit_name = (
            contributor.get("credit-name", {})
            .get("value", "")
            .strip()
        )
        if credit_name:
            authors.append(credit_name)

    # fallback if ORCID work has no contributor list
    if not authors:
        authors = ["Matthijs Moerkerke"]

    # de-duplicate while preserving order
    seen = set()
    unique_authors = []
    for author in authors:
        key = author.casefold()
        if key not in seen:
            seen.add(key)
            unique_authors.append(author)

    return unique_authors


def split_author_for_bib(author: str) -> str:
    parts = author.strip().split()
    if len(parts) < 2:
        return author
    family = parts[-1]
    given = " ".join(parts[:-1])
    return f"{family}, {given}"


def build_bibtex_authors(authors: list[str]) -> str:
    return " and ".join(split_author_for_bib(a) for a in authors)


def build_bibtex_key(authors: list[str], year: str, title: str) -> str:
    first_author_last = slugify(authors[0].split()[-1]) if authors else "paper"
    first_word = slugify(title.split()[0]) if title.split() else "work"
    return f"{first_author_last}{year}{first_word}"


def write_index_md(path: str, frontmatter: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(frontmatter, f, sort_keys=False, allow_unicode=True)
        f.write("---\n")


def write_bib(
    path: str,
    entry_type: str,
    key: str,
    title: str,
    authors: list[str],
    journal: str,
    year: str,
    doi: str,
    url: str,
) -> None:
    lines = [
        f"@{entry_type}{{{key},",
        f"  title = {{{title}}},",
        f"  author = {{{build_bibtex_authors(authors)}}},",
    ]

    if journal:
        if entry_type == "incollection":
            lines.append(f"  booktitle = {{{journal}}},")
        else:
            lines.append(f"  journal = {{{journal}}},")

    lines.append(f"  year = {{{year}}},")

    if doi:
        lines.append(f"  doi = {{{doi}}},")

    if url:
        lines.append(f"  url = {{{url}}},")

    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    works_data = fetch_json(WORKS_URL)
    groups = works_data.get("group", [])

    created = 0
    skipped = 0
    errors = 0

    for group in groups:
        summaries = group.get("work-summary", [])
        if not summaries:
            skipped += 1
            continue

        summary = summaries[0]
        put_code = summary.get("put-code")
        if not put_code:
            skipped += 1
            continue

        detail_url = f"https://pub.orcid.org/v3.0/{ORCID}/work/{put_code}"

        try:
            work_detail = fetch_json(detail_url)
        except Exception as exc:
            print(f"Skipping put-code {put_code}: {exc}")
            errors += 1
            continue

        title = get_title(work_detail)
        if not title:
            skipped += 1
            continue

        year = get_year(work_detail)
        month = get_month(work_detail)
        day = get_day(work_detail)
        journal = get_journal(work_detail)
        doi = get_doi(work_detail)
        url = get_url(work_detail)
        authors = get_authors(work_detail)
        publication_type, bib_entry_type = get_work_type(work_detail)

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
            "authors": authors,
            "date": f"{year}-{month}-{day}",
            "publication_types": [publication_type],
            "publication": journal if journal else "",
            "doi": doi,
            "url_pdf": "",
            "url_code": "",
            "url_dataset": "",
            "featured": False,
            "draft": False,
            "summary": "",
            "tags": [],
        }

        write_index_md(index_path, frontmatter)

        bibtex_key = build_bibtex_key(authors, year, title)
        write_bib(
            bib_path,
            bib_entry_type,
            bibtex_key,
            title,
            authors,
            journal,
            year,
            doi,
            url,
        )

        created += 1
        print(f"Created: {folder}")

    print(
        f"Done. Created {created}, skipped {skipped}, errors {errors}."
    )


if __name__ == "__main__":
    main()
