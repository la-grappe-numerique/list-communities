# process_community_issue.py
import os,sys
import json
from pathlib import Path
from typing import Dict, List
from github import Github
import re

current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(current_dir))
from utils.issue_parser import IssueParser

def create_community_folder(repo, base_branch: str, community_data: Dict) -> tuple[str, str]:
    """Create a new branch and initialize community structure"""
    try:
        community_name = community_data['community_name'].strip()
        # Sanitize community name
        if not re.match(r'^[a-z0-9-]+$', community_name):
            return "", "Invalid community name format. Use only lowercase letters, numbers, and hyphens."

        # Create branch name
        branch_name = f"init-community/{community_name}"
        
        # Get base branch ref
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha
        
        try:
            repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        except Exception as e:
            print(f"Branch might already exist: {str(e)}")
            branch_ref = repo.get_git_ref(f"heads/{branch_name}")
            base_sha = branch_ref.object.sha

        # Generate files content
        files_to_create = {
            f"{community_name}/README.md": generate_readme(community_data),
            f"{community_name}/events.json": "[]",
        }

        # Add events_src.json if using Meetup
        if community_data.get('meetup_url'):
            files_to_create[f"{community_name}/events_src.json"] = generate_events_src(community_data)

        # Create all files
        for file_path, content in files_to_create.items():
            try:
                repo.create_file(
                    file_path,
                    f"Initialize {community_name} community",
                    content,
                    branch=branch_name
                )
                print(f"Created {file_path}")
            except Exception as e:
                print(f"Error creating {file_path}: {e}")
                return branch_name, f"Error creating {file_path}"

        return branch_name, "Community initialized successfully"

    except Exception as e:
        print(f"Error in create_community_folder: {e}")
        return "", str(e)

def generate_readme(data: Dict) -> str:
    """Generate README.md content for the community"""
    social_links = []
    
    if data.get('website'):
        social_links.append(f"| 🌐 Site web | {data['website']} |")
    if data.get('meetup_url'):
        social_links.append(f"| 👥 Meetup | {data['meetup_url']} |")
    if data.get('linkedin_url'):
        social_links.append(f"| 💼 LinkedIn | {data['linkedin_url']} |")
    if data.get('x/twitter_url'):
        social_links.append(f"| 🐦 X/Twitter | {data['x/twitter_url']} |")
    if data.get('mastodon_url'):
        social_links.append(f"| 🐘 Mastodon | {data['mastodon_url']} |")
    if data.get('bluesky_url'):
        social_links.append(f"| ☁️ Bluesky | {data['bluesky_url']} |")

    # Get contacts from contact_persons field
    contact_text = data.get('contact_persons', '').strip()
    contact_lines = []
    if contact_text:
        # Split on actual newlines and handle potential carriage returns
        contact_lines = [
            f"| ✉️ {contact.strip()} |" 
            for contact in contact_text.split('\n') 
            if contact.strip()
        ]

    readme = f"# {data['display_name']}\n\n"
    
    # Add contact and social info table if any information exists
    if contact_lines or social_links:
        readme += "|                                |     |\n"
        readme += "| ------------------------------ | --- |\n"
        readme += "\n".join(contact_lines + social_links) + "\n\n"

    # Add description if provided
    if data.get('description'):
        readme += f"{data['description']}\n\n"

    # Add iCal info
    readme += (f"Le calendrier des évènements est disponible au format iCal.\n"
              f"Voici son URL : [https://www.lagrappenumerique.fr/{data['community_name']}/events.ics](./events.ics ':ignore')\n\n")

    # Add events placeholder
    readme += "<!-- EVENTS:START -->\n<!-- EVENTS:END -->\n"

    return readme

def generate_events_src(data: Dict) -> str:
    """Generate events_src.json content for Meetup configuration"""
    return json.dumps({
        "type": "meetup",
        "url": data['meetup_url'],
        "status": ["upcoming", "past"]  # Default to both statuses
    }, indent=2)

def main():
    """Main script execution"""
    try:
        issue_body = json.loads(os.environ['ISSUE_BODY'])
        issue_number = os.environ['ISSUE_NUMBER']
        
        print("\n=== Processing Issue Body ===")
        print(issue_body)
        
        # Parse issue body
        community_data = IssueParser.parse_issue_body(issue_body, issue_type='community')
        
        # Add debug output for contact persons
        print("\n=== Contact Persons Content ===")
        print(f"Raw contact_persons: {community_data.get('contact_persons', 'Not found')}")
        
        # Validate required fields
        required_fields = ['community_name', 'display_name', 'contact_persons']
        missing_fields = [field for field in required_fields if not community_data.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
        print("\n=== Parsed Community Data ===")
        print(json.dumps(community_data, indent=2))
        
        # Initialize GitHub client
        gh = Github(os.environ['GITHUB_TOKEN'])
        repo = gh.get_repo(os.environ['GITHUB_REPOSITORY'])
        issue = repo.get_issue(number=int(issue_number))
        
        # Create community folder and files
        branch_name, message = create_community_folder(repo, 'main', community_data)
        
        if branch_name:
            # Create pull request
            pr = repo.create_pull(
                title=f"Initialize community: {community_data['display_name']}",
                body=(
                    f"Initializes new community from issue #{issue_number}\n\n"
                    f"Community details:\n"
                    f"- Name: {community_data['display_name']}\n"
                    f"- Folder: {community_data['community_name']}\n"
                    f"- Event source: {community_data.get('event_source', 'Manual')}"
                ),
                head=branch_name,
                base='main'
            )
            
            # Add labels and link issue
            pr.add_to_labels('community')
            issue.create_comment(f"✅ Pull Request created: {pr.html_url}")
            issue.add_to_labels('processed')
        else:
            issue.create_comment(f"❌ Error initializing community: {message}")
            issue.add_to_labels('error')
            
    except Exception as e:
        print(f"Error in main: {e}")
        if 'issue' in locals():
            issue.create_comment(f"❌ Error processing community initialization: {str(e)}")
            issue.add_to_labels('error')

if __name__ == "__main__":
    main()