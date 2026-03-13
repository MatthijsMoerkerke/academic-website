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
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise RuntimeError(f"{path} does not start with YAML front matter")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError(f"Could not parse front matter in {path}")

    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Front matter in {path} is not a dictionary")

    return data


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

    # bare URLs clickable
    text = re.sub(r"(?m)^(https?://\S+)\s*$", r"<\1>", text)

    return text


def strip_cv_button_from_bio(text: str) -> str:
    if not text:
        return ""

    # remove full button paragraph
    text = re.sub(
        r'(?is)<p[^>]*>\s*<a[^>]*href="[^"]*CV_Matthijs_Moerkerke\.pdf[^"]*"[^>]*>.*?</a>\s*</p>',
        "",
        text,
    )

    # remove standalone anchor
    text = re.sub(
        r'(?is)<a[^>]*href="[^"]*CV_Matthijs_Moerkerke\.pdf[^"]*"[^>]*>.*?</a>',
        "",
        text,
    )

    # remove plain Download CV line if it survived
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


def get_home_sections() -> dict:
    fm = read_front_matter(SITE_INDEX)

    sections = fm.get("sections")
    if not isinstance(sections, list):
        raise RuntimeError(f"'sections' in {SITE_INDEX} is not a list")

    result = {}

    for sec in sections:
        if not isinstance(sec, dict):
            continue

        sec_id = sec.get("id")
        content = sec.get("content", {}) or {}

        if not sec_id:
            continue

        text = content.get("text", "") or ""
        title = content.get("title", "") or ""

        if sec_id == "bio":
            text = strip_cv_button_from_bio(text)

        result[sec_id] = {
            "title": title,
            "text": text,
        }

    return result


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


def format_authors(authors):
    if not authors:
        return "Unknown authors"
    return ", ".join(authors)


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


def format_publication_html(front_matter: dict) -> str:
    authors_text = format_authors(front_matter.get("authors", []))
    date = str(front_matter.get("date", ""))
    year = date[:4] if len(date) >= 4 else "n.d."
    title = front_matter.get("title", "Untitled")
    publication = front_matter.get("publication", "")
    doi = front_matter.get("doi", "")

    parts = [f"{authors_text} ({year}). <em>{title}</em>."]
    if publication:
        parts.append(f"{publication}.")
    if doi:
        parts.append(f'<a href="https://doi.org/{doi}">https://doi.org/{doi}</a>')

    return "<li>" + " ".join(parts) + "</li>"


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


def build_bio(sections: dict, author: dict) -> str:
    bio_text = sections.get("bio", {}).get("text", "")
    bio_html = md_to_html(bio_text)

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

    <div class="hero-bio">
      {bio_html}
    </div>
  </div>

  <div class="hero-right">
    <strong>Email</strong><br>{email}<br><br>
    <strong>LinkedIn</strong><br>{linkedin}<br><br>
    <strong>ORCID</strong><br>{orcid}
  </div>
</div>
"""


def build_markdown_section(sections: dict, key: str, fallback_title: str) -> str:
    sec = sections.get(key, {})
    title = sec.get("title", "") or fallback_title
    html = md_to_html(sec.get("text", ""))

    if not html:
        return ""

    return f"""
<section class="cv-section">
  <h2>{title}</h2>
  {html}
</section>
"""


def build_card_section(title: str, cards: list[str]) -> str:
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


def build_education(author: dict) -> str:
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


def build_interests(author: dict) -> str:
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


def build_publications() -> str:
    pubs = collect_publications()
    metrics = read_scholar_metrics()

    items = ""
    for p in pubs:
        items += format_publication_html(p)

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
