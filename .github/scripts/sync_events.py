import json
from pathlib import Path
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional, Dict
import pytz

@dataclass
class EventVenue:
    """Represents a venue location"""
    name: str
    address: str
    city: str
    country: str

@dataclass
class Event:
    """Represents a single event with all its details"""
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
        """Parse a community's events_src.json file"""
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
    """Handles reading events from the Meetup API"""
    
    def __init__(self):
        # Timezone for France, used if no specific timezone is provided
        self.default_timezone = pytz.timezone('Europe/Paris')
    
    @staticmethod
    def extract_meetup_name_from_url(url: str) -> str:
        """Extract the Meetup group name from its URL"""
        return url.rstrip('/').split('/')[-1]
    
    @staticmethod
    def clean_html_description(html_description: str) -> str:
        """Convert HTML description to plain text while preserving formatting"""
        soup = BeautifulSoup(html_description, 'html.parser')
        for br in soup.find_all(['br', 'p']):
            br.replace_with('\n' + br.text + '\n')
        text = soup.get_text()
        return re.sub(r'\n\s*\n', '\n', text).strip()

    def get_event_timezone(self, event_data: Dict) -> pytz.timezone:
        """
        Extract timezone from event data.
        Falls back to Europe/Paris if no timezone is found or if it's invalid.
        """
        try:
            # Get timezone from event data
            if 'group' in event_data and 'timezone' in event_data['group']:
                return pytz.timezone(event_data['group']['timezone'])
            # Try venue timezone
            elif 'venue' in event_data and 'timezone' in event_data['venue']:
                return pytz.timezone(event_data['venue']['timezone'])
        except pytz.exceptions.UnknownTimeZoneError:
            pass
        
        # Default to French timezone if no valid timezone found
        return self.default_timezone

    def parse_event_time(self, event_data: Dict) -> datetime:
        """
        Parse event time with proper timezone handling.
        Returns datetime in the event's local timezone.
        """
        event_tz = self.get_event_timezone(event_data)
        
        # Convert milliseconds timestamp to seconds
        timestamp = event_data['time'] / 1000
        
        # Create UTC time first
        utc_time = datetime.fromtimestamp(timestamp, pytz.UTC)
        
        # Convert to event's timezone
        local_time = utc_time.astimezone(event_tz)
        
        return local_time

    def get_events(self, url: str, community: str, status: List[str]) -> List[Event]:
        """Fetch events from Meetup API for a given community"""
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
                    
                    # Get event time in its local timezone
                    event_time = self.parse_event_time(event_data)
                    
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
                    
                    # Debug log
                    print(f"Event: {event.title}")
                    print(f"Original timestamp: {event_data['time']}")
                    print(f"Parsed time: {event_time}")
                    print(f"Timezone: {event_time.tzinfo}")
                    print("---")
                    
            except Exception as e:
                print(f"Error fetching API data for {group_name} with status {event_status}: {e}")
                continue
                
        return all_events

class CommunityEventManager:
    """Manages event synchronization for individual communities"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def process_community_folder(self, folder_path: Path):
        """Process a single community folder and update its events"""
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
        self.write_events(events_file, new_events)
        print(f"Updated events for {community_name}")

    def write_events(self, file_path: Path, events: List[Event]):
        """Write events to a JSON file with proper formatting"""
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

        formatted_events = [format_event(event) for event in events]
        formatted_events.sort(key=lambda x: x['date'], reverse=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_events, f, indent=2, ensure_ascii=False)

    def process_all_communities(self):
        """Process all community folders in the root directory"""
        for item in self.root_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                self.process_community_folder(item)

def main():
    root_dir = Path('.')
    manager = CommunityEventManager(root_dir)
    manager.process_all_communities()

if __name__ == "__main__":
    main()