# sync_contributors.py
"""
Synchronize GitHub contributors with .all-contributorsrc file
and update the contributors section in README.md
"""
import os
import json
from pathlib import Path
from github import Github


def get_github_contributors(repo) -> list:
    """Fetch all contributors from the GitHub repository"""
    contributors = []
    for contributor in repo.get_contributors():
        contributors.append({
            "login": contributor.login,
            "name": contributor.name or contributor.login,
            "avatar_url": contributor.avatar_url,
            "profile": contributor.html_url,
            "contributions": ["code"]
        })
    return contributors


def load_all_contributors_config(config_path: Path) -> dict:
    """Load existing .all-contributorsrc file"""
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "projectName": "list-communities",
        "projectOwner": "la-grappe-numerique",
        "files": ["README.md"],
        "commitType": "docs",
        "commitConvention": "angular",
        "contributorsPerLine": 7,
        "contributors": []
    }


def merge_contributors(existing: list, github_contributors: list) -> list:
    """Merge existing contributors with GitHub contributors"""
    # Create a dict of existing contributors by login
    existing_by_login = {c["login"]: c for c in existing}

    # Add new contributors from GitHub
    for gh_contrib in github_contributors:
        login = gh_contrib["login"]
        if login not in existing_by_login:
            # New contributor - add them
            existing_by_login[login] = gh_contrib
        else:
            # Existing contributor - update avatar_url and name if changed
            existing_by_login[login]["avatar_url"] = gh_contrib["avatar_url"]
            if gh_contrib["name"] and gh_contrib["name"] != gh_contrib["login"]:
                existing_by_login[login]["name"] = gh_contrib["name"]
            # Add "code" to contributions if not present
            if "code" not in existing_by_login[login]["contributions"]:
                existing_by_login[login]["contributions"].append("code")

    return list(existing_by_login.values())


def generate_contributors_table(contributors: list, per_line: int = 7) -> str:
    """Generate the HTML table for contributors"""
    if not contributors:
        return ""

    # Contribution type to emoji mapping
    contribution_emojis = {
        "code": "\U0001F4BB",
        "doc": "\U0001F4D6",
        "design": "\U0001F3A8",
        "ideas": "\U0001F914",
        "bug": "\U0001F41B",
        "test": "\u26A0\uFE0F",
        "review": "\U0001F440",
        "maintenance": "\U0001F6E0\uFE0F",
        "infra": "\U0001F687",
        "example": "\U0001F4A1",
        "translation": "\U0001F30D",
        "content": "\U0001F58A\uFE0F",
        "tutorial": "\u270D\uFE0F",
        "question": "\U0001F4AC",
        "talk": "\U0001F4E2",
        "video": "\U0001F4F9",
        "financial": "\U0001F4B5",
        "fundingFinding": "\U0001F50D",
        "eventOrganizing": "\U0001F4C5",
        "projectManagement": "\U0001F4C6",
        "mentoring": "\U0001F9D1\u200D\U0001F3EB",
        "plugin": "\U0001F50C",
        "tool": "\U0001F527",
        "platform": "\U0001F4E6",
        "promotion": "\U0001F4E3",
        "security": "\U0001F6E1\uFE0F",
        "userTesting": "\U0001F4D3",
        "a11y": "\u267F\uFE0F",
        "data": "\U0001F50E",
        "audio": "\U0001F50A",
        "research": "\U0001F52C",
    }

    lines = ['<table>', '  <tbody>']

    for i, contributor in enumerate(contributors):
        if i % per_line == 0:
            if i > 0:
                lines.append('    </tr>')
            lines.append('    <tr>')

        login = contributor["login"]
        name = contributor.get("name", login)
        avatar_url = contributor["avatar_url"]
        profile = contributor.get("profile", f"https://github.com/{login}")
        contributions = contributor.get("contributions", ["code"])

        # Build contribution links
        contrib_links = []
        for contrib_type in contributions:
            emoji = contribution_emojis.get(contrib_type, "\u2728")
            title = contrib_type.capitalize()
            contrib_links.append(f'<a href="#{contrib_type}-{login}" title="{title}">{emoji}</a>')

        contrib_html = " ".join(contrib_links)

        cell = f'''      <td align="center" valign="top" width="14.28%"><a href="{profile}"><img src="{avatar_url}?s=100" width="100px;" alt="{name}"/><br /><sub><b>{name}</b></sub></a><br />{contrib_html}</td>'''
        lines.append(cell)

    # Close the last row
    lines.append('    </tr>')
    lines.append('  </tbody>')
    lines.append('</table>')

    return '\n'.join(lines)


def update_readme(readme_path: Path, contributors_table: str) -> bool:
    """Update the contributors section in README.md"""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find and replace the contributors section
    start_marker = "<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->"
    end_marker = "<!-- ALL-CONTRIBUTORS-LIST:END -->"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("Contributors section markers not found in README.md")
        return False

    new_section = f"""{start_marker}
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
{contributors_table}

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

{end_marker}"""

    new_content = content[:start_idx] + new_section + content[end_idx + len(end_marker):]

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    # Initialize GitHub client
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return 1

    g = Github(github_token)

    # Get repository
    repo_name = os.environ.get('GITHUB_REPOSITORY', 'la-grappe-numerique/list-communities')
    repo = g.get_repo(repo_name)

    # Paths
    root_dir = Path(__file__).parent.parent.parent
    config_path = root_dir / '.all-contributorsrc'
    readme_path = root_dir / 'README.md'

    print(f"Syncing contributors for {repo_name}...")

    # Get GitHub contributors
    github_contributors = get_github_contributors(repo)
    print(f"Found {len(github_contributors)} contributors on GitHub")

    # Load existing config
    config = load_all_contributors_config(config_path)
    existing_contributors = config.get("contributors", [])
    print(f"Found {len(existing_contributors)} contributors in .all-contributorsrc")

    # Merge contributors
    merged_contributors = merge_contributors(existing_contributors, github_contributors)
    print(f"Total contributors after merge: {len(merged_contributors)}")

    # Update config
    config["contributors"] = merged_contributors

    # Save updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f"Updated {config_path}")

    # Generate and update README
    per_line = config.get("contributorsPerLine", 7)
    contributors_table = generate_contributors_table(merged_contributors, per_line)

    if update_readme(readme_path, contributors_table):
        print(f"Updated {readme_path}")

    return 0


if __name__ == "__main__":
    exit(main())
