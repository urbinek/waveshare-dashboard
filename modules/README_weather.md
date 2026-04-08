# Moduł: Pogoda (Agregator)

Ten moduł (`weather.py`) pełni od teraz rolę agregatora — nie łączy się już bezpośrednio z żadnym zewnętrznym pojedynczym API (jak dawniej AccuWeather). Zamiast tego zespala zbiór danych pobranych lokalnie lub z dedykowanych małych skryptów dostarczających oddzielne wycinki parametrów meteo.

## Wymagane Komponenty do działania

Moduł ten oczekuje gotowych wyników wygenerowanych (w tle lub osobno z crona schedulera) z innych bibliotek peryferyjnych:

- **`imgw.py`**: Oczekiwane na bazową temperaturę powietrza z dokładnej stacji synoptycznej (np. z Katowic). Aktualizowane raz na godzinę. Zapotrzebowanie: `imgw_station_id`.
- **`zigbee2mqtt.py`**: Podaje surowe dane bezpośrednio dla własnego wew/zewn sensora. Konieczny MQTT oraz wpis w konfiguracji (pamiętaj o odpowiednim `topic_outdoor`).
- **`open_meteo.py`**: Generuje stan ikony pogodowej (zachmurzenie) używając szerokości i długości geograficznej poprzez bezpłatne API Open-Meteo. Określa również kody opisowe z biblioteki WMO World Meteorological Organization.
- **`airly.py`**: Koncentrator smogu odpowiadający za indeks CAQI, wilgotność oraz ciśnienie.

## Wyciąg zasobów

Ikony WMO renderowane przez Open-Meteo wykorzystują bazę znaków z katalogu `assets/icons/feather`. Są dopasowane automatycznie wg czasu Wschodu i Zachodu Słońca. Moduł kalibruje nazwy słońca dzięki bibliotece `astral`.

## Odporność na Błędy 

Agregator jest wysoce niewrażliwy na braki sieciowe:
- W razie awarii chmury (Airly padnie), `weather.py` nadal zaprezentuje temperaturę pobraną z Twojego fizycznego czujnika przy oknie (MQTT). Pliki stanu zachowuje niezależnie dla poszczególnych zmiennych.
- Ostrzeżenie `--` zostaje użyte jedynie dla braku pre-cache (np. pustego JSON z poprzedniej sesji rano przy restarcie modułu systemowego) bez połączenia MQTT.
