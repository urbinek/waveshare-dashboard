import requests
import json
import os
import logging
from datetime import datetime, timezone

from modules.config_loader import config
from modules import path_manager
from modules.network_utils import retry

logger = logging.getLogger(__name__)

API_BASE_URL = "https://danepubliczne.imgw.pl/api/data/meteo/id"


def _get_station_id():
    """Pobiera ID stacji IMGW z konfiguracji."""
    return config.get('location', {}).get('imgw_station_id')


@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=10, backoff=2, logger=logger)
def _fetch_imgw_data(station_id, verbose_mode=False):
    """Pobiera dane z API IMGW-PIB dla podanej stacji."""
    url = f"{API_BASE_URL}/{station_id}"
    logger.info(f"Pobieranie danych z API IMGW: {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    json_data = response.json()
    if verbose_mode:
        logger.debug(f"Pobrana odpowiedź JSON z IMGW: {json.dumps(json_data, ensure_ascii=False)}")
    return json_data


def update_imgw_data(verbose_mode=False):
    """
    Pobiera dane meteorologiczne z API IMGW-PIB i zapisuje do cache.
    Dostarcza temperaturę powietrza ze stacji pomiarowej.
    """
    station_id = _get_station_id()
    if not station_id:
        logger.error("Brak skonfigurowanego imgw_station_id w config.yaml -> location. Pomijam pobieranie danych IMGW.")
        return

    file_path = os.path.join(path_manager.CACHE_DIR, 'imgw.json')

    try:
        raw_data = _fetch_imgw_data(station_id, verbose_mode)

        # API zwraca listę stacji – bierzemy pierwszą
        if isinstance(raw_data, list):
            if not raw_data:
                logger.warning("API IMGW zwróciło pustą listę stacji.")
                return
            station_data = raw_data[0]
        else:
            station_data = raw_data

        def _safe_float(val):
            try:
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        result = {
            "station_name": station_data.get("nazwa_stacji", "NIEZNANA"),
            "station_id": station_data.get("kod_stacji"),
            "temp_air": _safe_float(station_data.get("temperatura_powietrza")),
            "temp_ground": _safe_float(station_data.get("temperatura_gruntu")),
            "wind_direction": _safe_float(station_data.get("wiatr_kierunek")),
            "wind_speed": _safe_float(station_data.get("wiatr_srednia_predkosc")),
            "wind_gust": _safe_float(station_data.get("wiatr_predkosc_maksymalna")),
            "humidity": _safe_float(station_data.get("wilgotnosc_wzgledna")),
            "precipitation_10min": _safe_float(station_data.get("opad_10min")),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info(f"Pomyślnie zaktualizowano dane IMGW ze stacji: {result['station_name']}.")

    except requests.exceptions.RequestException as e:
        logger.warning(f"Błąd sieci podczas pobierania danych IMGW: {e}. Używam danych z cache.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd w module IMGW: {e}", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    update_imgw_data(verbose_mode=True)
