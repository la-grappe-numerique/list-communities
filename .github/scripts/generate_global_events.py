from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict

class GlobalEventsGenerator:
    """Generates a global events file by combining all community events"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.output_file = root_dir / 'events.json'

    def read_community_events(self, events_file: Path) -> List[Dict]:
        """Read events from a community's events file"""
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading events file {events_file}: {e}")
            return []

    def generate_global_events(self):
        """Generate global events file by combining all community events"""
        all_events = []

        # Collect all events from communities
        for community_dir in self.root_dir.iterdir():
            if community_dir.is_dir() and not community_dir.name.startswith('.'):
                events_file = community_dir / 'events.json'
                if events_file.exists():
                    events = self.read_community_events(events_file)
                    all_events.extend(events)

        # Sort all events by date, most recent first
        all_events.sort(key=lambda x: x['date'], reverse=True)

        # Write the combined events to the global file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(all_events, f, indent=2, ensure_ascii=False)
        
        print(f"Generated global events file with {len(all_events)} events")

def main():
    root_dir = Path('.')
    generator = GlobalEventsGenerator(root_dir)
    generator.generate_global_events()

if __name__ == "__main__":
    main()