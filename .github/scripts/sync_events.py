import json
from pathlib import Path
from datetime import datetime
import re
import time
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict
import pytz
from teemup import parse as teemup_parse

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
                }
        except Exception as e:
            print(f"Error parsing source file {file_path}: {e}")
            return None

class MeetupTeemupReader:
    """Handles reading events from Meetup using teemup HTML parsing"""

    def __init__(self):
        # Timezone for France, used if no specific timezone is provided
        self.default_timezone = pytz.timezone('Europe/Paris')

    @staticmethod
    def clean_description(description: str) -> str:
        """Clean up description text"""
        if not description:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', description)
        return text.strip()

    def fetch_meetup_html(self, url: str) -> Optional[bytes]:
        """Fetch HTML content from Meetup page using requests with proper headers"""
        # Normalize URL - remove language prefix if present for more consistent access
        url = re.sub(r'meetup\.com/[a-z]{2}-[A-Z]{2}/', 'meetup.com/', url)

        # Ensure URL ends with slash for better parsing
        if not url.endswith('/'):
            url = url + '/'

        # Comprehensive headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Meetup page {url}: {e}")
            return None

    def get_events(self, url: str, community: str) -> List[Event]:
        """Fetch events from Meetup using teemup HTML parsing"""
        print(f"Fetching events for {community} from {url}")

        html = self.fetch_meetup_html(url)
        if not html:
            return []

        try:
            events_data = teemup_parse(html)
            print(f"Found {len(events_data)} events for {community}")
        except Exception as e:
            print(f"Error parsing Meetup HTML for {community}: {e}")
            return []

        events = []
        for event_data in events_data:
            try:
                # Parse venue if available
                venue = None
                is_online = False

                if 'venue' in event_data and event_data['venue']:
                    v = event_data['venue']
                    venue = EventVenue(
                        name=v.get('name', ''),
                        address=v.get('address', ''),
                        city=v.get('city', ''),
                        country=v.get('country', '')
                    )
                else:
                    # If no venue, assume it might be online
                    is_online = True

                # Parse start time - teemup returns datetime objects
                starts_at = event_data.get('starts_at')
                if starts_at is None:
                    print(f"Skipping event without start time: {event_data.get('title', 'Unknown')}")
                    continue

                # Ensure datetime has timezone info
                if starts_at.tzinfo is None:
                    starts_at = self.default_timezone.localize(starts_at)

                event = Event(
                    title=event_data.get('title', ''),
                    date=starts_at,
                    url=event_data.get('url', ''),
                    description=self.clean_description(event_data.get('description', '')),
                    community=community,
                    venue=venue,
                    is_online=is_online
                )
                events.append(event)

                # Debug log
                print(f"  - {event.title} ({starts_at.strftime('%Y-%m-%d %H:%M')})")

            except Exception as e:
                print(f"Error parsing event data: {e}")
                continue

        return events

class CommunityEventManager:
    """Manages event synchronization for individual communities"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.reader = MeetupTeemupReader()

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

        new_events = self.reader.get_events(source['url'], community_name)

        if new_events:
            # Merge with existing events to preserve manually added events
            existing_events = self.read_existing_events(events_file)
            merged_events = self.merge_events(existing_events, new_events)
            self.write_events(events_file, merged_events)
            print(f"Updated events for {community_name}: {len(new_events)} from Meetup, {len(merged_events)} total")
        else:
            print(f"No new events found for {community_name}")

    def read_existing_events(self, file_path: Path) -> List[Dict]:
        """Read existing events from JSON file"""
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading existing events from {file_path}: {e}")
            return []

    def merge_events(self, existing: List[Dict], new_events: List[Event]) -> List[Event]:
        """
        Merge existing events with new events from Meetup.
        - Keep ALL existing events (history)
        - Add/update new Meetup events (avoid duplicates by URL)
        """
        # Get URLs from new Meetup events for duplicate detection
        new_urls = {event.url for event in new_events}

        # Convert existing events to Event objects, keeping all of them
        preserved_events = []
        for event in existing:
            url = event.get('url', '')

            # Skip if this URL is in the new events (will be replaced with fresh data)
            if url in new_urls:
                continue

            # Convert dict to Event object
            venue = None
            if 'venue' in event:
                v = event['venue']
                venue = EventVenue(
                    name=v.get('name', ''),
                    address=v.get('address', ''),
                    city=v.get('city', ''),
                    country=v.get('country', '')
                )
            try:
                date_str = event.get('date', '')
                if date_str:
                    date = datetime.fromisoformat(date_str)
                else:
                    continue

                preserved_event = Event(
                    title=event.get('title', ''),
                    date=date,
                    url=url,
                    description=event.get('description', ''),
                    community=event.get('community', ''),
                    venue=venue,
                    is_online=event.get('is_online', False)
                )
                preserved_events.append(preserved_event)
            except Exception as e:
                print(f"Error converting existing event: {e}")

        # Combine preserved events with new Meetup events
        return preserved_events + new_events

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
                # Build location string
                location_parts = []
                if event.venue.address:
                    location_parts.append(event.venue.address)
                if event.venue.city:
                    location_parts.append(event.venue.city)
                if location_parts:
                    event_dict['location'] = ", ".join(location_parts)

            return event_dict

        formatted_events = [format_event(event) for event in events]
        formatted_events.sort(key=lambda x: x['date'], reverse=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_events, f, indent=2, ensure_ascii=False)

    def process_all_communities(self):
        """Process all community folders in the root directory"""
        communities = [
            item for item in self.root_dir.iterdir()
            if item.is_dir() and not item.name.startswith('.')
        ]

        total = len(communities)
        processed = 0

        for item in communities:
            self.process_community_folder(item)
            processed += 1

            # Add delay between requests to avoid rate limiting
            if processed < total:
                time.sleep(2)  # 2 seconds between each community

        print(f"\nSync complete: processed {processed} communities")

def main():
    root_dir = Path('.')
    manager = CommunityEventManager(root_dir)
    manager.process_all_communities()

if __name__ == "__main__":
    main()