from pathlib import Path
import yaml
from datetime import datetime
from typing import List, Dict
import re
from collections import defaultdict

class ReadmeUpdater:
    """Updates README files with event information"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        
    def read_events(self, events_file: Path) -> List[Dict]:
        """Read and parse events from YAML file"""
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error reading events file {events_file}: {e}")
            return []
            
    def get_future_events(self, events: List[Dict]) -> List[Dict]:
        """Filter and sort future events"""
        now = datetime.now()
        future_events = [
            event for event in events
            if datetime.fromisoformat(event['date']) > now
        ]
        future_events.sort(key=lambda x: x['date'])  # Sort by date ascending
        return future_events

    def get_past_events(self, events: List[Dict]) -> List[Dict]:
        """Filter and sort past events"""
        now = datetime.now()
        past_events = [
            event for event in events
            if datetime.fromisoformat(event['date']) <= now
        ]
        past_events.sort(key=lambda x: x['date'], reverse=True)  # Sort by date descending
        return past_events
        
    def format_event_row_global(self, event: Dict) -> str:
        """Format event for global README table"""
        date = datetime.fromisoformat(event['date']).strftime('%Y-%m-%d')
        location = event.get('location', 'Online' if event.get('is_online') else 'TBD')
        return f"| {date} | {event['community']} | {event['title']} | {location} | {event['url']} |"
        
    def format_event_row_community(self, event: Dict) -> str:
        """Format event for community README table"""
        date = datetime.fromisoformat(event['date']).strftime('%Y-%m-%d %H:%M')
        location = event.get('location', 'Online' if event.get('is_online') else 'TBD')
        return f"| {date} | {event['title']} | {location} | {event['url']} |"
        
    def generate_year_section(self, year: int, events: List[Dict]) -> str:
        """Generate a collapsible section for a year's events"""
        table = (
            f"<details>\n"
            f"<summary>{year}</summary>\n\n"
            f"| Date | Event | Location | Link |\n"
            f"|------|--------|----------|------|\n"
        )
        table += "\n".join(self.format_event_row_community(event) for event in events)
        table += "\n</details>\n"
        return table
        
    def update_community_readme(self, community_dir: Path, events: List[Dict]):
        """Update a community's README with its events"""
        readme_path = community_dir / 'README.md'
        
        # Prepare content
        content = []
        
        # Upcoming events section
        future_events = self.get_future_events(events)
        if future_events:
            content.extend([
                "## 📅 Upcoming Events\n",
                "| Date | Event | Location | Link |",
                "|------|--------|----------|------|"
            ])
            content.extend(self.format_event_row_community(event) for event in future_events)
            content.append("\n")
        
        # Past events by year
        events_by_year = self.group_events_by_year(events)
        if events_by_year:
            content.append("## 📆 Past Events\n")
            for year, year_events in events_by_year.items():
                content.extend([
                    f"<details>",
                    f"<summary>{year}</summary>\n",
                    "| Date | Event | Location | Link |",
                    "|------|--------|----------|------|",
                    "\n".join(self.format_event_row_community(event) for event in year_events),
                    "</details>\n"
                ])
        
        # Update README
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                
            # Replace content between markers or add at the end
            events_pattern = r"(<!-- EVENTS:START -->).*(<!-- EVENTS:END -->)"
            if re.search(events_pattern, readme_content, re.DOTALL):
                readme_content = re.sub(
                    events_pattern,
                    f"<!-- EVENTS:START -->\n{'\n'.join(content)}\n<!-- EVENTS:END -->",
                    readme_content,
                    flags=re.DOTALL
                )
            else:
                readme_content += f"\n<!-- EVENTS:START -->\n{'\n'.join(content)}\n<!-- EVENTS:END -->\n"
        else:
            # Create new README if it doesn't exist
            readme_content = (
                f"# {community_dir.name}\n\n"
                f"<!-- EVENTS:START -->\n"
                f"{'\n'.join(content)}\n"
                f"<!-- EVENTS:END -->\n"
            )
            
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
    def update_global_readme(self, events: List[Dict]):
        """Update the global README with all upcoming events"""
        readme_path = self.root_dir / 'README.md'
        if not readme_path.exists():
            return
            
        future_events = self.get_future_events(events)[:10]  # Only show next 10 events
        
        # Generate events table
        events_table = (
            "| Date | Community | Event | Location | Link |\n"
            "|------|------------|--------|-----------|------|\n"
        )
        events_table += "\n".join(self.format_event_row_global(event) for event in future_events)
        
        # Update README
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace content between markers
        pattern = r"(<!-- ALL-EVENTS-LIST:START -->).*(<!-- ALL-EVENTS-LIST:END -->)"
        content = re.sub(
            pattern,
            f"\\1\n{events_table}\n\\2",
            content,
            flags=re.DOTALL
        )
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    def process_all(self):
        """Process all community directories and update READMEs"""
        all_events = []
        
        # Process each community
        for community_dir in self.root_dir.iterdir():
            if community_dir.is_dir() and not community_dir.name.startswith('.'):
                events_file = community_dir / 'events.yml'
                if events_file.exists():
                    events = self.read_events(events_file)
                    all_events.extend(events)
                    self.update_community_readme(community_dir, events)
        
        # Update global README
        self.update_global_readme(all_events)

def main():
    """Main script execution"""
    root_dir = Path('.')
    updater = ReadmeUpdater(root_dir)
    updater.process_all()

if __name__ == "__main__":
    main()
