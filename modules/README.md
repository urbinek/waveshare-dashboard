# Moduły Aplikacji

Ten katalog zawiera kluczowe moduły logiczne aplikacji, które są odpowiedzialne za zbieranie i przetwarzanie danych.

## Główne Moduły

- `weather.py`: Główny agregator danych pogodowych z lokalnych i zewnętrznych źródeł. Szczegółowy opis w `README_weather.md`.
- `google_calendar.py`: Zarządza interakcją z API Kalendarza Google. Szczegółowy opis w `README_google_calendar.md`.
- `time.py`: Moduł odpowiedzialny za lokalny czas i datę.
- `display.py`: Główny kontroler EPD, który zarządza odświeżaniem, przesunięciem pikseli (pixel shift) oraz nakłada panele graficzne.
- `drawing_utils.py`: Zestaw funkcji pomocniczych do operacji na czcionkach oraz obsługi obrazów SVG i kształtów bazowych.
- `imgw.py`: Pobiera dane wprost ze stacji synoptycznej IMGW-PIB publicznego wydawcy meteo (PL).
- `open_meteo.py`: Transformuje lokalizację we współrzędne dla darmowego serwera, dając kody opisu pogody WMO.
- `airly.py`: Odpytuje dany sensor czystości powietrza i parsuje metryki smogu (CAQI).
- `zigbee2mqtt.py`: Klient nasłuchujący brokera MQTT pracujący w tle, dla ciągłych odczytów termicznych.
