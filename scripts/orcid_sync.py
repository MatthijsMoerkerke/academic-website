import requests
import os
import yaml

ORCID = "0000-0002-7133-8418"

url = f"https://pub.orcid.org/v3.0/{ORCID}/works"

headers = {
    "Accept": "application/json"
}

data = requests.get(url, headers=headers).json()

works = data["group"]

for w in works:
    title = w["work-summary"][0]["title"]["title"]["value"]

    slug = title.lower().replace(" ", "-").replace(":", "")
    folder = f"content/publications/{slug}"

    if not os.path.exists(folder):
        os.makedirs(folder)

        frontmatter = {
            "title": title,
            "authors": ["Matthijs Moerkerke"],
            "date": "2024-01-01",
            "publication_types": ["article-journal"],
            "featured": False
        }

        with open(f"{folder}/index.md", "w") as f:
            f.write("---\n")
            yaml.dump(frontmatter, f)
            f.write("---\n")
