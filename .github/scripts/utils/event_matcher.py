from datetime import datetime
import re
from typing import Dict, List

class EventMatcher:
    """Utility class for matching and comparing events"""

    def normalize_url(url: str) -> str:
        """Normalize URL by removing language prefix and trailing slashes"""
        # Remove language code (e.g., /fr-FR/)
        url = re.sub(r'meetup\.com/[a-z]{2}-[A-Z]{2}/', 'meetup.com/', url)
        # Remove trailing slash
        url = url.rstrip('/')
        return url

    @staticmethod
    def normalize_location(location: str) -> str:
        """
        Normalize location string to help with comparison.
        Removes spaces, makes lowercase, and removes common variations.
        """
        if not location:
            return ""
        
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', location.lower().strip())
        
        # Remove common address parts that might be written differently
        normalized = re.sub(r'\b(rue|avenue|av|boulevard|bd|place|pl)\b', '', normalized)
        
        # Remove postal codes
        normalized = re.sub(r'\b\d{5}\b', '', normalized)
        
        # Remove common separators
        normalized = re.sub(r'[,.-]', ' ', normalized)
        
        # Remove extra spaces and return
        return re.sub(r'\s+', ' ', normalized).strip()

    @staticmethod
    def compare_titles(title1: str, title2: str) -> float:
        """
        Compare two titles and return similarity score (0 to 1)
        """
        # Simple word set comparison for titles
        words1 = set(re.findall(r'\w+', title1.lower()))
        words2 = set(re.findall(r'\w+', title2.lower()))
        return len(words1.intersection(words2)) / max(len(words1), len(words2))

    @classmethod
    def are_same_event(cls, event1: Dict, event2: Dict) -> bool:
        """
        Determine if two events are actually the same event based on multiple criteria.
        Returns True if events are considered the same.
        """
        # If URLs are same after normalization, it's definitely the same event
        if 'url' in event1 and 'url' in event2:
            url1 = cls.normalize_url(event1['url'])
            url2 = cls.normalize_url(event2['url'])
            if url1 == url2:
                return True
        
        # Compare dates (must be exactly the same)
        try:
            date1 = datetime.fromisoformat(event1['date'])
            date2 = datetime.fromisoformat(event2['date'])
            if date1 != date2:
                return False
        except (KeyError, ValueError):
            return False

        # Compare locations (if both events have locations)
        location1 = event1.get('location', '')
        location2 = event2.get('location', '')
        if location1 and location2:
            norm_loc1 = cls.normalize_location(location1)
            norm_loc2 = cls.normalize_location(location2)
            if norm_loc1 != norm_loc2:
                return False

        # If we have same date and location, do a title similarity check
        title1 = event1.get('title', '')
        title2 = event2.get('title', '')
        if not title1 or not title2:
            return False
        
        # If titles are very similar (>70% same words), consider it the same event
        return cls.compare_titles(title1, title2) > 0.7

    @classmethod
    def find_matching_event(cls, event: Dict, event_list: List[Dict]) -> Dict | None:
        """
        Search through a list of events and return the first matching event, if any.
        Returns None if no match is found.
        """
        for existing_event in event_list:
            if cls.are_same_event(event, existing_event):
                return existing_event
        return None

    @classmethod
    def merge_event_communities(cls, event1: Dict, event2: Dict) -> List[str]:
        """
        Merge communities from two events into a single sorted list.
        """
        communities1 = event1.get('communities', [event1.get('community')] if event1.get('community') else [])
        communities2 = event2.get('communities', [event2.get('community')] if event2.get('community') else [])
        
        # Combine and deduplicate
        all_communities = set(
            [c for c in communities1 if c is not None] +
            [c for c in communities2 if c is not None]
        )
        
        return sorted(list(all_communities))