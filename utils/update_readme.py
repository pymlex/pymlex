import json
import urllib.request


USERNAME = "pymlex"
PROFILE_REPO = "pymlex/pymlex"
README_PATH = "README.md"
STARRED_START = "<!-- STARRED:START -->"
STARRED_END = "<!-- STARRED:END -->"
FORKED_START = "<!-- FORKED:START -->"
FORKED_END = "<!-- FORKED:END -->"


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def paginate(url: str, token: str) -> list[dict]:
    """Fetch all pages from a GitHub REST API collection endpoint."""
    items: list[dict] = []
    next_url: str | None = url
    while next_url:
        request = urllib.request.Request(next_url, headers=github_headers(token))
        with urllib.request.urlopen(request) as response:
            page_items = json.loads(response.read().decode())
            items.extend(page_items)
            link_header = response.headers.get("Link", "")
            next_url = None
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
    return items


def owned_repos(token: str) -> list[dict]:
    """Return public repositories owned by the profile user."""
    repos = paginate(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated",
        token,
    )
    return [repo for repo in repos if repo["full_name"] != PROFILE_REPO]


def format_starred_line(repo: dict) -> str:
    """Render a repository starred by the community."""
    name = repo["full_name"]
    url = repo["html_url"]
    description = repo.get("description") or "No description"
    stars = repo["stargazers_count"]
    return f"- **[{name}]({url})** — {description} · ⭐ {stars}"


def format_forked_line(repo: dict) -> str:
    """Render a repository forked by the community."""
    name = repo["full_name"]
    url = repo["html_url"]
    description = repo.get("description") or "No description"
    forks = repo["forks_count"]
    return f"- **[{name}]({url})** — {description} · 🍴 {forks}"


def build_starred_section(repos: list[dict]) -> str:
    """Build repositories starred by other users."""
    lines = [STARRED_START, "", "### Starred by users", ""]
    if repos:
        lines.extend(format_starred_line(repo) for repo in repos)
    else:
        lines.append("_No stars on your repositories yet._")
    lines.extend(["", STARRED_END])
    return "\n".join(lines)


def build_forked_section(repos: list[dict]) -> str:
    """Build repositories forked by other users."""
    lines = [FORKED_START, "", "### Forked by users", ""]
    if repos:
        lines.extend(format_forked_line(repo) for repo in repos)
    else:
        lines.append("_No forks of your repositories yet._")
    lines.extend(["", FORKED_END])
    return "\n".join(lines)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    """Replace a marked README section with new content."""
    prefix = text.split(start, 1)[0]
    suffix = text.split(end, 1)[1]
    return prefix + replacement + suffix


def update_readme(token: str, readme_path: str = README_PATH) -> bool:
    """Refresh community engagement sections in README.md."""
    repos = owned_repos(token)
    starred = sorted(
        [repo for repo in repos if repo["stargazers_count"] > 0],
        key=lambda repo: repo["stargazers_count"],
        reverse=True,
    )
    forked = sorted(
        [repo for repo in repos if repo["forks_count"] > 0],
        key=lambda repo: repo["forks_count"],
        reverse=True,
    )

    with open(readme_path, encoding="utf-8") as file:
        readme = file.read()

    updated = replace_section(
        readme,
        STARRED_START,
        STARRED_END,
        build_starred_section(starred),
    )
    updated = replace_section(
        updated,
        FORKED_START,
        FORKED_END,
        build_forked_section(forked),
    )

    if updated == readme:
        return False

    with open(readme_path, "w", encoding="utf-8", newline="\n") as file:
        file.write(updated)
    return True
