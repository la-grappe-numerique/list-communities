import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import json
import requests
from pathlib import Path
import re
from bs4 import BeautifulSoup

@dataclass
class EventVenue:
    """Represents a venue location"""
    name: str
    address: str
    city: str
    country: str

@dataclass
class Event:
    """Represents a single event"""
    title: str
    date: datetime
    url: str
    description: str
    community: str
    venue: Optional[EventVenue] = None
    rsvp_limit: Optional[int] = None
    rsvp_count: Optional[int] = None
    is_online: bool = False

class EventSourceParser:
    """Handles parsing of event source configuration files"""
    
    @staticmethod
    def parse_source_file(file_path: Path, community_name: str) -> Optional[Dict]:
        """Parse an events_src.json file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'type': data.get('type'),
                    'url': data.get('url'),
                    'community': community_name,
                    'status': data.get('status', ['upcoming'])
                }
        except Exception as e:
            print(f"Error parsing source file {file_path}: {e}")
            return None

class MeetupAPIReader:
    """Handles reading events from Meetup API"""
    
    @staticmethod
    def extract_meetup_name_from_url(url: str) -> str:
        """Extract Meetup group name from URL"""
        return url.rstrip('/').split('/')[-1]
    
    @staticmethod
    def clean_html_description(html_description: str) -> str:
        """Convert HTML description to plain text while preserving formatting"""
        soup = BeautifulSoup(html_description, 'html.parser')
        for br in soup.find_all(['br', 'p']):
            br.replace_with('\n' + br.text + '\n')
        text = soup.get_text()
        return re.sub(r'\n\s*\n', '\n', text).strip()

    def get_events(self, url: str, community: str, status: List[str]) -> List[Event]:
        """Fetch events from Meetup API"""
        group_name = self.extract_meetup_name_from_url(url)
        all_events = []
        
        for event_status in status:
            try:
                api_url = f"https://api.meetup.com/{group_name}/events"
                params = {'status': event_status}
                
                response = requests.get(api_url, params=params)
                response.raise_for_status()
                events_data = response.json()
                
                for event_data in events_data:
                    venue = None
                    if 'venue' in event_data:
                        v = event_data['venue']
                        venue = EventVenue(
                            name=v.get('name', ''),
                            address=v.get('address_1', ''),
                            city=v.get('city', ''),
                            country=v.get('localized_country_name', '')
                        )
                    
                    event_time = datetime.fromtimestamp(event_data['time'] / 1000)
                    
                    event = Event(
                        title=event_data['name'],
                        date=event_time,
                        url=event_data['link'],
                        description=self.clean_html_description(event_data['description']),
                        community=community,
                        venue=venue,
                        rsvp_limit=event_data.get('rsvp_limit'),
                        rsvp_count=event_data.get('yes_rsvp_count'),
                        is_online=event_data.get('is_online_event', False)
                    )
                    all_events.append(event)
                    
            except Exception as e:
                print(f"Error fetching API data for {group_name} with status {event_status}: {e}")
                continue
                
        return all_events

class EventsFile:
    """Handles reading and writing events files"""

    @staticmethod
    def read_existing_events(file_path: Path) -> List[Dict]:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or []
            except Exception as e:
                print(f"Error reading events file {file_path}: {e}")
                return []
        return []

    @staticmethod
    def format_venue(venue: EventVenue) -> Dict:
        """Format venue information for YAML output"""
        return {
            'name': venue.name,
            'address': venue.address,
            'city': venue.city,
            'country': venue.country
        }

    @staticmethod
    def format_event_for_yaml(event: Event) -> Dict:
        """Format a single event for YAML output"""
        event_dict = {
            'title': event.title,
            'date': event.date.isoformat(),
            'url': event.url,
            'description': event.description,
            'community': event.community,
            'is_online': event.is_online
        }

        if event.venue:
            event_dict['venue'] = EventsFile.format_venue(event.venue)
            event_dict['location'] = f"{event.venue.address}, {event.venue.city}"

        if event.rsvp_limit:
            event_dict['rsvp_limit'] = event.rsvp_limit

        if event.rsvp_count:
            event_dict['rsvp_count'] = event.rsvp_count

        return event_dict

    class CustomYAMLFormatter(yaml.SafeDumper):
        pass

    @staticmethod
    def str_presenter(dumper, data):
        """Custom string presenter for YAML"""
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='')

    @staticmethod
    def write_events(file_path: Path, events: List[Event], existing_events: List[Dict], is_global: bool = False):
        """Write events to a YAML file, preserving existing events"""
        def format_event(event: Event, is_global: bool) -> Dict:
            if is_global:
                # Simplified format for global file
                event_dict = {
                    'title': event.title,
                    'date': event.date.isoformat(),
                    'url': event.url,
                    'community': event.community,
                    'is_online': event.is_online
                }
                if event.venue:
                    event_dict['location'] = f"{event.venue.address}, {event.venue.city}, {event.venue.country}"
                else:
                    event_dict['location'] = ''
                return event_dict
            else:
                # Full format for community files
                return EventsFile.format_event_for_yaml(event)

        new_events = [
            format_event(event, is_global)
            for event in events
            if event.date is not None
        ]

        existing_urls = {event['url'] for event in existing_events}
        unique_new_events = [
            event for event in new_events
            if event['url'] not in existing_urls
        ]

        all_events = existing_events + unique_new_events
        all_events.sort(
            key=lambda x: datetime.fromisoformat(x['date']) if x['date'] else datetime.min,
            reverse=True
        )

        # Register the custom string presenter
        EventsFile.CustomYAMLFormatter.add_representer(str, EventsFile.str_presenter)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    all_events,
                    f,
                    Dumper=EventsFile.CustomYAMLFormatter,
                    allow_unicode=True,
                    sort_keys=False,
                    width=10000
                )
        except Exception as e:
            print(f"Error writing events file {file_path}: {e}")

class EventsManager:
    """Manages both community-specific and global events"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.global_events_file = root_dir / 'events.json'
        self.all_new_events: List[Event] = []

    def process_community_folder(self, folder_path: Path):
        """Process a single community folder"""
        community_name = folder_path.name
        source_file = folder_path / 'events_src.json'
        events_file = folder_path / 'events.json'
        
        if not source_file.exists():
            return
            
        source = EventSourceParser.parse_source_file(source_file, community_name)
        if not source or source['type'] != 'meetup':
            return
            
        reader = MeetupAPIReader()
        new_events = reader.get_events(source['url'], community_name, source['status'])
        self.all_new_events.extend(new_events)
        
        existing_events = self.read_existing_events(events_file)
        self.write_events(events_file, new_events, existing_events)
        print(f"Updated events for {community_name}")

    def read_existing_events(self, file_path: Path) -> List[Dict]:
        """Read existing events from JSON file"""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading events file {file_path}: {e}")
                return []
        return []

    def write_events(self, file_path: Path, events: List[Event], existing_events: List[Dict]):
        """Write events to a JSON file"""
        def format_event(event: Event) -> Dict:
            event_dict = {
                'title': event.title,
                'date': event.date.isoformat(),
                'url': event.url,
                'description': event.description,
                'community': event.community,
                'is_online': event.is_online
            }
            
            if event.venue:
                event_dict['venue'] = {
                    'name': event.venue.name,
                    'address': event.venue.address,
                    'city': event.venue.city,
                    'country': event.venue.country
                }
                event_dict['location'] = f"{event.venue.address}, {event.venue.city}"
            
            if event.rsvp_limit:
                event_dict['rsvp_limit'] = event.rsvp_limit
            
            if event.rsvp_count:
                event_dict['rsvp_count'] = event.rsvp_count
                
            return event_dict

        new_events = [format_event(event) for event in events]
        existing_urls = {event['url'] for event in existing_events}
        unique_new_events = [
            event for event in new_events
            if event['url'] not in existing_urls
        ]
        
        all_events = existing_events + unique_new_events
        all_events.sort(
            key=lambda x: datetime.fromisoformat(x['date']),
            reverse=True
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_events, f, indent=2, ensure_ascii=False)

    def update_global_events(self):
        """Update the global events file with events from all communities"""
        existing_global_events = self.read_existing_events(self.global_events_file)
        self.write_events(self.global_events_file, self.all_new_events, existing_global_events)
        print("Updated global events file")

    def process_all_communities(self):
        """Process all community folders and update global events"""
        for item in self.root_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                self.process_community_folder(item)
        
        self.update_global_events()

def main():
    """Main script execution"""
    root_dir = Path('.')
    manager = EventsManager(root_dir)
    manager.process_all_communities()

if __name__ == "__main__":
    main()