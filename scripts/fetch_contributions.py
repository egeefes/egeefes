#!/usr/bin/env python3
"""
Fetch the last year of contributions + featured repos into data/contributions.json.
Runs in GitHub Actions with the built-in GITHUB_TOKEN (no extra secrets needed).

  GITHUB_TOKEN=... GH_USER=yourname python scripts/fetch_contributions.py
"""
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ["GH_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

REPO_FIELDS = "name description url stargazerCount isFork primaryLanguage { name color }"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
    pinnedItems(first: 4, types: REPOSITORY) { nodes { ... on Repository { %s } } }
    repositories(first: 20, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) { totalCount nodes { %s } }
  }
}""" % (REPO_FIELDS, REPO_FIELDS)


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        res = json.load(r)
    if "errors" in res:
        raise SystemExit(res["errors"])
    return res["data"]


def repo(n):
    lang = n.get("primaryLanguage") or {}
    return {"name": n["name"], "description": n.get("description"), "url": n["url"],
            "stars": n["stargazerCount"], "language": lang.get("name"), "language_color": lang.get("color")}


u = gql(QUERY, {"login": USER})["user"]
days = [{"date": d["date"], "count": d["contributionCount"]}
        for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
pinned = [repo(n) for n in u["pinnedItems"]["nodes"] if n]
recent = [repo(n) for n in u["repositories"]["nodes"] if n["name"].lower() != USER.lower()]
# Repos to show under "Now coding", in order (case doesn't matter).
# Leave the list empty to use your pinned repos, or else your most recently pushed ones.
FEATURED = ["WebDrop", "CampusLoop"]

if FEATURED:
    q = "query($o:String!,$n:String!){repository(owner:$o,name:$n){ %s }}" % REPO_FIELDS
    featured = []
    for name in FEATURED:
        try:
            r = gql(q, {"o": USER, "n": name})["repository"]
        except SystemExit as e:
            print(f"skipping {name}: {e}")
            continue
        if r:
            featured.append(repo(r))
else:
    featured = (pinned or recent)[:4]  # pinned repos win; otherwise most recently pushed

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps({"user": USER, "public_repos": u["repositories"]["totalCount"],
                           "repos": featured, "days": days}, indent=1))
print(f"{len(days)} days, {len(featured)} featured repos -> {OUT}")
