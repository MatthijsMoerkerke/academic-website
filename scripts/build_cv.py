from pathlib import Path
import base64
import re
import yaml
import markdown

ROOT = Path(__file__).resolve().parents[1]
SITE_INDEX = ROOT / "content" / "_index.md"
AUTHOR_DIR = ROOT / "content" / "authors" / "me"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.html"
STYLE_FILE = ROOT / "cv" / "style.css"
OUTPUT_HTML = ROOT / "cv" / "cv_generated.html"


def read_front_matter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise RuntimeError(f"{md_path} does not start with YAML front matter.")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError(f"Could not parse front matter in {md_path}")
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise RuntimeError(f"Front matter in {md_path} is not a YAML mapping.")
    return data


def clean_markdown_block(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    lines = []
    for line in text.split("\n"):
        line = line.rstrip()
        line = re.sub(r"[ \t]{2,}", " ", line)
        lines.append(line)

    text = "\n".join(lines).strip()

    # Make bare URL lines clickable in Markdown
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


def get_site_sections():
    data = read_front_matter(SITE_INDEX)
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise RuntimeError(
            f"'sections' in {SITE_INDEX} is not a list. "
            "Check that homepage blocks are properly indented under sections:."
        )
    return sections


def get_section(sections, sec_id: str):
    for sec in sections:
        if isinstance(sec, dict) and sec.get("id") == sec_id:
            return sec
    return {}


def get_section_title(sec: dict, fallback: str) -> str:
    content = sec.get("content", {}) or {}
    return content.get("title", fallback)


def get_section_text(sec: dict) -> str:
    content = sec.get("content", {}) or {}
    return content.get("text", "") or ""


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

    for ext in ("png", "jpg", "jpeg", "webp"):
        files = list(AUTHOR_DIR.glob(f"avatar*.{ext}"))
        if files:
            img_path = files[0]
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            encoded = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"

    return ""


def build_bio_block(sections):
    bio = get_section(sections, "bio")
    bio_text = md_to_html(get_section_text(bio))
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
    sec = get_section(sections, sec_id)
    title = get_section_title(sec, fallback_title)
    body = md_to_html(get_section_text(sec))
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
    print(f"Generated {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
