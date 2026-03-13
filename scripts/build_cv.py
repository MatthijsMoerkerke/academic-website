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


def read_front_matter(path: Path):

    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)

    if len(parts) < 3:
        return {}

    return yaml.safe_load(parts[1]) or {}


def read_yaml(path: Path):

    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    if isinstance(data, dict):
        return data

    return {}


def md_to_html(text):

    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"]
    )


def remove_cv_button(text):

    if not text:
        return ""

    text = re.sub(
        r'(?is)<a[^>]*CV_Matthijs_Moerkerke\.pdf[^>]*>.*?</a>',
        "",
        text
    )

    text = re.sub(
        r'(?im)^.*Download CV.*$',
        "",
        text
    )

    return text.strip()


def get_home_sections():

    fm = read_front_matter(SITE_INDEX)

    sections = fm.get("sections")

    if not isinstance(sections, list):
        sections = []

    result = {}

    for sec in sections:

        if not isinstance(sec, dict):
            continue

        sec_id = sec.get("id")

        content = sec.get("content", {})

        if not sec_id:
            continue

        text = content.get("text", "")

        if sec_id == "bio":
            text = remove_cv_button(text)

        result[sec_id] = {
            "title": content.get("title", ""),
            "text": text
        }

    return result


def get_avatar():

    for name in ["avatar.jpg", "avatar.jpeg", "avatar.png"]:

        p = AUTHOR_DIR / name

        if p.exists():

            encoded = base64.b64encode(p.read_bytes()).decode("ascii")

            mime = "image/jpeg" if name.endswith("jpg") else "image/png"

            return f"data:{mime};base64,{encoded}"

    return ""


def build_bio(sections, author):

    bio_html = md_to_html(sections.get("bio", {}).get("text", ""))

    avatar = get_avatar()

    name = author.get("name", {}).get("display", "Matthijs Moerkerke")

    role = author.get("role", "")

    affiliations = "<br>".join(
        a["name"] for a in author.get("affiliations", [])
    )

    email = "matthijs.moerkerke@ugent.be"
    linkedin = ""
    orcid = ""

    for l in author.get("links", []):

        url = l.get("url", "")

        if url.startswith("mailto:"):
            email = url.replace("mailto:", "")

        if "linkedin" in url:
            linkedin = url

        if "orcid" in url:
            orcid = url

    return f"""
<div class="hero">

<div class="hero-left">

<div class="hero-top">

<img class="hero-avatar" src="{avatar}">

<div class="hero-title">

<h1>{name}</h1>
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


def build_education(author):

    cards = []

    for e in author.get("education", []):

        degree = e.get("degree", "")
        inst = e.get("institution", "")
        summary = md_to_html(e.get("summary", ""))

        cards.append(f"""
<div class="info-card">
<div class="card-title">{degree}</div>
<div class="card-inst">{inst}</div>
<div>{summary}</div>
</div>
""")

    return f"""
<section class="cv-section">
<h2>Education</h2>
<div class="card-grid">
{''.join(cards)}
</div>
</section>
"""


def build_interests(author):

    pills = ""

    for i in author.get("interests", []):

        pills += f'<span class="interest-pill">{i}</span>'

    return f"""
<section class="cv-section">
<h2>Research Interests</h2>
<div class="interest-row">{pills}</div>
</section>
"""


def build_languages(author):

    cards = ""

    for l in author.get("languages", []):

        cards += f"""
<div class="info-card compact">
<div class="card-title">{l.get('name')}</div>
<div>{l.get('label')}</div>
</div>
"""

    return f"""
<section class="cv-section">
<h2>Languages</h2>
<div class="card-grid">
{cards}
</div>
</section>
"""


def collect_publications():

    pubs = []

    for folder in PUBLICATIONS_DIR.iterdir():

        index = folder / "index.md"

        if index.exists():

            fm = read_front_matter(index)

            pubs.append(fm)

    pubs.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    return pubs


def build_publications():

    pubs = collect_publications()

    metrics = read_yaml(SCHOLAR_FILE)

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
<div class="metric-value">{metrics.get('citations',0)}</div>
</div>

<div class="metric-box">
<div class="metric-label">h-index</div>
<div class="metric-value">{metrics.get('h_index',0)}</div>
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

    template = TEMPLATE_FILE.read_text()

    style = STYLE_FILE.read_text()

    replacements = {

        "{{STYLE}}": style,
        "{{BIO}}": build_bio(sections, author),
        "{{EDUCATION}}": build_education(author),
        "{{INTERESTS}}": build_interests(author),
        "{{TRAINING}}": build_markdown_section(sections,"training","Additional Training"),
        "{{TEACHING}}": build_markdown_section(sections,"teaching","Teaching & Mentoring"),
        "{{ENGAGEMENT}}": build_markdown_section(sections,"engagement","Scientific Engagement & Outreach"),
        "{{SKILLS}}": build_markdown_section(sections,"skills","Skills & Methods"),
        "{{LANGUAGES}}": build_languages(author),
        "{{AWARDS}}": build_markdown_section(sections,"awards","Awards & Grants"),
        "{{PRESENTATIONS}}": build_markdown_section(sections,"presentations","Presentations"),
        "{{PUBLICATIONS}}": build_publications()
    }

    out = template

    for k,v in replacements.items():

        out = out.replace(k,v)

    OUTPUT_HTML.write_text(out)

    print("CV generated.")


if __name__ == "__main__":
    main()
