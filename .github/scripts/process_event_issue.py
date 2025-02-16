import os
import yaml
from pathlib import Path
import json
from datetime import datetime
from github import Github
import re

def parse_issue_body(body: str) -> dict:
    """Parse the issue body form data into a dictionary"""
    data = {}
    lines = body.split('\n')
    current_field = None
    current_value = []
    
    for line in lines:
        if line.startswith('### '):
            if current_field and current_value:
                data[current_field] = '\n'.join(current_value).strip()
                current_value = []
            current_field = line.replace('### ', '').strip().lower().replace(' ', '_')
        elif line.strip() and current_field:
            current_value.append(line.strip())
    
    if current_field and current_value:
        data[current_field] = '\n'.join(current_value).strip()
    
    return data

def validate_event_data(data: dict) -> tuple[bool, str]:
    """Validate the event data"""
    required_fields = ['event_title', 'event_date', 'event_url', 'community', 'location', 'description']
    
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

def format_event_yaml(community: str, event_data: dict) -> str:
    """Format the event data as YAML"""
    event = {
        'title': event_data['event_title'],
        'date': datetime.strptime(event_data['event_date'], '%Y-%m-%d %H:%M').isoformat(),
        'url': event_data['event_url'],
        'description': event_data['description'],
        'community': community,
        'location': event_data['location'],
        'is_online': event_data.get('is_this_an_online_event', 'No') == 'Yes'
    }
    
    return yaml.dump([event], allow_unicode=True, sort_keys=False)

def create_or_update_branch(repo, base_branch: str, community: str, event_data: dict) -> tuple[str, str]:
    """Create a new branch and update the events file"""
    # Generate branch name from event details
    safe_title = re.sub(r'[^a-zA-Z0-9]', '-', event_data['event_title'].lower())
    branch_name = f"add-event/{safe_title}"
    
    # Get the latest commit from base branch
    base_ref = repo.get_git_ref(f"heads/{base_branch}")
    base_sha = base_ref.object.sha
    
    try:
        # Try to create new branch
        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    except Exception:
        # Branch might already exist - get its latest commit
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        base_sha = branch_ref.object.sha
    
    # Get current file content if exists
    file_path = f"{community}/events.yml"
    current_content = []
    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        if contents.content:
            current_content = yaml.safe_load(contents.decoded_content.decode('utf-8')) or []
    except Exception:
        # File doesn't exist yet
        pass
    
    # Add new event
    new_event = {
        'title': event_data['event_title'],
        'date': datetime.strptime(event_data['event_date'], '%Y-%m-%d %H:%M').isoformat(),
        'url': event_data['event_url'],
        'description': event_data['description'],
        'community': community,
        'location': event_data['location'],
        'is_online': event_data.get('is_this_an_online_event', 'No') == 'Yes'
    }
    
    # Check if event already exists
    if not any(event['url'] == new_event['url'] for event in current_content):
        current_content.append(new_event)
        current_content.sort(key=lambda x: x['date'], reverse=True)
        
        # Create or update file
        file_content = yaml.dump(current_content, allow_unicode=True, sort_keys=False)
        commit_message = f"Add event: {event_data['event_title']}"
        
        if contents:
            repo.update_file(
                file_path,
                commit_message,
                file_content,
                contents.sha,
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
    
    return branch_name, "Event already exists"

def main():
    # Get issue data from environment
    issue_body = json.loads(os.environ['ISSUE_BODY'])
    issue_number = os.environ['ISSUE_NUMBER']
    
    # Parse issue body
    event_data = parse_issue_body(issue_body)
    
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
