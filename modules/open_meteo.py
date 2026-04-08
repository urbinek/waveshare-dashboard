import requests
import json
import os
import logging
from datetime import datetime, timezone

from modules.config_loader import config
from modules import path_manager
from modules.network_utils import retry

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"

# Mapowanie kodów WMO na ikony Feather SVG
# https://open-meteo.com/en/docs
WMO_ICON_MAP = {
    0: 'sun',              # Clear sky
    1: 'sun',              # Mainly clear
    2: 'cloud',            # Partly cloudy
    3: 'cloud',            # Overcast
    45: 'cloud-off',       # Fog
    48: 'cloud-off',       # Depositing rime fog
    51: 'cloud-drizzle',   # Drizzle: Light
    53: 'cloud-drizzle',   # Drizzle: Moderate
    55: 'cloud-drizzle',   # Drizzle: Dense
    56: 'cloud-drizzle',   # Freezing Drizzle: Light
    57: 'cloud-drizzle',   # Freezing Drizzle: Dense
    61: 'cloud-rain',      # Rain: Slight
    63: 'cloud-rain',      # Rain: Moderate
    65: 'cloud-rain',      # Rain: Heavy
    66: 'cloud-rain',      # Freezing Rain: Light
    67: 'cloud-rain',      # Freezing Rain: Heavy
    71: 'cloud-snow',      # Snow: Slight
    73: 'cloud-snow',      # Snow: Moderate
    75: 'cloud-snow',      # Snow: Heavy
    77: 'cloud-snow',      # Snow grains
    80: 'cloud-rain',      # Rain showers: Slight
    81: 'cloud-rain',      # Rain showers: Moderate
    82: 'cloud-rain',      # Rain showers: Violent
    85: 'cloud-snow',      # Snow showers: Slight
    86: 'cloud-snow',      # Snow showers: Heavy
    95: 'cloud-lightning',  # Thunderstorm: Slight or moderate
    96: 'cloud-lightning',  # Thunderstorm with slight hail
    99: 'cloud-lightning',  # Thunderstorm with heavy hail
}

# Czytelne opisy WMO (po polsku)
WMO_DESCRIPTIONS = {
    0: 'Bezchmurnie',
    1: 'Prawie bezchmurnie',
    2: 'Częściowe zachmurzenie',
    3: 'Zachmurzenie całkowite',
    45: 'Mgła',
    48: 'Mgła z gołoledzią',
    51: 'Mżawka lekka',
    53: 'Mżawka umiarkowana',
    55: 'Mżawka gęsta',
    56: 'Marznąca mżawka lekka',
    57: 'Marznąca mżawka gęsta',
    61: 'Deszcz lekki',
    63: 'Deszcz umiarkowany',
    65: 'Deszcz silny',
    66: 'Marznący deszcz lekki',
    67: 'Marznący deszcz silny',
    71: 'Śnieg lekki',
    73: 'Śnieg umiarkowany',
    75: 'Śnieg obfity',
    77: 'Ziarnistości śniegu',
    80: 'Przelotny deszcz lekki',
    81: 'Przelotny deszcz umiarkowany',
    82: 'Przelotny deszcz gwałtowny',
    85: 'Przelotny śnieg lekki',
    86: 'Przelotny śnieg obfity',
    95: 'Burza',
    96: 'Burza z gradem',
    99: 'Burza z silnym gradem',
}


@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=10, backoff=2, logger=logger)
def _fetch_open_meteo_data(verbose_mode=False):
    """Pobiera aktualne warunki pogodowe z Open-Meteo API (bezpłatne, bez klucza)."""
    location_cfg = config.get('location', {})
    lat = location_cfg.get('latitude')
    lon = location_cfg.get('longitude')

    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'weather_code',
        'timezone': 'Europe/Warsaw',
        'forecast_days': 1,
    }

    logger.info(f"Pobieranie danych z Open-Meteo API dla lokalizacji: lat={lat}, lon={lon}")
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if verbose_mode:
        logger.debug(f"Pobrana odpowiedź JSON z Open-Meteo: {json.dumps(data, ensure_ascii=False)}")
    return data


def _get_icon_path(weather_code):
    """Zwraca ścieżkę do ikony Feather SVG dla kodu WMO."""
    from modules import asset_manager
    if weather_code is None:
        return asset_manager.get_path('icon_sync_problem')
    icon_name = WMO_ICON_MAP.get(weather_code, 'cloud')
    icons_path = asset_manager.get_path('icons_feather_path')
    return os.path.join(icons_path, f'{icon_name}.svg')


def update_open_meteo_data(verbose_mode=False):
    """
    Pobiera dane pogodowe (kod WMO) z Open-Meteo i zapisuje do cache.
    Open-Meteo jest bezpłatne, bez rejestracji i bez klucza API.
    """
    file_path = os.path.join(path_manager.CACHE_DIR, 'open_meteo.json')

    try:
        raw_data = _fetch_open_meteo_data(verbose_mode)
        current = raw_data.get('current', {})
        weather_code = current.get('weather_code')

        result = {
            "weather_code": weather_code,
            "icon_name": WMO_ICON_MAP.get(weather_code, 'cloud'),
            "icon_path": _get_icon_path(weather_code),
            "description": WMO_DESCRIPTIONS.get(weather_code, 'Nieznane warunki'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info(f"Pomyślnie zaktualizowano dane Open-Meteo. Kod WMO: {weather_code} ({result['description']}).")

    except requests.exceptions.RequestException as e:
        logger.warning(f"Błąd sieci podczas pobierania danych Open-Meteo: {e}. Używam danych z cache.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd w module Open-Meteo: {e}", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    update_open_meteo_data(verbose_mode=True)
