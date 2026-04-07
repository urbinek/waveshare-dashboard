
import datetime
import os.path
import json
import logging
import calendar
import socket
import ssl
from filelock import FileLock

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

if __name__ == '__main__' and __package__ is None:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.config_loader import config
from modules import path_manager
from modules.network_utils import retry

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
JSON_PATH = os.path.join(path_manager.CACHE_DIR, 'calendar.json')
LOCK_PATH = os.path.join(path_manager.CACHE_DIR, 'calendar.json.lock')
GCAL_CONFIG = config['google_calendar']

def get_google_creds():
    """Zarządza uwierzytelnianiem Google i zwraca obiekt credentials."""
    creds = None
    token_file = GCAL_CONFIG['token_file']
    creds_file = GCAL_CONFIG['credentials_file']

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Odświeżanie wygasłego tokenu Google...")
                creds.refresh(Request())
            except RefreshError as e:
                logger.warning(f"Nie udało się odświeżyć tokenu ({e}). Rozpoczynam ponowną autoryzację.")
                os.remove(token_file)
                creds = None
        if not creds:
            if not os.path.exists(creds_file):
                logger.critical(f"Brak pliku {creds_file}! Pobierz go z Google Cloud Console.")
                return None
            logger.info("Uruchamianie przepływu autoryzacji Google...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return creds

@retry(exceptions=(socket.timeout, ssl.SSLError, TransportError, ConnectionResetError, HttpError), tries=3, delay=10, backoff=2, logger=logger)
def _get_events(service, calendar_id, time_min, time_max=None, max_results=250, verbose_mode=False):
    """Pomocnicza funkcja do pobierania wydarzeń z określonego kalendarza."""
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        if verbose_mode:
            logger.debug(f"Pobrana odpowiedź JSON z Google Calendar dla {calendar_id}: {json.dumps(events_result, indent=4)}")
        return events_result.get('items', [])
    except HttpError as e:
        if e.resp.status == 404:
            logger.error(f"Nie znaleziono kalendarza o ID '{calendar_id}'. Sprawdź ID w config.yaml.")
        else:
            logger.error(f"Wystąpił błąd API ({e.resp.status}) podczas pobierania danych dla kalendarza {calendar_id}: {e}")
        return []

def _read_calendar_data():
    """Bezpiecznie odczytuje dane kalendarza z pliku JSON."""
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'upcoming_events': [], 'unusual_holiday': '', 'unusual_holiday_desc': '', 'month_calendar': [], 'event_dates': [], 'holiday_dates': []}

def _write_calendar_data(data):
    """Zapisuje dane kalendarza do pliku JSON."""
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def _update_json_data(update_dict):
    """Bezpiecznie aktualizuje plik JSON z danymi."""
    with FileLock(LOCK_PATH):
        data = _read_calendar_data()
        data.update(update_dict)
        _write_calendar_data(data)

def update_events(verbose_mode=False):
    """Pobiera i aktualizuje wydarzenia osobiste oraz święta."""
    logger.info("Aktualizowanie wydarzeń osobistych i świąt...")
    creds = get_google_creds()
    if not creds: return

    try:
        service = build('calendar', 'v3', credentials=creds)
        now_utc_iso = datetime.datetime.utcnow().isoformat() + 'Z'
        
        personal_events_raw = _get_events(service, GCAL_CONFIG['calendar_ids']['personal'], now_utc_iso, max_results=GCAL_CONFIG['max_upcoming_events'], verbose_mode=verbose_mode)
        holiday_events_raw = _get_events(service, GCAL_CONFIG['calendar_ids']['holidays'], now_utc_iso, max_results=GCAL_CONFIG['max_upcoming_events'], verbose_mode=verbose_mode)
        shared_events_raw = _get_events(service, GCAL_CONFIG['calendar_ids']['shared'], now_utc_iso, max_results=GCAL_CONFIG['max_upcoming_events'], verbose_mode=verbose_mode)

        all_events = []
        for event_raw in personal_events_raw + holiday_events_raw + shared_events_raw:
            start_info = event_raw.get('start')
            end_info = event_raw.get('end')
            if not start_info or not end_info:
                continue

            start_date_str = start_info.get('dateTime', start_info.get('date'))
            end_date_str = end_info.get('dateTime', end_info.get('date'))

            if not start_date_str or not end_date_str:
                continue

            start_dt = datetime.datetime.fromisoformat(start_date_str.split('T')[0])
            end_dt = datetime.datetime.fromisoformat(end_date_str.split('T')[0])

            # Google Calendar all-day events end at midnight of the next day, so adjust end_dt
            if 'date' in start_info and 'date' in end_info:
                end_dt -= datetime.timedelta(days=1)

            current_dt = start_dt
            now = datetime.datetime.now().date()
            while current_dt <= end_dt:
                if current_dt.date() >= now:
                    is_holiday_event = event_raw.get('organizer', {}).get('email') == GCAL_CONFIG['calendar_ids']['holidays']
                    all_events.append({
                        'summary': event_raw.get('summary', 'Brak tytułu'),
                        'start': current_dt.isoformat(),
                        'is_holiday': is_holiday_event,
                        'is_all_day': 'date' in start_info
                    })
                current_dt += datetime.timedelta(days=1)

        # Sort events by start time
        all_events.sort(key=lambda x: x['start'])
        
        upcoming_events = []
        event_dates = []
        for event in all_events[:GCAL_CONFIG['max_upcoming_events']]:
            upcoming_events.append(event)
            event_dates.append(datetime.datetime.fromisoformat(event['start'].split('T')[0]).date().isoformat())

        _update_json_data({
            'upcoming_events': upcoming_events,
            'event_dates': event_dates
        })
        logger.info("Zakończono aktualizację wydarzeń osobistych i świąt.")
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji wydarzeń osobistych i świąt: {e}", exc_info=True)

def update_holidays(verbose_mode=False):
    """Pobiera i aktualizuje tylko dane o świętach (raz dziennie)."""
    logger.info("Aktualizowanie danych o świętach...")
    creds = get_google_creds()
    if not creds: return

    try:
        service = build('calendar', 'v3', credentials=creds)
        today_local = datetime.date.today()
        start_of_month = today_local.replace(day=1)
        _, num_days = calendar.monthrange(start_of_month.year, start_of_month.month)
        end_of_month = start_of_month.replace(day=num_days)

        time_min_month_utc = datetime.datetime.combine(start_of_month, datetime.time.min).isoformat() + 'Z'
        time_max_month_utc = datetime.datetime.combine(end_of_month, datetime.time.max).isoformat() + 'Z'

        polish_holidays_raw = _get_events(service, GCAL_CONFIG['calendar_ids']['holidays'], time_min_month_utc, time_max_month_utc, verbose_mode=verbose_mode)
        holiday_dates = [event['start']['date'] for event in polish_holidays_raw if 'date' in event['start']]

        today_start_utc = datetime.datetime.combine(today_local, datetime.time.min).isoformat() + 'Z'
        today_end_utc = datetime.datetime.combine(today_local, datetime.time.max).isoformat() + 'Z'
        unusual_holidays_today_raw = _get_events(
            service,
            GCAL_CONFIG['calendar_ids']['unusual'],
            time_min=today_start_utc,
            time_max=today_end_utc,
            max_results=5,
            verbose_mode=verbose_mode
        )

        unusual_holiday_title = 'Brak nietypowych świąt dzisiaj.'
        unusual_holiday_desc = ''
        if unusual_holidays_today_raw:
            first_event = unusual_holidays_today_raw[0]
            unusual_holiday_title = first_event.get('summary', 'Brak tytułu')
            description = first_event.get('description')
            if description:
                if '•' in description:
                    unusual_holiday_desc = description.split('•')[0].strip()
                else:
                    unusual_holiday_desc = description.splitlines()[0].strip()

        _update_json_data({
            'holiday_dates': holiday_dates,
            'unusual_holiday': unusual_holiday_title,
            'unusual_holiday_desc': unusual_holiday_desc
        })
        logger.info("Zakończono aktualizację danych o świętach.")
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji świąt: {e}", exc_info=True)

def build_calendar_grid():
    """Generuje siatkę kalendarza na podstawie danych z pliku JSON."""
    logger.info("Budowanie siatki kalendarza...")
    with FileLock(LOCK_PATH):
        data = _read_calendar_data()
        holiday_dates_set = {datetime.date.fromisoformat(d) for d in data.get('holiday_dates', [])}
        event_dates_set = {datetime.date.fromisoformat(d) for d in data.get('event_dates', [])}
        today_local = datetime.date.today()
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(today_local.year, today_local.month)
        month_calendar = []
        for week in month_days:
            week_list = []
            for day_date in week:
                week_list.append({
                    "day": day_date.day,
                    "date": day_date.isoformat(),
                    "is_today": day_date == today_local,
                    "is_weekend": day_date.weekday() >= 5,
                    "is_holiday": day_date in holiday_dates_set,
                    "has_event": day_date in event_dates_set,
                    "is_current_month": day_date.month == today_local.month
                })
            month_calendar.append(week_list)
        data['month_calendar'] = month_calendar
        _write_calendar_data(data)
    logger.info("Zakończono budowanie siatki kalendarza.")

def update_calendar_data(verbose_mode=False):
    """Uruchamia pełną aktualizację wszystkich danych kalendarza."""
    logger.info("Uruchamianie pełnej aktualizacji danych kalendarza...")
    try:
        update_holidays(verbose_mode)
        update_events(verbose_mode)
        build_calendar_grid()
    except (socket.timeout, ssl.SSLError, TransportError, ConnectionResetError, HttpError) as e:
        logger.warning(f"Błąd sieci podczas aktualizacji danych kalendarza: {e}.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd w module kalendarza: {e}.", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Uruchamianie modułu kalendarza w celu autoryzacji i wstępnej synchronizacji...")
    update_calendar_data()
    logger.info("Autoryzacja i synchronizacja zakończona.")
