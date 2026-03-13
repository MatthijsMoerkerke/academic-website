from pathlib import Path
import base64
import re
import yaml
import markdown

ROOT = Path(__file__).resolve().parents[1]

SITE_INDEX = ROOT / "content" / "_index.md"
AUTHOR_DATA = ROOT / "data" / "authors" / "me.yaml"
AUTHOR_DIR = ROOT / "content" / "authors" / "matthijs"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.html"
STYLE_FILE = ROOT / "cv" / "style.css"
OUTPUT_HTML = ROOT / "cv" / "cv_generated.html"


def read_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1]) or {}
    return data if isinstance(data, dict) else {}


def read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


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
    text = re.sub(r"(?m)^(https?://\S+)\s*$", r"<\1>", text)
    return text


def strip_cv_button_from_bio(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r'(?is)<p[^>]*>\s*<a[^>]*href="[^"]*CV_Matthijs_Moerkerke\.pdf[^"]*"[^>]*>.*?</a>\s*</p>',
        "",
        text,
    )
    text = re.sub(
        r'(?is)<a[^>]*href="[^"]*CV_Matthijs_Moerkerke\.pdf[^"]*"[^>]*>.*?</a>',
        "",
        text,
    )
    text = re.sub(
        r'(?im)^\s*\[Download CV\]\([^)]+CV_Matthijs_Moerkerke\.pdf[^)]*\)\s*$',
        "",
        text,
    )
    text = re.sub(r"(?im)^\s*Download CV\s*$", "", text)

    return text.strip()


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
    lines = site_text.splitlines()

    block_start = None
    for i, line in enumerate(lines):
        if re.match(rf"^\s+id:\s*{re.escape(block_id)}\s*$", line):
            block_start = i
            break

    if block_start is None:
        return ""

    text_line_index = None
    text_indent = None

    for i in range(block_start, len(lines)):
        line = lines[i]
        m = re.match(r"^(\s+)text:\s*\|\s*$", line)
        if m:
            text_line_index = i
            text_indent = len(m.group(1))
            break
        if i > block_start and re.match(r"^\s*-\s*block:", line):
            break

    if text_line_index is None:
        return ""

    collected = []
    for i in range(text_line_index + 1, len(lines)):
        line = lines[i]

        if line.strip() == "":
            collected.append("")
            continue

        indent = len(line) - len(line.lstrip(" "))

        if indent <= text_indent:
            break

        collected.append(line)

    if not collected:
        return ""

    nonempty = [ln for ln in collected if ln.strip()]
    min_indent = min(len(ln) - len(ln.lstrip(" ")) for ln in nonempty) if nonempty else 0
    normalized = [
        ln[min_indent:] if len(ln) >= min_indent else ln.lstrip()
        for ln in collected
    ]

    return clean_markdown_block("\n".join(normalized).strip())


def get_home_sections() -> dict:
    site_text = SITE_INDEX.read_text(encoding="utf-8")

    bio_text = strip_cv_button_from_bio(extract_text_block(site_text, "bio"))

    return {
        "bio": {
            "title": "About",
            "text": bio_text,
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
            "title": extract_block_title(site_text, "presentations", "Presentations"),
            "text": extract_text_block(site_text, "presentations"),
        },
    }


def read_scholar_metrics() -> dict:
    data = read_yaml(SCHOLAR_FILE)
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


def find_avatar_data_uri() -> str:
    if not AUTHOR_DIR.exists():
        return ""

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


def build_bio(sections, author):
    bio_html = md_to_html(sections.get("bio", {}).get("text", ""))
    avatar = find_avatar_data_uri()

    display_name = author.get("name", {}).get("display", "Matthijs Moerkerke")
    role = author.get("role", "Neuroscientist")

    affiliations = "<br>".join(
        a.get("name", "")
        for a in author.get("affiliations", [])
        if isinstance(a, dict) and a.get("name")
    )

    email = "matthijs.moerkerke@ugent.be"
    linkedin = ""
    orcid = ""

    for link in author.get("links", []):
        if not isinstance(link, dict):
            continue
        url = link.get("url", "")
        if url.startswith("mailto:"):
            email = url.replace("mailto:", "")
        elif "linkedin" in url:
            linkedin = url
        elif "orcid" in url:
            orcid = url

    avatar_html = ""
    if avatar:
        avatar_html = f'<img class="hero-avatar" src="{avatar}" alt="{display_name}">'

    return f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-top">
      {avatar_html}
      <div class="hero-title">
        <h1>{display_name}</h1>
        <div class="hero-subtitle">{role}</div>
        <div class="hero-affiliation">{affiliations}</div>
      </div>
    </div>
    <div class="hero-bio">{bio_html}</div>
  </div>

  <div class="hero-right">
    <strong>Email</strong><br>{email}<br><br>
    <strong>LinkedIn</strong><br>{linkedin}<br><br>
    <strong>ORCID</strong><br>{orcid}
  </div>
</div>
"""


def build_markdown_section(sections, key, title):
    sec = sections.get(key, {})
    html = md_to_html(sec.get("text", ""))

    if not html:
        return ""

    return f"""
<section class="cv-section">
  <h2>{title}</h2>
  {html}
</section>
"""


def build_card_section(title, cards):
    if not cards:
        return ""

    return f"""
<section class="cv-section">
  <h2>{title}</h2>
  <div class="card-grid">
    {''.join(cards)}
  </div>
</section>
"""


def build_education(author):
    cards = []

    for item in author.get("education", []):
        if not isinstance(item, dict):
            continue

        degree = item.get("degree", "")
        institution = item.get("institution", "")
        summary = item.get("summary", "")
        button = item.get("button", {}) or {}
        url = button.get("url", "")

        link_html = ""
        if url:
            link_html = f'<div class="card-link"><a href="{url}">Dissertation link</a></div>'

        cards.append(f"""
<div class="info-card">
  <div class="card-title">{degree}</div>
  <div class="card-inst">{institution}</div>
  <div>{md_to_html(summary)}</div>
  {link_html}
</div>
""")

    return build_card_section("Education", cards)


def build_interests(author):
    interests = author.get("interests", [])
    if not interests:
        return ""

    pills = "".join(f'<span class="interest-pill">{item}</span>' for item in interests)

    return f"""
<section class="cv-section">
  <h2>Research Interests</h2>
  <div class="interest-row">
    {pills}
  </div>
</section>
"""


def build_publications():
    pubs = collect_publications()
    metrics = read_scholar_metrics()

    items = ""
    for p in pubs:
        authors = ", ".join(p.get("authors", []))
        year = str(p.get("date", ""))[:4]
        title = p.get("title", "")
        journal = p.get("publication", "")
        items += f"<li>{authors} ({year}). <em>{title}</em>. {journal}</li>"

    return f"""
<section class="cv-section">
  <h2>Publications</h2>

  <div class="metrics-row">
    <div class="metric-box">
      <div class="metric-label">Publications</div>
      <div class="metric-value">{len(pubs)}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">Citations</div>
      <div class="metric-value">{metrics.get('citations', 0)}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">h-index</div>
      <div class="metric-value">{metrics.get('h_index', 0)}</div>
    </div>
  </div>

  <ol class="pub-list">
    {items}
  </ol>
</section>
"""


def main():
    sections = get_home_sections()
    author = read_yaml(AUTHOR_DATA)
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    style = STYLE_FILE.read_text(encoding="utf-8")

    replacements = {
        "{{STYLE}}": style,
        "{{BIO}}": build_bio(sections, author),
        "{{EDUCATION}}": build_education(author),
        "{{INTERESTS}}": build_interests(author),
        "{{TRAINING}}": build_markdown_section(sections, "training", "Additional Training"),
        "{{TEACHING}}": build_markdown_section(sections, "teaching", "Teaching & Mentoring"),
        "{{ENGAGEMENT}}": build_markdown_section(sections, "engagement", "Scientific Engagement & Outreach"),
        "{{SKILLS}}": build_markdown_section(sections, "skills", "Skills & Methods"),
        "{{AWARDS}}": build_markdown_section(sections, "awards", "Awards & Grants"),
        "{{PRESENTATIONS}}": build_markdown_section(sections, "presentations", "Presentations"),
        "{{PUBLICATIONS}}": build_publications(),
    }

    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)

    OUTPUT_HTML.write_text(out, encoding="utf-8")
    print("CV generated.")


if __name__ == "__main__":
    main()
