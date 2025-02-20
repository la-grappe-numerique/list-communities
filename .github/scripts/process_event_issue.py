import os
import json
from pathlib import Path
from datetime import datetime
from github import Github
import re

import os,sys
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(current_dir))
from utils.event_matcher import EventMatcher
from utils.issue_parser import IssueParser

def validate_event_data(data: dict) -> tuple[bool, str]:
    """Validate the event data"""
    required_fields = ['event_title', 'event_date', 'event_url', 'community', 'location']

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate date format
    try:
        datetime.strptime(data['event_date'], '%Y-%m-%d %H:%M')
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD HH:MM"

    # Validate URL
    if not data['event_url'].startswith('http'):
        return False, "Invalid URL format"

    return True, ""

def format_event_json(community: str, event_data: dict) -> dict:
    """Format event data as a JSON object"""
    event = {
        'title': event_data['event_title'],
        'date': datetime.strptime(event_data['event_date'], '%Y-%m-%d %H:%M').isoformat(),
        'url': event_data['event_url'],
        'description': event_data.get('description', ''),
        'community': community,
        'location': event_data['location'],
        'is_online': event_data.get('is_this_an_online_event', 'No') == 'Yes'
    }
    return event

def create_or_update_branch(repo, base_branch: str, community: str, event_data: dict) -> tuple[str, str]:
    """Create a new branch and update the events file"""
    safe_title = re.sub(r'[^a-zA-Z0-9]', '-', event_data['event_title'].lower())
    branch_name = f"add-event/{safe_title}"
    
    try:
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha
        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    except Exception:
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        base_sha = branch_ref.object.sha
    
    file_path = f"{community}/events.json"
    file_sha = None
    current_content = []
    
    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        if contents.content:
            current_content = json.loads(contents.decoded_content.decode('utf-8'))
            file_sha = contents.sha
    except Exception:
        pass
    
    new_event = format_event_json(community, event_data)
    
    # Use EventMatcher to check for existing events
    matcher = EventMatcher()
    matching_event = matcher.find_matching_event(new_event, current_content)
    
    if matching_event:
        # If we found a match, we might want to update its communities
        return branch_name, "Event already exists"
    
    # No match found, add as new event
    current_content.append(new_event)
    current_content.sort(key=lambda x: x['date'], reverse=True)
    
    file_content = json.dumps(current_content, indent=2, ensure_ascii=False)
    commit_message = f"Add event: {event_data['event_title']}"
    
    if file_sha:
        repo.update_file(
            file_path,
            commit_message,
            file_content,
            file_sha,
            branch=branch_name
        )
    else:
        repo.create_file(
            file_path,
            commit_message,
            file_content,
            branch=branch_name
        )
    
    return branch_name, "Event added successfully"

def main():
    # Get issue data from environment
    issue_body = json.loads(os.environ['ISSUE_BODY'])
    issue_number = os.environ['ISSUE_NUMBER']
    
    # Parse issue body
    event_data = IssueParser.parse_issue_body(issue_body, issue_type='event')
    
    # Initialize GitHub client
    gh = Github(os.environ['GITHUB_TOKEN'])
    repo = gh.get_repo(os.environ['GITHUB_REPOSITORY'])
    issue = repo.get_issue(number=int(issue_number))
    
    # Validate event data
    is_valid, error_message = validate_event_data(event_data)
    if not is_valid:
        issue.create_comment(f"❌ Error processing event: {error_message}")
        issue.add_to_labels('invalid')
        return
    
    try:
        # Create branch and update file
        branch_name, message = create_or_update_branch(
            repo,
            'main',
            event_data['community'],
            event_data
        )
        
        if message == "Event added successfully":
            # Create pull request
            pr = repo.create_pull(
                title=f"Add event: {event_data['event_title']}",
                body=(
                    f"Adds new event from issue #{issue_number}\n\n"
                    f"Event details:\n"
                    f"- Title: {event_data['event_title']}\n"
                    f"- Date: {event_data['event_date']}\n"
                    f"- Location: {event_data['location']}\n"
                    f"- Community: {event_data['community']}"
                ),
                head=branch_name,
                base='main'
            )
            
            # Add labels and link issue
            pr.add_to_labels('event')
            issue.create_comment(f"✅ Pull Request created: {pr.html_url}")
            issue.add_to_labels('processed')
            
        else:
            issue.create_comment(f"ℹ️ {message}")
            issue.add_to_labels('duplicate')
            
    except Exception as e:
        issue.create_comment(f"❌ Error processing event: {str(e)}")
        issue.add_to_labels('error')

if __name__ == "__main__":
    main()