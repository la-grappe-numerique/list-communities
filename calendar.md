<!-- CSS de FullCalendar -->
<link href='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.11.5/main.min.css' rel='stylesheet' />

<!-- Script de FullCalendar -->
<script src='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.11.5/main.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.11.5/locales/fr.min.js'></script>

<!-- Style pour le conteneur du calendrier -->
<style>
  #calendar {
    margin: 20px auto;
    max-width: 1200px;
    background-color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
  .fc-event {
    cursor: pointer;
  }
  .fc-event-title {
    font-weight: bold;
  }
</style>

<!-- Conteneur pour le calendrier -->
<div id="calendar"></div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Fonction pour charger les événements
  async function loadEvents() {
    try {
      const response = await fetch('events.yml');
      const yamlText = await response.text();
      const events = jsyaml.load(yamlText);
      
      return events.map(event => ({
        title: event.title,
        start: event.date,
        url: event.url,
        extendedProps: {
          community: event.community,
          location: event.location,
          isOnline: event.is_online
        },
        backgroundColor: getEventColor(event.community)
      }));
    } catch (error) {
      console.error('Erreur lors du chargement des événements:', error);
      return [];
    }
  }

  // Fonction pour générer une couleur unique par communauté
  function getEventColor(community) {
    // Générer une couleur basée sur le hash de la communauté
    let hash = 0;
    for (let i = 0; i < community.length; i++) {
      hash = community.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 70%, 50%)`;
  }

  // Initialisation du calendrier
  const calendarEl = document.getElementById('calendar');
  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,listMonth'
    },
    locale: 'fr',
    firstDay: 1,
    navLinks: true,
    eventTimeFormat: {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    },
    eventClick: function(info) {
      // Empêcher la navigation par défaut
      info.jsEvent.preventDefault();
      
      // Afficher une popup avec les détails
      const event = info.event;
      const props = event.extendedProps;
      
      alert(`
        ${event.title}
        📅 ${new Date(event.start).toLocaleString('fr-FR')}
        🏢 ${props.community}
        📍 ${props.location}
        ${props.isOnline ? '💻 Événement en ligne' : ''}
        
        🔗 ${event.url}
      `);
    },
    events: loadEvents
  });

  // Rendu du calendrier
  calendar.render();
});
</script>
