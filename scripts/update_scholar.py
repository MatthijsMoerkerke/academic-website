from scholarly import scholarly
import yaml

SCHOLAR_ID = "Dv9Rx2MAAAAJ"

author = scholarly.search_author_id(SCHOLAR_ID)
author = scholarly.fill(author)

data = {
    "citations": author.get("citedby", 0),
    "h_index": author.get("hindex", 0),
    "profile": f"https://scholar.google.com/citations?user={SCHOLAR_ID}",
}

with open("data/scholar.yaml", "w", encoding="utf-8") as f:
    yaml.dump(data, f, sort_keys=False, allow_unicode=True)

print("Scholar metrics updated")
