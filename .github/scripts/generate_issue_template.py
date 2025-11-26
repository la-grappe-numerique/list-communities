from pathlib import Path
import yaml

from utils.event_matcher import EventMatcher

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
        'name': 'Ajouter un évènement',
        'description': 'Ajouter un nouvel évènement communautaire',
        'title': '[Évènement]: ',
        'labels': ['event'],
        'body': [
            {
                'type': 'input',
                'id': 'title',
                'attributes': {
                    'label': 'Titre de l\'évènement',
                    'description': 'Le nom de l\'évènement',
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
                    'label': 'Date de l\'évènement',
                    'description': 'Quand aura lieu l\'évènement ? (AAAA-MM-JJ HH:mm)',
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
                    'label': 'URL de l\'évènement',
                    'description': 'Lien vers la page de l\'évènement',
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
                    'label': 'Communauté',
                    'description': 'Sélectionnez la communauté organisatrice',
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
                    'label': 'Lieu',
                    'description': 'Où se déroulera l\'évènement ?',
                    'placeholder': 'Le Node, 12 Rue des Faussets, 33000 Bordeaux'
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
                    'description': 'Description de l\'évènement (supporte le markdown)',
                    'placeholder': 'Cet évènement exceptionnel...'
                },
                'validations': {
                    'required': False
                }
            },
            {
                'type': 'dropdown',
                'id': 'is_online',
                'attributes': {
                    'label': 'Évènement en ligne ?',
                    'description': 'S\'agit-il d\'un évènement en ligne ?',
                    'options': ['Non', 'Oui']
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
