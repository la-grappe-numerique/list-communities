from pathlib import Path
import yaml

def get_communities():
    """Get list of communities from directories"""
    root_dir = Path('.')
    communities = []
    
    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name in ['docs', 'template']:
            communities.append(item.name)
    
    return sorted(communities)

def generate_template():
    """Generate the issue template with dynamic community list"""
    communities = get_communities()
    
    template = {
        'name': 'Add Event',
        'description': 'Add a new community event',
        'title': '[Event]: ',
        'labels': ['event'],
        'body': [
            {
                'type': 'input',
                'id': 'title',
                'attributes': {
                    'label': 'Event Title',
                    'description': 'The name of the event',
                    'placeholder': 'ex: Meetup AWS re:Invent re:Cap'
                },
                'validations': {
                    'required': True
                }
            },
            {
                'type': 'input',
                'id': 'date',
                'attributes': {
                    'label': 'Event Date',
                    'description': 'When will the event take place? (YYYY-MM-DD HH:mm)',
                    'placeholder': '2025-02-20 18:30'
                },
                'validations': {
                    'required': True
                }
            },
            {
                'type': 'input',
                'id': 'url',
                'attributes': {
                    'label': 'Event URL',
                    'description': 'Link to the event page',
                    'placeholder': 'https://www.meetup.com/...'
                },
                'validations': {
                    'required': True
                }
            },
            {
                'type': 'dropdown',
                'id': 'community',
                'attributes': {
                    'label': 'Community',
                    'description': 'Select the organizing community',
                    'options': communities
                },
                'validations': {
                    'required': True
                }
            },
            {
                'type': 'input',
                'id': 'location',
                'attributes': {
                    'label': 'Location',
                    'description': 'Where will the event take place?',
                    'placeholder': 'Betclic, 117 Quai de Bacalan, Bordeaux, France'
                },
                'validations': {
                    'required': True
                }
            },
            {
                'type': 'textarea',
                'id': 'description',
                'attributes': {
                    'label': 'Description',
                    'description': 'Event description (supports markdown)',
                    'placeholder': 'Description of the event...'
                },
                'validations': {
                    'required': False
                }
            },
            {
                'type': 'dropdown',
                'id': 'is_online',
                'attributes': {
                    'label': 'Is this an online event?',
                    'options': ['No', 'Yes']
                },
                'validations': {
                    'required': True
                }
            }
        ]
    }
    
    # Write template
    template_dir = Path('.github/ISSUE_TEMPLATE')
    template_dir.mkdir(parents=True, exist_ok=True)
    
    with open(template_dir / 'event.yml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    generate_template()
