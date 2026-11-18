# m3u-extra

Een kleine webinterface voor `N_m3u8DL-RE`. Plak een gekopieerd downloadcommando, start de taak en volg de voortgang en het live logboek in je browser. De image bevat alvast `N_m3u8DL-RE`, `ffmpeg` en `mp4decrypt`, dus je hoeft niets lokaal te installeren.

## Snel starten

Met Docker:

```bash
docker run -d \
  --name ndl-web \
  -p 8000:8000 \
  -v /pad/naar/downloads:/downloads \
  -e TZ=Europe/Brussels \
  crisperfx/m3u-extra:latest
```

Open daarna `http://<server-of-nas-ip>:8000`.

Met Docker Compose gebruik je de meegeleverde `docker-compose.yml`:

```bash
docker compose up -d
```

De bestanden komen terecht in de map die je aan `/downloads` koppelt.

## Gebruik

1. Kopieer het volledige `N_m3u8DL-RE`-commando in het tekstveld.
2. Klik op **Start download**.
3. Het live logboek opent in een apart tabblad. Je ziet daar ook het percentage en de huidige stap.
4. Onder **Bestanden** vind je de afgemaakte `.mkv`-bestanden. Daar kun je ze ook downloaden of verwijderen.

Actieve taken blijven in het geheugen van de container. Bestanden blijven op schaal staan zolang de `/downloads`-map correct gekoppeld is.

## Instellingen

Kopieer `.env.example` naar `.env` als je Docker Compose gebruikt. Vul alleen in wat je nodig hebt.

| Instelling | Wat het doet | Standaard |
| --- | --- | --- |
| `TZ` | Tijdzone voor de container | `Europe/Brussels` in het voorbeeld |
| `MAX_CONCURRENT` | Hoeveel downloads tegelijk mogen draaien | `3` |
| `WEB_USER` en `WEB_PASSWORD` | Inloggen met gebruikersnaam en wachtwoord. Allebei leeg betekent geen inlogbeveiliging. | leeg |
| `EXT_TOKEN` | Geheime token voor de browser-extensie. Alleen nodig als je downloads vanuit de extensie wilt starten. | leeg |

Voor de browser-extensie vul je als server-URL `http://<server-of-nas-ip>:8000` in en als token dezelfde waarde als `EXT_TOKEN`.

## Updates

Bij een push naar `main` bouwt GitHub automatisch een nieuwe image en publiceert die naar Docker Hub. De nieuwste versie staat op `crisperfx/m3u-extra:latest`; per commit komt er ook een `sha-<commit>`-tag bij. Versies met een `v`-tag, zoals `v1.0.0`, krijgen dezelfde tag op Docker Hub.

Om te updaten:

```bash
docker compose pull
docker compose up -d
```

Of bij een losse container:

```bash
docker pull crisperfx/m3u-extra:latest
docker stop ndl-web
docker rm ndl-web
docker run -d --name ndl-web -p 8000:8000 -v /pad/naar/downloads:/downloads crisperfx/m3u-extra:latest
```

## Zelf bouwen

Wil je toch lokaal bouwen:

```bash
docker build -t crisperfx/m3u-extra:latest .
```

## Automatische publicatie

De workflow staat in `.github/workflows/docker-hub.yml`. Voor publicatie zijn twee repository secrets nodig:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (een Docker Hub access token, geen accountwachtwoord)

Zonder die secrets blijft de code werken, maar wordt er geen image gepubliceerd. Zet de Docker Hub-repository op **Public** als iedereen de image zonder login moet kunnen ophalen.
