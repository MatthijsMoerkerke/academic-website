from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE_INDEX = ROOT / "content" / "_index.md"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.md"
PRESENTATIONS_FILE = ROOT / "cv" / "presentations.md"
OUTPUT_MD = ROOT / "cv" / "cv_generated.md"


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def extract_block_text(site_text: str, block_id: str) -> str:
    """
    Extracts the markdown text: | block for a given section id from content/_index.md
    using the pattern:
      id: <block_id>
      content:
        title: ...
        text: |
          ...
    """
    pattern = (
        rf"id:\s*{re.escape(block_id)}\s+"
        rf"content:\s+"
        rf"title:\s*.*?\s+"
        rf"text:\s*\|\s*"
        rf"(.*?)"
        rf"(?=\n\s*#\s*----------------|\n\s*-\s*block:|\Z)"
    )

    m = re.search(pattern, site_text, flags=re.DOTALL)
    if not m:
        return ""

    block = m.group(1).strip("\n")
    lines = block.splitlines()

    # remove common leading indentation
    stripped = [ln.rstrip() for ln in lines]
    nonempty = [ln for ln in stripped if ln.strip()]
    if not nonempty:
        return ""

    indents = []
    for ln in nonempty:
        leading = len(ln) - len(ln.lstrip(" "))
        indents.append(leading)
    base_indent = min(indents) if indents else 0

    cleaned = []
    for ln in stripped:
        if len(ln) >= base_indent:
            cleaned.append(ln[base_indent:])
        else:
            cleaned.append(ln.lstrip())

    text = "\n".join(cleaned).strip()
    return clean_markdown_block(text)


def read_site_sections():
    site_text = read_text_file(SITE_INDEX)

    sections = {
        "bio": {
            "title": "About",
            "text": extract_block_text(site_text, "bio"),
        },
        "training": {
            "title": "Additional Training",
            "text": extract_block_text(site_text, "training"),
        },
        "teaching": {
            "title": "Teaching & Mentoring",
            "text": extract_block_text(site_text, "teaching"),
        },
        "engagement": {
            "title": "Scientific Engagement & Outreach",
            "text": extract_block_text(site_text, "engagement"),
        },
        "skills": {
            "title": "Skills & Methods",
            "text": extract_block_text(site_text, "skills"),
        },
        "awards": {
            "title": "Awards & Grants",
            "text": extract_block_text(site_text, "awards"),
        },
        "presentations": {
            "title": "Summary of Presentations at Conferences",
            "text": extract_block_text(site_text, "presentations"),
        },
    }

    return sections


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


def clean_markdown_block(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    cleaned_lines = []
    for line in text.split("\n"):
        line = line.rstrip()
        line = re.sub(r"[ \t]{2,}", " ", line)
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    # keep list continuation indentation clean
    text = re.sub(r"\n {6,}", "\n  ", text)

    return text


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
    return section_markdown("About", site_sections.get("bio", {}).get("text", ""))


def build_training_section(site_sections):
    sec = site_sections.get("training", {})
    return section_markdown(sec.get("title", "Additional Training"), sec.get("text", ""))


def build_teaching_section(site_sections):
    sec = site_sections.get("teaching", {})
    return section_markdown(sec.get("title", "Teaching & Mentoring"), sec.get("text", ""))


def build_engagement_section(site_sections):
    sec = site_sections.get("engagement", {})
    return section_markdown(sec.get("title", "Scientific Engagement & Outreach"), sec.get("text", ""))


def build_skills_section(site_sections):
    sec = site_sections.get("skills", {})
    return section_markdown(sec.get("title", "Skills & Methods"), sec.get("text", ""))


def build_awards_section(site_sections):
    sec = site_sections.get("awards", {})
    return section_markdown(sec.get("title", "Awards & Grants"), sec.get("text", ""))


def build_presentations_section(site_sections):
    sec = site_sections.get("presentations", {})
    body = sec.get("text", "")
    if not body and PRESENTATIONS_FILE.exists():
        body = PRESENTATIONS_FILE.read_text(encoding="utf-8").strip()
    return section_markdown(sec.get("title", "Summary of Presentations at Conferences"), body)


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
        "{{PRESENTATIONS_SECTION}}": build_presentations_section(site_sections),
        "{{PUBLICATIONS_SECTION}}": build_publications_section(),
    }

    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)

    OUTPUT_MD.write_text(output, encoding="utf-8")
    print(f"Using homepage source: {SITE_INDEX}")
    print(f"Generated {OUTPUT_MD}")


if __name__ == "__main__":
    main()
