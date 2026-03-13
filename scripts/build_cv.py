from pathlib import Path
import base64
import re
import yaml
import markdown

ROOT = Path(__file__).resolve().parents[1]
SITE_INDEX = ROOT / "content" / "_index.md"
AUTHOR_DIR = ROOT / "content" / "authors" / "matthijs"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.html"
STYLE_FILE = ROOT / "cv" / "style.css"
OUTPUT_HTML = ROOT / "cv" / "cv_generated.html"


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


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

    # Convert bare URL lines into clickable links
    text = re.sub(r"(?m)^(https?://\S+)\s*$", r"<\1>", text)

    return text


def md_to_html(text: str) -> str:
    text = clean_markdown_block(text)
    if not text:
        return ""
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )


def extract_block_title(site_text: str, block_id: str, fallback: str) -> str:
    pattern = (
        rf"(?ms)^-\s*block:.*?\n"
        rf"\s+id:\s*{re.escape(block_id)}\s*\n"
        rf".*?"
        rf"^\s+content:\s*\n"
        rf".*?"
        rf"^\s+title:\s*\"?(.*?)\"?\s*$"
    )
    match = re.search(pattern, site_text)
    if not match:
        return fallback
    title = match.group(1).strip()
    return title if title else fallback


def extract_text_block(site_text: str, block_id: str) -> str:
    """
    Extract only the lines that belong to:
      text: |
        ...
    and stop before sibling keys like button:, headings:, design:, etc.
    """
    lines = site_text.splitlines()

    # Find the block with id: <block_id>
    block_start = None
    for i, line in enumerate(lines):
        if re.match(rf"^\s+id:\s*{re.escape(block_id)}\s*$", line):
            block_start = i
            break

    if block_start is None:
        return ""

    # Find the "text: |" line after block_start
    text_line_index = None
    text_indent = None
    for i in range(block_start, len(lines)):
        line = lines[i]
        m = re.match(r"^(\s+)text:\s*\|\s*$", line)
        if m:
            text_line_index = i
            text_indent = len(m.group(1))
            break

        # stop if next top-level block starts before text was found
        if i > block_start and re.match(r"^\s*-\s*block:", line):
            break

    if text_line_index is None:
        return ""

    # Collect only lines indented more than the text: line
    collected = []
    for i in range(text_line_index + 1, len(lines)):
        line = lines[i]

        # blank lines belong to the text block
        if line.strip() == "":
            collected.append("")
            continue

        indent = len(line) - len(line.lstrip(" "))

        # text block content must be more indented than the text: line itself
        if indent <= text_indent:
            break

        collected.append(line)

    if not collected:
        return ""

    # remove common leading indentation
    nonempty = [ln for ln in collected if ln.strip()]
    min_indent = min(len(ln) - len(ln.lstrip(" ")) for ln in nonempty) if nonempty else 0
    normalized = [ln[min_indent:] if len(ln) >= min_indent else ln.lstrip() for ln in collected]

    return clean_markdown_block("\n".join(normalized).strip())


def get_site_sections():
    site_text = read_text_file(SITE_INDEX)

    return {
        "bio": {
            "title": "About",
            "text": extract_text_block(site_text, "bio"),
        },
        "training": {
            "title": extract_block_title(site_text, "training", "Additional Training"),
            "text": extract_text_block(site_text, "training"),
        },
        "teaching": {
            "title": extract_block_title(site_text, "teaching", "Teaching & Mentoring"),
            "text": extract_text_block(site_text, "teaching"),
        },
        "engagement": {
            "title": extract_block_title(site_text, "engagement", "Scientific Engagement & Outreach"),
            "text": extract_text_block(site_text, "engagement"),
        },
        "skills": {
            "title": extract_block_title(site_text, "skills", "Skills & Methods"),
            "text": extract_text_block(site_text, "skills"),
        },
        "awards": {
            "title": extract_block_title(site_text, "awards", "Awards & Grants"),
            "text": extract_text_block(site_text, "awards"),
        },
        "presentations": {
            "title": extract_block_title(site_text, "presentations", "Summary of Presentations at Conferences"),
            "text": extract_text_block(site_text, "presentations"),
        },
    }


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


def format_publication_html(front_matter: dict) -> str:
    authors_text = format_authors(front_matter.get("authors", []))
    date = str(front_matter.get("date", ""))
    year = date[:4] if len(date) >= 4 else "n.d."
    title = front_matter.get("title", "Untitled")
    publication = front_matter.get("publication", "")
    pub_types = front_matter.get("publication_types", [])
    pub_type = pub_types[0] if pub_types else ""
    label = pub_type_label(pub_type)
    doi = front_matter.get("doi", "")

    parts = [f"{authors_text} ({year}). <em>{title}</em>."]
    if publication:
        parts.append(f"{publication}.")
    if label:
        parts.append(label)
    if doi:
        parts.append(f'<a href="https://doi.org/{doi}">https://doi.org/{doi}</a>')

    return "<li>" + " ".join(parts) + "</li>"


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


def find_avatar_data_uri():
    if not AUTHOR_DIR.exists():
        return ""

    # Prefer exact avatar filename first
    preferred = [
        AUTHOR_DIR / "avatar.jpg",
        AUTHOR_DIR / "avatar.jpeg",
        AUTHOR_DIR / "avatar.png",
        AUTHOR_DIR / "avatar.webp",
    ]

    for img_path in preferred:
        if img_path.exists():
            suffix = img_path.suffix.lower()
            if suffix in [".jpg", ".jpeg"]:
                mime = "image/jpeg"
            elif suffix == ".png":
                mime = "image/png"
            elif suffix == ".webp":
                mime = "image/webp"
            else:
                continue

            encoded = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"

    return ""


def build_bio_block(sections):
    bio_text = md_to_html(sections.get("bio", {}).get("text", ""))
    avatar_src = find_avatar_data_uri()

    avatar_html = ""
    if avatar_src:
        avatar_html = f'<img class="hero-avatar" src="{avatar_src}" alt="Matthijs Moerkerke">'

    return f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-top">
      <div class="hero-avatar-wrap">
        {avatar_html}
      </div>
      <div class="hero-heading">
        <h1>Matthijs Moerkerke</h1>
        <div class="hero-subtitle">Neuroscientist</div>
        <div class="hero-affiliation">
          Ghent University — Spine, Head and Pain Research Unit, Department of Rehabilitation Sciences<br>
          KU Leuven — Center for Developmental Psychiatry, Department of Neurosciences
        </div>
      </div>
    </div>

    <div class="hero-bio">
      {bio_text}
    </div>
  </div>

  <div class="hero-right">
    <div><strong>Email</strong><br>matthijs.moerkerke@ugent.be</div>
    <div><strong>LinkedIn</strong><br><a href="https://www.linkedin.com/in/matthijs-moerkerke/">linkedin.com/in/matthijs-moerkerke</a></div>
    <div><strong>ORCID</strong><br><a href="https://orcid.org/0000-0002-7133-8418">orcid.org/0000-0002-7133-8418</a></div>
    <div><strong>Website</strong><br><a href="https://matthijsmoerkerke.com">matthijsmoerkerke.com</a></div>
  </div>
</div>
""".strip()


def build_markdown_section(sections, sec_id: str, fallback_title: str) -> str:
    sec = sections.get(sec_id, {})
    title = sec.get("title", fallback_title)
    body = md_to_html(sec.get("text", ""))

    if not body:
        return ""

    return f"""
<section class="cv-section">
  <h2>{title}</h2>
  <div class="section-body">
    {body}
  </div>
</section>
""".strip()


def build_publications_section():
    pubs = collect_publications()
    metrics = read_scholar_metrics()
    pub_items = "\n".join(format_publication_html(p) for p in pubs)

    return f"""
<section class="cv-section">
  <h2>Publications</h2>

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

  <ol class="pub-list">
    {pub_items}
  </ol>
</section>
""".strip()


def main():
    sections = get_site_sections()
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    style = STYLE_FILE.read_text(encoding="utf-8")

    replacements = {
        "{{STYLE}}": style,
        "{{BIO_BLOCK}}": build_bio_block(sections),
        "{{TRAINING_SECTION}}": build_markdown_section(sections, "training", "Additional Training"),
        "{{TEACHING_SECTION}}": build_markdown_section(sections, "teaching", "Teaching & Mentoring"),
        "{{ENGAGEMENT_SECTION}}": build_markdown_section(sections, "engagement", "Scientific Engagement & Outreach"),
        "{{SKILLS_SECTION}}": build_markdown_section(sections, "skills", "Skills & Methods"),
        "{{AWARDS_SECTION}}": build_markdown_section(sections, "awards", "Awards & Grants"),
        "{{PRESENTATIONS_SECTION}}": build_markdown_section(sections, "presentations", "Summary of Presentations at Conferences"),
        "{{PUBLICATIONS_SECTION}}": build_publications_section(),
    }

    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)

    OUTPUT_HTML.write_text(output, encoding="utf-8")
    print(f"Using homepage source: {SITE_INDEX}")
    print(f"Using avatar directory: {AUTHOR_DIR}")
    print(f"Generated {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
