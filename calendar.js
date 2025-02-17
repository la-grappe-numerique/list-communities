// Format date and time for display
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

// Create Google Maps link from location
function createGoogleMapsLink(location) {
    if (!location) return null;
    const encodedLocation = encodeURIComponent(location);
    return `https://www.google.com/maps/search/?api=1&query=${encodedLocation}`;
}

// Create community link with proper base URL handling
function createCommunityLink(community) {
    if (!community) return null;
    const baseUrl = getBaseUrl();
    return `${baseUrl}${community}/`;
}

// Get the base URL depending on environment (Docsify vs standard)
function getBaseUrl() {
    if (window.$docsify) {
        const basePath = window.location.pathname.replace(/\/$/, '');
        const baseHash = '#/';
        return `${basePath}${baseHash}`;
    }
    return window.location.pathname.replace(/\/$/, '') + '/';
}

// Format communities array or single community for display
function formatCommunities(extendedProps) {
    if (!extendedProps) return 'N/A';

    // Handle array of communities
    if (extendedProps.communities && Array.isArray(extendedProps.communities)) {
        return extendedProps.communities.map(community => {
            const communityLink = createCommunityLink(community);
            return communityLink 
                ? `<a href="${communityLink}">${community}</a>`
                : community;
        }).join(' & ');
    }

    // Fallback for single community (backward compatibility)
    const community = extendedProps.community || 'N/A';
    const communityLink = createCommunityLink(community);
    return communityLink 
        ? `<a href="${communityLink}">${community}</a>`
        : community;
}

// Create popover content with event details
function createPopoverContent(event) {
    const mapsLink = createGoogleMapsLink(event.extendedProps.location);

    return `
        <div class="event-details">
            <div class="event-title">${event.title}</div>
            <div class="event-info">
                <i class="bi bi-calendar"></i> ${formatDateTime(event.start)}
            </div>
            <div class="event-info">
                <i class="bi bi-people"></i> Community(ies): ${formatCommunities(event.extendedProps)}
            </div>
            <div class="event-info">
                <i class="bi bi-geo-alt"></i> Location: ${
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

// Get initial view based on screen size
function getInitialView() {
    return window.innerWidth < 768 ? 'listMonth' : 'dayGridMonth';
}

// Initialize and load the calendar
function loadCalendar() {
    const calendarEl = document.getElementById('calendar');
    let currentPopover = null;
    
    const calendar = new FullCalendar.Calendar(calendarEl, {
        themeSystem: 'bootstrap5',
        initialView: getInitialView(),
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth'
        },
        locale: 'fr',
        height: 'auto',
        firstDay: 1,
        // Handle responsive view changes
        windowResize: function(arg) {
            const newView = window.innerWidth < 768 ? 'listMonth' : 'dayGridMonth';
            calendar.changeView(newView);
        },
        // Setup event popovers
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

    // Close popover when clicking outside
    document.addEventListener('click', function(e) {
        if (currentPopover && !e.target.closest('.fc-event') && !e.target.closest('.popover')) {
            currentPopover.hide();
            currentPopover = null;
        }
    });

    // Load events from JSON file
    fetch('events.json')
        .then(response => response.json())
        .then(events => {
            const formattedEvents = events.map(event => ({
                title: event.title,
                start: event.date,
                url: event.url || null,
                extendedProps: {
                    communities: event.communities || [event.community],
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