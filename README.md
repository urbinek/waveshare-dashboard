# Waveshare E-Paper Dashboard

Spersonalizowany, dwukolorowy (czarno-biały z odcieniami szarości) dashboard dla 7.5-calowego wyświetlacza e-papierowego Waveshare (model WB), zaprojektowany do działania na Raspberry Pi. Aplikacja integruje dane z wielu źródeł, aby stworzyć użyteczny i estetyczny ekran informacyjny.

<!-- TODO: Wstaw zrzut ekranu -->

---

## Funkcjonalności

- **Panel Czasu**: Wyświetla aktualną godzinę, datę, dzień tygodnia oraz godziny wschodu i zachodu słońca.
- **Panel Pogody**: Pokazuje aktualne warunki pogodowe (dwie temperatury: lokalna z własnego czujnika IoT oraz referencyjna z najbliższej stacji IMGW), ikony bazujące na bezpłatnym Open-Meteo oraz dane o środowisku z Airly.
- **Wskaźnik Nieaktualnych Danych**: Jeśli dane (np. pogodowe) nie mogą zostać odświeżone z powodu braku internetu, aplikacja wyświetli ostatnie znane dane wraz z ikoną ostrzegawczą.
- **Panel Wydarzeń**: Listuje nadchodzące wydarzenia z Twojego osobistego Kalendarza Google.
- **Panel Kalendarza**: Przedstawia widok całego miesiąca z zaznaczonymi weekendami, świętami państwowymi oraz dniami, w których masz zaplanowane wydarzenia.
- **Nietypowe Święta**: Codziennie wyświetla jedno nietypowe święto z kalendarza "Days of the Year".
- **Ochrona Wyświetlacza**:
  - **Pixel Shift**: Co godzinę obraz jest subtelnie przesuwany o kilka pikseli, aby zapobiegać wypalaniu się ekranu.
  - **Głębokie Odświeżenie**: Codziennie o 3:00 w nocy następuje pełne, głębokie odświeżenie całego ekranu, co dodatkowo konserwuje wyświetlacz.
- **Elastyczność**: Możliwość uruchomienia z argumentami linii poleceń do debugowania i personalizacji.
- **Automatyzacja**: Pełna obsługa uruchamiania jako usługa `systemd` zapewnia automatyczny start i niezawodne działanie.

---

## Instalacja i Konfiguracja na Raspberry Pi

### Krok 1: Wymagania wstępne

Upewnij się, że masz zainstalowane `git` oraz środowisko Python. Włącz interfejsy SPI i I2C w `raspi-config`.

```bash
sudo apt-get update
sudo apt-get install git python3-pip python3-venv libopenjp2-7 libcairo2-dev -y
sudo raspi-config
# Wybierz 'Interface Options' -> 'SPI' -> 'Yes'
# Wybierz 'Interface Options' -> 'I2C' -> 'Yes'
```

### Krok 2: Klonowanie i instalacja zależności

```bash
git clone https://github.com/urbinek/waveshare-dashboard
cd waveshare-dashboard

# Utwórz i aktywuj wirtualne środowisko
python3 -m venv .venv
source .venv/bin/activate

# Zainstaluj wymagane biblioteki
# Dla najlepszej wydajności renderowania ikon, zalecane jest zainstalowanie `cairosvg`
pip install -r requirements.txt cairosvg
```

### Krok 3: Konfiguracja Aplikacji

Skopiuj plik konfiguracyjny i dostosuj go do swoich potrzeb.

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

#### a) Moduł Pogody, MQTT i Jakości Powietrza

W pliku konfiguracyjnym w sekcji `location`, `mqtt` i `api_keys` skonfigurujesz następujące wskaźniki:
- `imgw_station_id`: Identyfikator stacji synoptycznej IMGW (do pobierania oficjalnej temperatury w okolicy).
- `latitude` i `longitude`: Twoja szerokość i długość geograficzna potrzebna dla strefy czasowej, wschodów Słońca oraz Open-Meteo.
- Sekcja `mqtt`: Konfiguracja do brokera dla subskrypcji odczytów Twojego czujnika na zewnątrz (`topic_outdoor: "zigbee2mqtt//Outdoor"`). Aplikacja nieprzerwanie śledzi go w tle.
- Ustawienia `airly` i `airly_location_id`: Konieczne do widoczności zanieczyszczeń powietrza (CAQI) i wilgotności.

#### b) Moduł Kalendarza Google

#### c) Ustawienia Wyświetlacza

- `FLIP_DISPLAY`: Ustaw na `True`, jeśli chcesz, aby obraz na wyświetlaczu był domyślnie obrócony o 180 stopni. Jest to przydatne, jeśli obudowa lub ustawienie urządzenia wymaga odwróconej orientacji.

To najważniejszy krok konfiguracyjny dla wydarzeń. Musisz uzyskać klucze API od Google w postaci json.

#### d) Konfiguracja Layoutu

Plik `config.yaml` posiada sekcję `panels`, która pozwala na pełną kontrolę nad układem kafelków na ekranie bez potrzeby modyfikacji kodu. Możesz zmieniać ich pozycje, a także włączać je i wyłączać.

```yaml
panels:
  time:
    enabled: true
    rect: [0, 0, 400, 160]
    positional_adjustments:
      y: 10
  # ... inne panele
```

**Dostępne opcje dla każdego panelu:**

- `enabled`: Ustaw na `false`, aby całkowicie wyłączyć rysowanie danego panelu. Domyślnie `true`.
- `rect`: Definiuje prostokątny obszar panelu w formacie `[lewy_x, górny_y, prawy_x, dolny_y]`.
- `y_offset`: (Opcjonalne) Dodatkowe przesunięcie zawartości panelu w pionie.

1.  Przejdź do Google Cloud Console.
2.  Utwórz nowy projekt (np. "RaspberryPi Dashboard").
3.  W menu nawigacyjnym wybierz **APIs & Services -> Library**.
4.  Wyszukaj **"Google Calendar API"** i włącz je.
5.  Przejdź do **APIs & Services -> Credentials**.
6.  Kliknij **+ CREATE CREDENTIALS** i wybierz **OAuth client ID**.
7.  Jeśli zostaniesz poproszony, skonfiguruj "OAuth consent screen". Jako typ użytkownika wybierz **External** i podaj podstawowe dane (nazwa aplikacji, e-mail).
8.  W formularzu tworzenia Client ID wybierz **Application type: Desktop app**.
9.  Kliknij **CREATE**, a następnie **DOWNLOAD JSON**.
10. Zmień nazwę pobranego pliku na `credentials.json` i umieść go w głównym katalogu projektu (`waveshare-dashboard/`).

### Krok 4: Pierwsza autoryzacja Google

Po umieszczeniu pliku `credentials.json` musisz jednorazowo autoryzować aplikację.

```bash
# Upewnij się, że jesteś w aktywnym środowisku wirtualnym
source .venv/bin/activate

# Uruchom skrypt modułu kalendarza
python modules/google_calendar.py
```

W konsoli pojawi się link. Otwórz go w przeglądarce, zaloguj się na swoje konto Google i zezwól aplikacji na dostęp. Po pomyślnej autoryzacji w katalogu projektu zostanie utworzony plik `token.json`.

### Krok 5: Bezpieczeństwo poświadczeń

Pliki `credentials.json` i `token.json` zawierają poufne dane. **Nigdy nie umieszczaj ich w publicznym repozytorium!** Upewnij się, że są dodane do pliku `.gitignore`.

```bash
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
```

---

## Uruchomienie

Możesz uruchomić aplikację bezpośrednio z terminala.

```bash
source .venv/bin/activate
python main.py [ARGUMENTY]
```

### Dostępne argumenty:

- `--draw-borders`: Rysuje ramki wokół poszczególnych paneli, przydatne do debugowania layoutu.
- `--service`: Optymalizuje format logów do użycia z `systemd` (brak znacznika czasu).
- `--no-splash`: Pomija ekran powitalny przy starcie aplikacji.
- `--verbose`: Włącza szczegółowe logowanie na poziomie `DEBUG`.
- `--2137`: Wyświetla ukryty Easter Egg przy starcie.
- `--flip`: Obraca obraz o 180 stopni, nadpisując ustawienie `FLIP_DISPLAY` z pliku `config.py`.

---

## Uruchomienie jako usługa `systemd`

Aby aplikacja działała w tle i uruchamiała się automatycznie po starcie Raspberry Pi, skonfiguruj ją jako usługę `systemd`.

1.  Utwórz plik usługi:
    ```bash
    sudo nano /etc/systemd/system/waveshare-dashboard.service
    ```

2.  Wklej poniższą konfigurację, **pamiętając o zmianie ścieżek (`WorkingDirectory` i `ExecStart`)**, aby pasowały do Twojej instalacji:

    ```ini
    [Unit]
    Description=Waveshare E-Paper Dashboard
    After=network.target

    [Service]
    Type=simple
    User=pi # <-- ZMIEŃ NA SWOJĄ NAZWĘ UŻYTKOWNIKA
    WorkingDirectory=/home/pi/waveshare-dashboard # <-- ZMIEŃ NA PEŁNĄ ŚCIEŻKĘ DO PROJEKTU
    ExecStart=/home/pi/waveshare-dashboard/.venv/bin/python main.py --service
    Restart=on-failure
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    ```

3.  Przeładuj `systemd`, włącz i uruchom usługę:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable waveshare-dashboard.service
    sudo systemctl start waveshare-dashboard.service
    ```

4.  Aby sprawdzić status usługi i oglądać logi na żywo:

    ```bash
    sudo systemctl status waveshare-dashboard.service
    sudo journalctl -fu waveshare-dashboard.service
    ```

---

## Podziękowania i Zasoby

- **Wyświetlacz**: Projekt został stworzony dla wyświetlacza [Waveshare 7.5inch e-Paper HAT (WB)](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual).
- **Biblioteki**: Wykorzystano oficjalne biblioteki od Waveshare, dostępne na [GitHubie](https://github.com/waveshareteam/e-Paper).
- **Wsparcie AI**: Znaczna część kodu została napisana i zrefaktoryzowana przy pomocy asystenta kodowania Gemini.

---

## Struktura Projektu

- `main.py`: Główny plik aplikacji, zarządza harmonogramem i cyklem życia.
- `config.yaml`: Centralny plik konfiguracyjny.
- `modules/`: Zawiera logikę poszczególnych funkcjonalności.
  - `panels/`: Moduły odpowiedzialne za rysowanie konkretnych sekcji na ekranie.
  - Szczegółowe opisy modułów znajdziesz w dedykowanych plikach `README.md` wewnątrz tych katalogów.
