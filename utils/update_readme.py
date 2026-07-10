import json
import urllib.request


USERNAME = "pymlex"
PROFILE_REPO = "pymlex/pymlex"
README_PATH = "README.md"
LANGUAGES_START = "<!-- LANGUAGES:START -->"
LANGUAGES_END = "<!-- LANGUAGES:END -->"
STARRED_START = "<!-- STARRED:START -->"
STARRED_END = "<!-- STARRED:END -->"
FORKED_START = "<!-- FORKED:START -->"
FORKED_END = "<!-- FORKED:END -->"
TOP_LANGUAGE_COUNT = 8
MIN_LANGUAGE_PERCENT = 1.0


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_get(url: str, token: str) -> dict | list:
    """Fetch one GitHub REST API resource."""
    request = urllib.request.Request(url, headers=github_headers(token))
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


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


def repo_languages(full_name: str, token: str) -> dict[str, int]:
    """Return language byte counts for one repository."""
    languages = github_get(
        f"https://api.github.com/repos/{full_name}/languages",
        token,
    )
    return {language: int(bytes_count) for language, bytes_count in languages.items()}


def aggregate_languages(repos: list[dict], token: str) -> dict[str, float]:
    """Aggregate repository language bytes into percentage shares."""
    totals: dict[str, int] = {}
    for repo in repos:
        languages = repo_languages(repo["full_name"], token)
        for language, bytes_count in languages.items():
            totals[language] = totals.get(language, 0) + bytes_count

    total_bytes = sum(totals.values())
    if total_bytes == 0:
        return {}

    percentages = {
        language: 100.0 * bytes_count / total_bytes
        for language, bytes_count in totals.items()
    }
    ranked = sorted(percentages.items(), key=lambda item: item[1], reverse=True)
    major = [item for item in ranked if item[1] >= MIN_LANGUAGE_PERCENT]
    minor = [item for item in ranked if item[1] < MIN_LANGUAGE_PERCENT]

    if len(major) > TOP_LANGUAGE_COUNT:
        kept = major[:TOP_LANGUAGE_COUNT]
        other_share = sum(share for _, share in major[TOP_LANGUAGE_COUNT:])
        other_share += sum(share for _, share in minor)
    else:
        kept = major
        other_share = sum(share for _, share in minor)

    grouped = {language: share for language, share in kept}
    if other_share > 0:
        grouped["Other"] = other_share
    return grouped


def build_languages_section(language_shares: dict[str, float]) -> str:
    """Build a Mermaid pie chart for language distribution."""
    lines = [
        LANGUAGES_START,
        "",
        "```mermaid",
        "pie showData",
        "    title Language distribution across repositories (%)",
    ]
    if language_shares:
        for language, share in sorted(
            language_shares.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            label = language.replace('"', "'")
            lines.append(f'    "{label}" : {share:.1f}')
    else:
        lines.append('    "No code detected" : 100')
    lines.extend(["```", "", LANGUAGES_END])
    return "\n".join(lines)


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
    """Refresh language and community engagement sections in README.md."""
    repos = owned_repos(token)
    language_shares = aggregate_languages(repos, token)
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
        LANGUAGES_START,
        LANGUAGES_END,
        build_languages_section(language_shares),
    )
    updated = replace_section(
        updated,
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
