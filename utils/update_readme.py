import json
import os
import urllib.request


USERNAME = "pymlex"
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


def fetch_repo(full_name: str, token: str) -> dict:
    """Fetch a single repository with fork metadata."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}",
        headers=github_headers(token),
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def format_repo_line(repo: dict, fork_label: str | None = None) -> str:
    """Render one repository as a Markdown list item."""
    name = repo["full_name"]
    url = repo["html_url"]
    description = repo.get("description") or "No description"
    stars = repo["stargazers_count"]
    suffix = f" · {fork_label}" if fork_label else ""
    return f"- **[{name}]({url})** — {description}{suffix} · ⭐ {stars}"


def build_starred_section(repos: list[dict]) -> str:
    """Build the starred repositories Markdown block."""
    lines = [STARRED_START, "", "### Starred", ""]
    if repos:
        lines.extend(format_repo_line(repo) for repo in repos)
    else:
        lines.append("_No starred repositories yet._")
    lines.extend(["", STARRED_END])
    return "\n".join(lines)


def build_forked_section(repos: list[dict]) -> str:
    """Build the forked repositories Markdown block."""
    lines = [FORKED_START, "", "### Forked", ""]
    if repos:
        for repo in repos:
            parent = repo.get("parent") or {}
            parent_name = parent.get("full_name")
            fork_label = f"fork of [{parent_name}]({parent['html_url']})" if parent_name else None
            lines.append(format_repo_line(repo, fork_label))
    else:
        lines.append("_No forked repositories yet._")
    lines.extend(["", FORKED_END])
    return "\n".join(lines)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    """Replace a marked README section with new content."""
    prefix = text.split(start, 1)[0]
    suffix = text.split(end, 1)[1]
    return prefix + replacement + suffix


def update_readme(token: str, readme_path: str = README_PATH) -> bool:
    """Refresh starred and forked repository sections in README.md."""
    starred = paginate(
        f"https://api.github.com/users/{USERNAME}/starred?per_page=100&sort=updated",
        token,
    )
    all_repos = paginate(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated",
        token,
    )
    forked = [
        fetch_repo(repo["full_name"], token)
        for repo in all_repos
        if repo.get("fork")
    ]

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
