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


def format_stats(repo: dict) -> str:
    """Render star and fork counters for one repository."""
    stats: list[str] = []
    if repo["stargazers_count"] > 0:
        stats.append(f"⭐ {repo['stargazers_count']}")
    if repo["forks_count"] > 0:
        stats.append(f"🍴 {repo['forks_count']}")
    return " ".join(stats)


def format_project_line(repo: dict) -> str:
    """Render one project entry for the README list."""
    name = repo["full_name"]
    url = repo["html_url"]
    description = repo.get("description") or "No description"
    stats = format_stats(repo)
    return f"- **[{name}]({url})** — {description} · {stats}"


def build_projects_section(repos: list[dict]) -> str:
    """Build the Projects section for README.md."""
    lines = [PROJECTS_START, ""]
    if repos:
        lines.extend(format_project_line(repo) for repo in repos)
    else:
        lines.append("_No projects with stars or forks yet._")
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
