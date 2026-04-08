
import requests
import json
import os
import logging
from datetime import datetime, timezone

from modules.config_loader import config
from modules import path_manager
from modules.network_utils import retry

logger = logging.getLogger(__name__)

# Nowy endpoint Airly: measurements/location (po locationId zamiast lat/lng)
API_URL = "https://airapi.airly.eu/v2/measurements/location"


def get_mock_data():
    """Zwraca dane zastępcze w przypadku błędu."""
    logger.warning("Używam zastępczych danych Airly.")
    return {
        "current": {
            "values": [],
            "indexes": [{"name": "AIRLY_CAQI", "value": 0, "level": "UNKNOWN", "description": "Brak danych"}],
            "standards": []
        }
    }


@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=10, backoff=2, logger=logger)
def _fetch_airly_data(verbose_mode=False):
    """Pobiera dane z API Airly z mechanizmem ponawiania prób."""
    airly_config = config['api_keys']
    api_key = airly_config.get('airly')
    location_id = airly_config.get('airly_location_id')

    if not api_key:
        logger.error("Brak skonfigurowanego klucza AIRLY_API_KEY w pliku config.yaml. Pomijam pobieranie danych Airly.")
        return None

    if not location_id:
        logger.error("Brak skonfigurowanego airly_location_id w pliku config.yaml -> api_keys. Pomijam pobieranie danych Airly.")
        return None

    headers = {'apikey': api_key, 'Accept-Language': 'pl'}
    params = {'locationId': location_id}

    logger.info(f"Pobieranie danych z API Airly ({API_URL}) dla locationId={location_id}")
    response = requests.get(API_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    json_data = response.json()
    if verbose_mode:
        logger.debug(f"Pobrana odpowiedź JSON z Airly: {json.dumps(json_data, ensure_ascii=False)}")
    return json_data


def update_airly_data(verbose_mode=False):
    """
    Pobiera dane o jakości powietrza z API Airly (endpoint /location).
    W przypadku błędu, aplikacja będzie korzystać z ostatnich pomyślnie pobranych danych.
    """
    file_path = os.path.join(path_manager.CACHE_DIR, 'airly.json')

    try:
        airly_data = _fetch_airly_data(verbose_mode)

        if airly_data:
            airly_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(airly_data, f, ensure_ascii=False, indent=4)
            logger.info("Pomyślnie zaktualizowano i zapisano dane Airly.")
        else:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(get_mock_data(), f, ensure_ascii=False, indent=4)

    except requests.exceptions.RequestException as e:
        logger.warning(f"Błąd sieci podczas pobierania danych Airly: {e}. Aplikacja użyje danych z pamięci podręcznej.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd w module Airly: {e}. Aplikacja użyje danych z pamięci podręcznej.", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_airly_data()
