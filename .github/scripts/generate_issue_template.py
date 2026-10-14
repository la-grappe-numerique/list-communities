from pathlib import Path
import yaml

from utils.event_matcher import EventMatcher


def get_communities():
    """Get list of communities from directories"""
    root_dir = Path(".")
    communities = []

    for item in root_dir.iterdir():
        if (
            item.is_dir()
            and not item.name.startswith(".")
            and not item.name in ["docs", "template"]
        ):
            communities.append(item.name)

    return sorted(communities)


def generate_template():
    """Generate the issue template with dynamic community list"""
    communities = get_communities()

    template = {
        "name": "Add Event",
        "description": "Ajouter un nouvel événement communautaire",
        "title": "[Event]: ",
        "labels": ["event"],
        "body": [
            {
                "type": "input",
                "id": "title",
                "attributes": {
                    "label": "Event Title",
                    "description": "Le nom de l'événement",
                    "placeholder": "ex: Meetup AWS re:Invent re:Cap",
                },
                "validations": {"required": True},
            },
            {
                "type": "input",
                "id": "date",
                "attributes": {
                    "label": "Event Date",
                    "description": "Quand l'événement aura-t-il lieu ? (AAAA-MM-JJ HH:mm)",
                    "placeholder": "2025-02-20 18:30",
                },
                "validations": {"required": True},
            },
            {
                "type": "input",
                "id": "url",
                "attributes": {
                    "label": "Event URL",
                    "description": "Lien vers la page de l'événement",
                    "placeholder": "https://www.meetup.com/...",
                },
                "validations": {"required": True},
            },
            {
                "type": "dropdown",
                "id": "community",
                "attributes": {
                    "label": "Community",
                    "description": "Sélectionnez la communauté organisatrice",
                    "options": communities,
                },
                "validations": {"required": True},
            },
            {
                "type": "input",
                "id": "location",
                "attributes": {
                    "label": "Location",
                    "description": "Où se déroulera l'évènement ?",
                    "placeholder": "Le node, 12 Rue des Faussets, 33000 Bordeaux"
                },
                "validations": {"required": True},
            },
            {
                "type": "textarea",
                "id": "description",
                "attributes": {
                    "label": "Description",
                    "description": "Description de l'évènement (supports markdown)",
                    "placeholder": "Cet évènement exceptionnel ..."
                },
                "validations": {"required": False},
            },
            {
                "type": "dropdown",
                "id": "is_online",
                "attributes": {
                    "label": "S'agit-il d'un événement en ligne ?",
                    "options": ["No", "Yes"],
                },
                "validations": {"required": True},
            },
        ],
    }

    # Write template
    template_dir = Path(".github/ISSUE_TEMPLATE")
    template_dir.mkdir(parents=True, exist_ok=True)

    with open(template_dir / "event.yml", "w", encoding="utf-8") as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    generate_template()
