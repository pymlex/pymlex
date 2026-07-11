import json
import urllib.request


USERNAME = "pymlex"
PROFILE_REPO = "pymlex/pymlex"
README_PATH = "README.md"
PROJECTS_START = "<!-- PROJECTS:START -->"
PROJECTS_END = "<!-- PROJECTS:END -->"


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
    """Return all public repositories for the profile user."""
    repos = paginate(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100",
        token,
    )
    return [repo for repo in repos if repo["full_name"] != PROFILE_REPO]


def engaged_repos(repos: list[dict]) -> list[dict]:
    """Return repositories with at least one star or fork."""
    return [
        repo for repo in repos
        if repo["stargazers_count"] > 0 or repo["forks_count"] > 0
    ]


def repo_short_name(full_name: str) -> str:
    """Return repository name without the owner prefix."""
    return full_name.split("/", 1)[1]


def escape_table_cell(text: str) -> str:
    """Escape characters that break Markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ")


def format_count_cell(count: int, emoji: str) -> str:
    """Render a table cell with emoji repeated by count."""
    if count == 0:
        return ""
    return emoji * count


def format_project_row(repo: dict) -> str:
    """Render one project row for the README table."""
    short_name = repo_short_name(repo["full_name"])
    url = repo["html_url"]
    description = escape_table_cell(repo.get("description") or "No description")
    stars = format_count_cell(repo["stargazers_count"], "⭐")
    forks = format_count_cell(repo["forks_count"], "🍴")
    return f"| [{short_name}]({url}) | {description} | {stars} | {forks} |"


def build_projects_section(repos: list[dict]) -> str:
    """Build the Projects section for README.md."""
    lines = [
        PROJECTS_START,
        "",
        "| Project | Description | Stars | Forks |",
        "| --- | --- | ---: | ---: |",
    ]
    if repos:
        lines.extend(format_project_row(repo) for repo in repos)
    else:
        lines.append("| _No projects with stars or forks yet._ | | | |")
    lines.extend(["", PROJECTS_END])
    return "\n".join(lines)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    """Replace a marked README section with new content."""
    prefix = text.split(start, 1)[0]
    suffix = text.split(end, 1)[1]
    return prefix + replacement + suffix


def update_readme(token: str, readme_path: str = README_PATH) -> bool:
    """Refresh the Projects section in README.md."""
    repos = owned_repos(token)
    projects = sorted(
        engaged_repos(repos),
        key=lambda repo: (repo["stargazers_count"], repo["forks_count"]),
        reverse=True,
    )

    with open(readme_path, encoding="utf-8") as file:
        readme = file.read()

    updated = replace_section(
        readme,
        PROJECTS_START,
        PROJECTS_END,
        build_projects_section(projects),
    )

    if updated == readme:
        return False

    with open(readme_path, "w", encoding="utf-8", newline="\n") as file:
        file.write(updated)
    return True
