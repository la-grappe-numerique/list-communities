import os
import yaml
from pathlib import Path
import json
from datetime import datetime
from github import Github
import re

def parse_issue_body(body: str) -> dict:
    """Parse the issue body form data into a dictionary"""
    # The body will be in a format like:
    # ### Event Title
    # MyEvent
    # ### Event Date
    # 2025-02-20 18:30
    # ...
    
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

def update_community_events(community: str, event_data: dict):
    """Update the community events file"""
    events_file = Path(f'{community}/events.yml')
    events_file.parent.mkdir(exist_ok=True)
    
    # Read existing events
    events = []
    if events_file.exists():
        with open(events_file, 'r', encoding='utf-8') as f:
            events = yaml.safe_load(f) or []
    
    # Format new event
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
    event_exists = any(e['url'] == new_event['url'] for e in events)
    if not event_exists:
        events.append(new_event)
        
        # Sort events by date
        events.sort(key=lambda x: x['date'], reverse=True)
        
        # Save updated events
        with open(events_file, 'w', encoding='utf-8') as f:
            yaml.dump(events, f, allow_unicode=True, sort_keys=False)
        
        return True
    return False

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
        # Update community events
        updated = update_community_events(
            event_data['community'],
            event_data
        )
        
        if updated:
            # Commit changes
            os.system('git config --local user.email "github-actions[bot]@users.noreply.github.com"')
            os.system('git config --local user.name "github-actions[bot]"')
            os.system(f'git add {event_data["community"]}/events.yml')
            os.system('git commit -m "Add new event via bot [skip ci]"')
            os.system('git push')
            
            # Update issue
            issue.create_comment("✅ Event added successfully!")
            issue.add_to_labels('processed')
            issue.edit(state='closed')
        else:
            issue.create_comment("ℹ️ This event already exists in the calendar.")
            issue.add_to_labels('duplicate')
            
    except Exception as e:
        issue.create_comment(f"❌ Error processing event: {str(e)}")
        issue.add_to_labels('error')

if __name__ == "__main__":
    main()
