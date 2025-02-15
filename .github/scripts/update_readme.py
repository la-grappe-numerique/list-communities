from pathlib import Path
import yaml
from datetime import datetime
import re

def read_global_events(root_dir: Path) -> list:
    """Read and parse the global events file"""
    try:
        with open(root_dir / 'events.yml', 'r', encoding='utf-8') as f:
            events = yaml.safe_load(f) or []
            
        # Filter future events and sort by date
        now = datetime.now()
        future_events = [
            event for event in events
            if datetime.fromisoformat(event['date']) > now
        ]
        future_events.sort(key=lambda x: x['date'])
        
        return future_events[:10]  # Return only next 10 events
    except Exception as e:
        print(f"Error reading events file: {e}")
        return []

def format_event_row(event: dict) -> str:
    """Format a single event as a markdown table row"""
    date = datetime.fromisoformat(event['date']).strftime('%Y-%m-%d')
    location = event.get('location', 'En ligne' if event.get('is_online') else 'À définir')
    
    return f"| {date} | {event['community']} | {event['title']} | {location} | {event['url']} |"

def update_readme(root_dir: Path):
    """Update the README.md file with the next 10 events"""
    readme_path = root_dir / 'README.md'
    if not readme_path.exists():
        print("README.md not found")
        return
        
    # Read current README content
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Get upcoming events
    events = read_global_events(root_dir)
    
    # Prepare new events section
    events_table = (
        "| Date | Communauté | Événement | Lieu | Lien |\n"
        "|------|------------|-----------|------|------|\n"
    )
    events_table += "\n".join(format_event_row(event) for event in events)
    
    # Replace content between markers
    pattern = r"(<!-- ALL-EVENTS-LIST:START - Do not remove or modify this section -->).*(<!-- ALL-EVENTS-LIST:STOP - Do not remove or modify this section -->)"
    new_content = re.sub(
        pattern,
        f"\\1\n{events_table}\n\\2",
        content,
        flags=re.DOTALL
    )
    
    # Write updated content
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("README.md updated with upcoming events")

def main():
    """Main script execution"""
    root_dir = Path('.')
    update_readme(root_dir)

if __name__ == "__main__":
    main()
