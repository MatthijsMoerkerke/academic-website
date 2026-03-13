from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.md"
PRESENTATIONS_FILE = ROOT / "cv" / "presentations.md"
OUTPUT_MD = ROOT / "cv" / "cv_generated.md"


def read_front_matter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


def looks_like_homepage_sections(data: dict) -> bool:
    if not isinstance(data, dict):
        return False

    sections = data.get("sections")
    if not isinstance(sections, list):
        return False

    ids = {
        sec.get("id")
        for sec in sections
        if isinstance(sec, dict)
    }

    expected_ids = {
        "bio",
        "training",
        "teaching",
        "engagement",
        "skills",
        "awards",
        "publications",
    }
    return len(ids.intersection(expected_ids)) >= 3


def resolve_site_index_and_data():
    checked = []

    for path in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            data = read_front_matter(path)
        except Exception as exc:
            checked.append(f"{path} (parse error: {exc})")
            continue

        if not isinstance(data, dict):
            checked.append(f"{path} (no usable front matter)")
            continue

        if looks_like_homepage_sections(data):
            return path, data

        checked.append(f"{path} (not homepage sections file)")

    raise RuntimeError(
        "Could not find the homepage file with landing-page sections. Checked:\n- "
        + "\n- ".join(str(x) for x in checked[:50])
    )


SITE_INDEX, SITE_DATA = resolve_site_index_and_data()


def read_site_sections():
    sections = SITE_DATA.get("sections") or []
    out = {}

    for sec in sections:
        if not isinstance(sec, dict):
            continue

        sec_id = sec.get("id", "")
        content = sec.get("content", {}) or {}

        out[sec_id] = {
            "title": content.get("title", ""),
            "text": content.get("text", "") or "",
            "raw": sec,
        }

    return out


def read_scholar_metrics():
    if not SCHOLAR_FILE.exists():
        return {"citations": 0, "h_index": 0, "profile": ""}

    data = yaml.safe_load(SCHOLAR_FILE.read_text(encoding="utf-8")) or {}
    return {
        "citations": data.get("citations", 0),
        "h_index": data.get("h_index", 0),
        "profile": data.get("profile", ""),
    }


def read_publication_front_matter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


def pub_type_label(pub_type: str) -> str:
    mapping = {
        "article-journal": "",
        "preprint": "Preprint.",
        "paper-conference": "Conference paper.",
        "thesis": "PhD dissertation.",
        "chapter": "Book chapter.",
        "manuscript": "Manuscript.",
    }
    return mapping.get(pub_type, "")


def format_authors(authors):
    if not authors:
        return "Unknown authors"
    return ", ".join(authors)


def format_publication(front_matter: dict) -> str:
    authors_text = format_authors(front_matter.get("authors", []))

    date = str(front_matter.get("date", ""))
    year = date[:4] if len(date) >= 4 else "n.d."

    title = front_matter.get("title", "Untitled")
    publication = front_matter.get("publication", "")
    pub_types = front_matter.get("publication_types", [])
    pub_type = pub_types[0] if pub_types else ""
    label = pub_type_label(pub_type)
    doi = front_matter.get("doi", "")

    line = f"- {authors_text} ({year}). *{title}*."
    if publication:
        line += f" {publication}."
    if label:
        line += f" {label}"
    if doi:
        line += f" https://doi.org/{doi}"
    return line


def collect_publications():
    entries = []
    if not PUBLICATIONS_DIR.exists():
        return entries

    for folder in PUBLICATIONS_DIR.iterdir():
        if not folder.is_dir():
            continue
        index_file = folder / "index.md"
        if not index_file.exists():
            continue
        fm = read_publication_front_matter(index_file)
        if not fm:
            continue
        entries.append(fm)

    entries.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    return entries


def load_presentations():
    if not PRESENTATIONS_FILE.exists():
        return ""
    return PRESENTATIONS_FILE.read_text(encoding="utf-8").strip()


def clean_markdown_block(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    cleaned_lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", line.rstrip())
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def section_markdown(title: str, body: str) -> str:
    body = clean_markdown_block(body)
    if not body:
        return ""
    return f"## {title}\n\n{body}"


def build_bio_block():
    return """
<div class="cv-hero">
  <div class="cv-hero-main">
    <h1>Matthijs Moerkerke</h1>
    <p class="cv-role"><strong>Postdoctoral Researcher</strong></p>
    <p class="cv-affiliation">
      Ghent University — Spine, Head and Pain Research Unit, Department of Rehabilitation Sciences<br>
      KU Leuven — Center for Developmental Psychiatry, Department of Neurosciences
    </p>
  </div>

  <div class="cv-hero-side">
    <p><strong>Email:</strong> matthijs.moerkerke@ugent.be</p>
    <p><strong>LinkedIn:</strong> https://www.linkedin.com/in/matthijs-moerkerke/</p>
    <p><strong>ORCID:</strong> https://orcid.org/0000-0002-7133-8418</p>
    <p><strong>Website:</strong> https://matthijsmoerkerke.com</p>
  </div>
</div>
""".strip()


def build_profile_section(site_sections):
    bio = site_sections.get("bio", {})
    bio_text = clean_markdown_block(
        bio.get("raw", {}).get("content", {}).get("text", "")
    )
    return f"## About\n\n{bio_text}"


def build_training_section(site_sections):
    sec = site_sections.get("training", {})
    return section_markdown(sec.get("title", "Additional Training"), sec.get("text", ""))


def build_teaching_section(site_sections):
    sec = site_sections.get("teaching", {})
    return section_markdown(sec.get("title", "Teaching & Mentoring"), sec.get("text", ""))


def build_engagement_section(site_sections):
    sec = site_sections.get("engagement", {})
    return section_markdown(
        sec.get("title", "Scientific Engagement & Outreach"),
        sec.get("text", ""),
    )


def build_skills_section(site_sections):
    sec = site_sections.get("skills", {})
    return section_markdown(sec.get("title", "Skills & Methods"), sec.get("text", ""))


def build_awards_section(site_sections):
    sec = site_sections.get("awards", {})
    return section_markdown(sec.get("title", "Awards & Grants"), sec.get("text", ""))


def build_presentations_section():
    presentations = load_presentations()
    presentations = clean_markdown_block(presentations)
    if not presentations:
        return ""
    return f"## Summary of Presentations at Conferences\n\n{presentations}"


def build_publications_section():
    pubs = collect_publications()
    metrics = read_scholar_metrics()

    pub_lines = [format_publication(p) for p in pubs]
    pub_block = "\n".join(pub_lines)

    metrics_html = f"""
<div class="metrics-row">
  <div class="metric-box">
    <div class="metric-label">Citations</div>
    <div class="metric-value">{metrics.get('citations', 0)}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">h-index</div>
    <div class="metric-value">{metrics.get('h_index', 0)}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Publications</div>
    <div class="metric-value">{len(pubs)}</div>
  </div>
</div>
""".strip()

    return f"## Publications\n\n{metrics_html}\n\n{pub_block}"


def main():
    site_sections = read_site_sections()
    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    replacements = {
        "{{BIO_BLOCK}}": build_bio_block(),
        "{{ABOUT_SECTION}}": build_profile_section(site_sections),
        "{{TRAINING_SECTION}}": build_training_section(site_sections),
        "{{TEACHING_SECTION}}": build_teaching_section(site_sections),
        "{{ENGAGEMENT_SECTION}}": build_engagement_section(site_sections),
        "{{SKILLS_SECTION}}": build_skills_section(site_sections),
        "{{AWARDS_SECTION}}": build_awards_section(site_sections),
        "{{PRESENTATIONS_SECTION}}": build_presentations_section(),
        "{{PUBLICATIONS_SECTION}}": build_publications_section(),
    }

    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)

    OUTPUT_MD.write_text(output, encoding="utf-8")
    print(f"Using site index: {SITE_INDEX}")
    print(f"Generated {OUTPUT_MD}")


if __name__ == "__main__":
    main()
