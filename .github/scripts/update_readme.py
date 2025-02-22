import pytz
from pathlib import Path
import json
from datetime import datetime
import locale
from collections import defaultdict
from typing import List, Dict, Optional
import re

class ReadmeUpdater:
    """Updates README files with event information"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.timezone = pytz.timezone('Europe/Paris')
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

    def read_events(self, events_file: Path) -> List[Dict]:
        """Read and parse events from JSON file"""
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading events file {events_file}: {e}")
            return []

    def format_date_for_display(self, date: datetime) -> str:
        """Format date for display in markdown with day name and month name"""
        # Format in French locale
        formatted = date.strftime('%A %d %B %Y à %H:%M')
        return formatted[0].upper() + formatted[1:]

    def parse_date(self, date_str: str) -> datetime:
        """Parse an ISO format date string to timezone-aware datetime"""
        date = datetime.fromisoformat(date_str)
        # If the date has no timezone, assume it's in French time
        if date.tzinfo is None:
            date = self.timezone.localize(date)
        return date

    def get_future_events(self, events: List[Dict]) -> List[Dict]:
        """Filter and sort future events"""
        now = datetime.now(self.timezone)
        future_events = [
            event for event in events
            if self.parse_date(event['date']) > now
        ]
        future_events.sort(key=lambda x: self.parse_date(x['date']))
        return future_events

    def get_past_events(self, events: List[Dict]) -> List[Dict]:
        """Filter and sort past events"""
        now = datetime.now(self.timezone)
        past_events = [
            event for event in events
            if self.parse_date(event['date']) <= now
        ]
        past_events.sort(key=lambda x: self.parse_date(x['date']), reverse=True)
        return past_events

    def format_event_row_community(self, event: Dict) -> str:
        """Format event for community README table"""
        date = self.parse_date(event['date'])
        formatted_date = self.format_date_for_display(date)
        location = event.get('location', 'Online' if event.get('is_online') else 'TBD')
        return f"| {formatted_date} | {event['title']} | {location} | {event['url']} |"

    def format_event_row_global(self, event: Dict) -> str:
        """Format event for global README table"""
        date = self.parse_date(event['date'])
        formatted_date = self.format_date_for_display(date)
        location = event.get('location', 'Online' if event.get('is_online') else 'TBD')
        
        # Handle multiple communities
        if 'communities' in event:
            # Sort communities: primary first, then alphabetically
            sorted_communities = sorted(
                event['communities'],
                key=lambda x: (not x['primary'], x['name'])
            )
            community_links = [
                f"[{comm['name']}]({comm['name']}/)"
                for comm in sorted_communities
            ]
            community_cell = ' & '.join(community_links)
        else:
            # Backward compatibility for single community events
            community = event.get('community', '')
            community_cell = f"[{community}]({community}/)"

        return f"| {formatted_date} | {community_cell} | [{event['title']}]({event['url']}) | {location} |"

    def group_events_by_year(self, events: List[Dict]) -> Dict[int, List[Dict]]:
        """Group events by year"""
        past_events = self.get_past_events(events)
        events_by_year = defaultdict(list)
        for event in past_events:
            year = self.parse_date(event['date']).year
            events_by_year[year].append(event)
        
        return dict(sorted(events_by_year.items(), reverse=True))

    def update_community_readme(self, community_dir: Path, events: List[Dict]):
        """Update a community's README with its events"""
        readme_path = community_dir / 'README.md'

        # Prepare content sections
        content_parts = []

        # Upcoming events section
        future_events = self.get_future_events(events)
        if future_events:
            upcoming_section = [
                "## 📅 Upcoming Events",
                "",
                "| Date | Event | Location | Link |",
                "|------|--------|----------|------|",
                *[self.format_event_row_community(event) for event in future_events],
                ""
            ]
            content_parts.extend(upcoming_section)

        # Past events by year
        events_by_year = self.group_events_by_year(events)
        if events_by_year:
            content_parts.append("## 📆 Past Events\n")
            for year, year_events in events_by_year.items():
                year_section = [
                    "<details>",
                    f"<summary>{year}</summary>",
                    "",
                    "| Date | Event | Location | Link |",
                    "|------|--------|----------|------|",
                    *[self.format_event_row_community(event) for event in year_events],
                    "</details>",
                    ""
                ]
                content_parts.extend(year_section)

        # Join all content parts
        full_content = "\n".join(content_parts)

        # Read existing README if it exists
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                current_content = f.read()

            # Replace between markers or append
            marker_pattern = r"<!-- EVENTS:START -->.*<!-- EVENTS:END -->"
            if re.search(marker_pattern, current_content, re.DOTALL):
                new_content = re.sub(
                    marker_pattern,
                    "<!-- EVENTS:START -->\n" + full_content + "<!-- EVENTS:END -->",
                    current_content,
                    flags=re.DOTALL
                )
            else:
                new_content = current_content + "\n<!-- EVENTS:START -->\n" + full_content + "<!-- EVENTS:END -->\n"
        else:
            # Create new README
            new_content = f"# {community_dir.name}\n\n<!-- EVENTS:START -->\n{full_content}<!-- EVENTS:END -->\n"

        # Write the updated content
        print(f"Update {readme_path} with {len(future_events)} future events")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def update_global_readme(self, events: List[Dict]):
        """Update the global README with all upcoming events"""
        readme_path = self.root_dir / 'README.md'
        if not readme_path.exists():
            print("Global README does not exist.")
            return

        future_events = self.get_future_events(events)[:3]  # Only show next 3 events
        # Generate events table
        table_lines = [
            "| Date | Community(ies) | Event | Location |",
            "|------|------------|--------|-----------|",
            *[self.format_event_row_global(event) for event in future_events]
        ]
        events_table = "\n".join(table_lines)

        # Update README
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace content between markers
        pattern = r"<!-- ALL-EVENTS-LIST:START -->.*?<!-- ALL-EVENTS-LIST:END -->"
        new_content = re.sub(
            pattern,
            "<!-- ALL-EVENTS-LIST:START -->\n" + events_table + "\n<!-- ALL-EVENTS-LIST:END -->",
            content,
            flags=re.DOTALL
        )

        print(f"Update global {readme_path} with {len(future_events)} events")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def process_all(self):
        """Process all community directories and update READMEs"""
        for community_dir in self.root_dir.iterdir():
            if community_dir.is_dir() and not community_dir.name.startswith('.') and not community_dir.name in ['docs', 'template']:
                events_file = community_dir / 'events.json'
                if events_file.exists():
                    events = self.read_events(events_file)
                    self.update_community_readme(community_dir, events)
        
        # Update global README
        global_events = []
        for community_dir in self.root_dir.iterdir():
            if community_dir.is_dir() and not community_dir.name.startswith('.'):
                events_file = community_dir / 'events.json'
                if events_file.exists():
                    events = self.read_events(events_file)
                    global_events.extend(events)
        
        self.update_global_readme(global_events)

def main():
    """Main script execution"""
    root_dir = Path('.')
    updater = ReadmeUpdater(root_dir)
    updater.process_all()

if __name__ == "__main__":
    main()
