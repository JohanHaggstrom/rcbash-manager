# RCBash Manager — Dokumentation

Timing- och resultathanteringssystem för RC-tävlingar i skala 1/5 ("bash"). Läser tider från RaceLogic timing-hårdvara via USB, hanterar hela tävlingsflödet från kvalificering till final, och beräknar poängställning automatiskt.

---

## Innehåll

1. [Översikt](#1-översikt)
2. [Installation](#2-installation)
3. [Konfiguration](#3-konfiguration)
4. [Tävlingsflöde](#4-tävlingsflöde)
5. [Batch-filer (snabbreferens)](#5-batch-filer-snabbreferens)
6. [Python-moduler](#6-python-moduler)
7. [Datamodell och lagring](#7-datamodell-och-lagring)
8. [Poängberäkning](#8-poängberäkning)
9. [Algoritmer för startlistor](#9-algoritmer-för-startlistor)
10. [Tekniska detaljer och kända begränsningar](#10-tekniska-detaljer-och-kända-begränsningar)

---

## 1. Översikt

Systemet är en fristående Python-applikation som styrs via Windows-batch-filer. Det är designat för en tävlingsdag uppdelad i fem omgångar (heats):

```
Kval  →  Åttondelsfinal  →  Kvartsfinal  →  Semifinal  →  Final
```

Tre RC-klasser stöds: **2WD**, **SC**, **4WD**. Varje klass delas i upp till tre nivågrupper: **A** (snabbast), **B**, **C**.

**Datakälla**: RaceLogic timing-system exporterar varje race som en HTML-fil till ett USB-minne. Systemet läser senaste filen, parsar tider och varv, matchar mot startlistan och sparar resultatet.

**Datalagring**: All data för en tävlingsdag sparas som JSON i `%USERPROFILE%/RCBashResults/YYMMDD.json`.

**Användargränssnitt**: CLI. Resultat- och startlistetexter kopieras automatiskt till Windows-urklipp så de kan klistras in i chat, streaming-overlay eller liknande.

---

## 2. Installation

Kräver Python 3.7+ med `py`-launchern tillgänglig på PATH.

Kör en gång innan första tävlingen:

```
scripts\KörDettaInnanFörstaStart.bat
```

Detta installerar pip-beroenden:

- `numpy` — används för poängberäkning (drop-worst-race)
- `clipboard` — kopierar text till urklipp

---

## 3. Konfiguration

### `racelogic/settings.json`

```json
{
  "drive": "E:",
  "max_participants": 9
}
```

| Nyckel | Beskrivning |
|---|---|
| `drive` | Monteringspunkt för USB-minne där RaceLogic skriver HTML-filer |
| `max_participants` | Max antal förare per grupp i Final |

### `racelogic/names.py`

Statisk uppslagstabell `NAMES = {nummer: "Förnamn Efternamn"}` med förarnummer i intervallet 10–99. Lägg till nya förare här innan tävling. Tomma slots representeras med strängliteral av numret, t.ex. `14: "14"`.

---

## 4. Tävlingsflöde

Hela tävlingsdagen körs genom följande sekvens av batch-filer från `scripts/`-mappen.

### Steg 0 — Förbered tävlingsdagen

```
StartaNyDeltävling.bat
```

- Skapar en ny `Raceday` för dagens datum.
- Frågar interaktivt efter deltagarnummer per klass och grupp.
- Genererar startlistor för **Kval**.
- Om en tävling redan startats idag frågar systemet om den ska skrivas över.

### Steg 1 — Kör en omgång (upprepas per klass/grupp)

```
StartaNästaHeat.bat            # Visar nästa race + startlista (för speaker/marshal)
[Förarna kör racet i timing-systemet]
RegistreraResultat.bat          # Läser senaste HTML från USB och sparar resultatet
VisaSenasteResultatet.bat       # Visar resultatet med medaljer, varvtider, totaltid
```

Vid problem med USB-läsning eller HTML-parsning, använd:

```
RegistreraResultatManuellt.bat  # Mata in placeringar manuellt i terminalen
```

### Steg 2 — Generera nästa omgångs startlistor

När alla heat i en omgång är registrerade:

```
StartaNästaOmgång.bat
```

- Verifierar att alla heat i nuvarande omgång är klara.
- Beräknar nya startlistor enligt algoritm för respektive omgång (se [§9](#9-algoritmer-för-startlistor)).
- Sparar och visar nya startlistorna.

### Steg 3 — Upprepa till och med Final

Stegen 1–2 upprepas för Åttondelsfinal, Kvartsfinal, Semifinal och Final. Final-omgången använder en annan algoritm: startlistorna baseras på total poäng från alla tidigare omgångar, inte på senaste omgångens placering.

### Hjälpkommandon (kan köras när som helst)

| Batch-fil | Funktion |
|---|---|
| `VisaNuvarandeOmgång.bat` | Visar startlistor för pågående omgång |
| `VisaNuvarandePoängställning.bat` | Visar aktuell poängställning |
| `VisaNuvarandePoängställningMedExtraDetaljer.bat` | Som ovan, men med poäng per omgång |

---

## 5. Batch-filer (snabbreferens)

Alla batch-filer är tunna omslag som kör `py ../racelogic/resultcalculation.py <flagga>` följt av `pause`.

| Batch-fil | Flagga | Beskrivning |
|---|---|---|
| `KörDettaInnanFörstaStart.bat` | (pip) | Engångsinstallation av Python-beroenden |
| `StartaNyDeltävling.bat` | `-s` | Starta ny tävlingsdag, registrera deltagare |
| `StartaNästaHeat.bat` | `-g` | Visa vilket race som ska köras härnäst |
| `RegistreraResultat.bat` | `-r` | Läs HTML från USB, registrera resultat |
| `RegistreraResultatManuellt.bat` | `-r -m` | Manuell inmatning av resultat |
| `StartaNästaOmgång.bat` | `-n` | Generera startlistor för nästa omgång |
| `VisaNuvarandeOmgång.bat` | `-l` | Visa nuvarande omgångs startlistor |
| `VisaSenasteResultatet.bat` | `-d` | Visa senaste resultatet |
| `VisaNuvarandePoängställning.bat` | `-o` | Visa aktuell poängställning |
| `VisaNuvarandePoängställningMedExtraDetaljer.bat` | `-o -v` | Poängställning med per-omgång-detaljer |

Övriga CLI-flaggor (kan köras direkt om man vill):

- `-d -p` — välj specifikt heat att visa
- `-e <nummer>` — exkludera förare från resultat (t.ex. DNS)

---

## 6. Python-moduler

Alla moduler ligger i `racelogic/`.

### `resultcalculation.py` — Huvudapplikation

CLI-driven workflow-motor. Tolkar flaggor med `argparse` och dispatchar till rätt funktion.

Centrala funktioner:

| Funktion | Roll |
|---|---|
| `create_qualifiers()` | Steg 0 — Skapar tävlingsdag och Kval-startlistor |
| `add_new_result()` | Steg 1 — Läser HTML, matchar mot startlista, sparar resultat |
| `add_new_result_manually()` | Manuell variant av ovan |
| `start_new_race_round()` | Steg 2 — Genererar nästa omgångs startlistor |
| `_create_start_list_from_qualifiers()` | Algoritm efter Kval |
| `_create_start_list_intermediate_races()` | Algoritm mellan Åttondel/Kvart/Semi |
| `_create_start_lists_for_finals()` | Algoritm till Final (poängbaserad) |
| `_calculate_cup_points()` | Beräknar poäng för en hel tävlingsdag |
| `calculate_season_points()` | Aggregerar poäng över flera tävlingsdagar (drop worst race) |
| `show_current_points()` | Visar poängställning |

### `raceday.py` — Datamodell

Definierar dataklasserna och hanterar serialisering till/från JSON.

| Klass | Beskrivning |
|---|---|
| `Driver` | Förare. Wrapper runt nummer, slår upp namn från `NAMES`. Hashbar. |
| `HeatStartLists` | Startlistor för en omgång inom en klass: `{grupp: [Driver]}` |
| `RaceResult` | Resultat för en grupp: positions, varv, totaltid, bästa varv, snittvarv, DNS-flaggor |
| `Raceday` | Hela tävlingsdagen: deltagare, startlistor, resultat, current_heat-index |

Konstanter för omgångsnamn (svenska): `"Kval"`, `"Åttondelsfinal"`, `"Kvartsfinal"`, `"Semifinal"`, `"Final"`.

Persistering:

- `get_raceday()` — laddar dagens tävlingsdag
- `load_and_deserialize_raceday(path)` — laddar från explicit sökväg
- `get_raceday_with_date("YYYY-MM-DD")` — laddar äldre tävling
- `get_all_dates()` — listar alla sparade tävlingar

### `htmlparsing.py` — RaceLogic HTML-parser

`RCMHtmlParser` (extends `html.parser.HTMLParser`) är en tillståndsmaskin som extraherar:

- Förarnummer och namn (header-rad)
- Lapptider per förare (en lista `Duration` per förare)

Hjälpfunktioner returnerar parsat resultat i färdig form:

- `get_total_times(parser)` — totaltid per förare
- `get_num_laps_driven(parser)` — antal varv per förare
- `get_positions(...)` — sorterad placeringslista (varv DESC, tid ASC)
- `get_best_laptimes(parser)` — bästa varvtid per förare (exkluderar setup-varv)
- `get_average_laptimes(...)` — snittvarv per förare

### `duration.py` — Tidsklass

Värde-objekt som lagrar millisekunder internt. Stödjer `+`, `*` och alla jämförelseoperatorer. `__str__` returnerar `M:SS:mmm`.

### `filelocation.py` — USB-läsning

`find_and_read_latest_html_file()` väntar på att USB-minnet är monterat, listar HTML-filer med numeriska filnamn, väljer den med högst nummer (= senaste racet) och läser den med encoding `utf-16-le` (RaceLogic-format).

### `textmessages.py` — Formatering

Bygger användarvänliga textsträngar för:

- Resultat (med medaljer 🥇🥈🥉, totaltid, bästa/snittvarv)
- Startlistor (sorterade per `CLASS_ORDER`)
- "Nästa race"-meddelande
- Poängtabeller (med eller utan per-omgång-detaljer)

### `constants.py`

| Konstant | Värde | Användning |
|---|---|---|
| `RESULT_FOLDER_PATH` | `~/RCBashResults` | Var tävlingsdags-JSON sparas |
| `MAX_POINTS_IN_NON_FINALS` | 40 | Förstaplats-poäng i Kval/Åttondel/Kvart/Semi |
| `MAX_POINTS_IN_FINALS` | 80 | Förstaplats-poäng i Final |

### `names.py`

Statiskt dict `NAMES = {10: "...", 11: "...", ...}`. Redigeras manuellt inför tävling.

### `util.py`

Hjälpfunktion `get_previous_group_wrap_around()` för navigering mellan grupper med wrap-around.

### `__names.py`

Backup/legacy-kopia av `names.py`. Används inte aktivt.

---

## 7. Datamodell och lagring

### Filplacering

- **Windows**: `%USERPROFILE%\RCBashResults\YYMMDD.json`
- **Linux fallback**: `/home/malcolm/RCBashResults/YYMMDD.json` (om denna sökväg existerar)

Filnamn är `YYMMDD.json`, t.ex. `260422.json` för 22 april 2026.

### JSON-schema

```json
{
  "all_participants": [10, 11, 12, ...],
  "start_lists": {
    "Kval": {
      "2WD": { "A": [10, 11, ...], "B": [...], "C": [...] },
      "SC":  { "A": [...], "B": [...], "C": [...] },
      "4WD": { "A": [...], "B": [...], "C": [...] }
    },
    "Åttondelsfinal": { ... },
    "Kvartsfinal":    { ... },
    "Semifinal":      { ... },
    "Final":          { ... }
  },
  "results": {
    "Kval": {
      "2WD": {
        "A": {
          "positions": [10, 11, 12, ...],
          "num_laps_driven": { "10": 14, "11": 13, ... },
          "total_times":     { "10": {"milliseconds": 480000}, ... },
          "best_laptimes":   [[10, {"milliseconds": 31000}], ...],
          "average_laptimes":[[10, {"milliseconds": 34000}], ...],
          "manual": false,
          "dns": [99]
        }
      }
    }
  },
  "current_heat": 0
}
```

`current_heat` är ett index i `RACE_ORDER` (0=Kval, 1=Åttondelsfinal, …, 4=Final).

---

## 8. Poängberäkning

### Per heat (under en tävlingsdag)

| Omgång | Förstaplats | Avdrag per plats |
|---|---|---|
| Kval, Åttondel, Kvart, Semi | 40 | −1 |
| Final | 80 | −2 |

Final-poäng räknas inte dubbelt mot tidigare omgångar — Final-resultatet ersätter inte tidigare poäng utan adderas till totalen via en separat poängskala.

### Säsong (flera tävlingsdagar)

`SeasonPoints` aggregerar varje förares poäng över flera tävlingar. **Sämsta tävlingen droppas** automatiskt (drop-worst-race). `numpy.argmin` används för att hitta vilken tävling som ska droppas per förare.

---

## 9. Algoritmer för startlistor

### Efter Kval → Åttondelsfinal

`_create_start_list_from_qualifiers()`:

1. Sortera varje grupp (A/B/C) inom en klass efter (varv DESC, totaltid ASC).
2. Interleavar vinnare från grupperna och bygger nya A/B/C-grupper.

### Mellan Åttondelsfinal/Kvart/Semi

`_create_start_list_intermediate_races()`:

- Byt de **två snabbaste från lägre grupp** med de **två långsammaste från högre grupp**.
- Detta jämnar ut grupperna inför nästa omgång.

### Inför Final

`_create_start_lists_for_finals()`:

1. Beräkna total poäng per förare (alla heats hittills).
2. Sortera per klass efter (poäng DESC, antal max-poäng-heat DESC som tiebreaker).
3. Fyll Final-grupper i ordning A → B → C, med max `max_participants` (default 9) per grupp.

---

## 10. Tekniska detaljer och kända begränsningar

### Tekniskt

- **Python-version**: 3.7+ (f-strings, type hints används genomgående).
- **Encoding**: HTML från RaceLogic läses som `utf-16-le` (hårdkodat).
- **Ingen nätverkstrafik**: helt lokalt USB-baserat system.
- **Tidshantering**: använder lokal systemtid via `datetime.now()`.

### Beroenden

| Paket | Källa | Användning |
|---|---|---|
| `numpy` | pip | `argmin` i drop-worst-race |
| `clipboard` | pip | Kopiera resultat till urklipp |
| `html.parser`, `json`, `argparse`, `pathlib`, `collections` | stdlib | — |

### Kända begränsningar

- **Hårdkodad fallback-sökväg**: `filelocation.py` har `/home/malcolm/RCBashResults` som fallback (sannolikt kvar från tidigare server-installation).
- **Dubbla import-paths**: vissa moduler försöker först `from server.racelogic.X` och faller tillbaka till `from X` — antyder en parallell webserver-deployment som inte är inkluderad här.
- **Duplikat-förare**: systemet **detekterar** men **tillåter** samma förare i flera grupper. Ingen automatisk korrigering.
- **Encoding-format låst**: andra HTML-encodings än UTF-16-LE stöds inte.
- **`__names.py`**: legacy-fil, ej aktivt använd.
- **Min Python via `py`-launcher**: batch-filerna anropar `py`, inte `python` — kräver Pythons `py`-launcher (finns på Windows som standard).
