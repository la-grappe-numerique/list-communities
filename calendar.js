// Fonction pour formater la date et l'heure
function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('fr-FR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Fonction pour créer le lien Google Maps
function createGoogleMapsLink(location) {
    if (!location) return null;
    const encodedLocation = encodeURIComponent(location);
    return `https://www.google.com/maps/search/?api=1&query=${encodedLocation}`;
}

// Fonction pour créer le lien de la communauté
function createCommunityLink(community) {
    if (!community) return null;
    return `./${community}/`;
}

// Fonction pour créer le contenu du popover
function createPopoverContent(event) {
    const communityLink = createCommunityLink(event.extendedProps.community);
    const mapsLink = createGoogleMapsLink(event.extendedProps.location);

    return `
        <div class="event-details">
            <div class="event-title">${event.title}</div>
            <div class="event-info">
                <i class="bi bi-calendar"></i> ${formatDateTime(event.start)}
            </div>
            <div class="event-info">
                <i class="bi bi-people"></i> Communauté: ${
                    communityLink 
                    ? `<a href="${communityLink}">${event.extendedProps.community}</a>`
                    : event.extendedProps.community || 'N/A'
                }
            </div>
            <div class="event-info">
                <i class="bi bi-geo-alt"></i> Lieu: ${
                    mapsLink && event.extendedProps.location
                    ? `<a href="${mapsLink}" class="location-link" target="_blank">${event.extendedProps.location}</a>`
                    : event.extendedProps.location || 'N/A'
                }
            </div>
            ${event.url ? `
                <a href="${event.url}" class="event-link" target="_blank">
                    <i class="bi bi-calendar-check"></i> S'inscrire à l'événement
                </a>
            ` : ''}
        </div>
    `;
}

function loadCalendar() {
    const calendarEl = document.getElementById('calendar');
    let currentPopover = null;
    
    const calendar = new FullCalendar.Calendar(calendarEl, {
        themeSystem: 'bootstrap5',
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth'
        },
        locale: 'fr',
        height: 'auto',
        firstDay: 1,
        eventDidMount: function(info) {
            const popover = new bootstrap.Popover(info.el, {
                title: info.event.title,
                content: createPopoverContent(info.event),
                html: true,
                trigger: 'click',
                placement: 'auto',
                container: 'body',
                customClass: 'event-popover'
            });

            info.el.addEventListener('click', function(e) {
                e.preventDefault();
                if (currentPopover && currentPopover !== popover) {
                    currentPopover.hide();
                }
                currentPopover = popover;
            });
        },
        eventClick: function(info) {
            info.jsEvent.preventDefault();
        }
    });

    // Fermer le popover en cliquant ailleurs
    document.addEventListener('click', function(e) {
        if (currentPopover && !e.target.closest('.fc-event') && !e.target.closest('.popover')) {
            currentPopover.hide();
            currentPopover = null;
        }
    });

    // Chargement des événements depuis le fichier JSON
    fetch('events.json')
        .then(response => response.json())
        .then(events => {
            const formattedEvents = events.map(event => ({
                title: event.title,
                start: event.date,
                url: event.url || null,
                extendedProps: {
                    community: event.community || '',
                    location: event.location || ''
                }
            }));

            calendar.addEventSource({
                events: formattedEvents
            });

            calendar.render();
        })
        .catch(error => {
            console.error('Error fetching events:', error);
            calendarEl.innerHTML = 'Erreur lors du chargement du calendrier';
        });
}