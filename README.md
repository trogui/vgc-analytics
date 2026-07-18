# VGC Regulation M-B Analytics

Motor analítico determinista para los torneos públicos de Pokémon VGC M-B en
Play Limitless. Regulation M-B utiliza Megaevolución: **tera no forma parte del
modelo**. Las megapiedras permanecen en el campo `item` de cada Pokémon.

La aplicación permite analizar win rates entre núcleos y buscar composiciones
o teamlists concretas. Cuando se seleccionan seis Pokémon, las variantes de set
se pueden comparar contra una referencia por movimientos, objeto, habilidad y
naturaleza.

## Requisitos

- Python 3.12 o superior.
- [`uv`](https://docs.astral.sh/uv/).
- Node.js 22 o superior y npm, solo para modificar el frontend.

## Abrir la aplicación

En macOS, haz doble clic en `run.command`. También se puede ejecutar:

```bash
uv sync
uv run vgc-analytics serve --database data/vgc_mb.duckdb --open
```

La aplicación se abre en `http://127.0.0.1:8765`. El botón **Refresh** busca
torneos nuevos, descarga `details`, `standings` y `pairings`, y solo ingiere los
que ya tienen resultados finales.

El servidor está diseñado para ejecutarse localmente y no implementa
autenticación. No debe exponerse directamente a Internet.

## Comandos

```bash
# Reconstruir desde el snapshot inicial
uv run vgc-analytics build \
  --snapshot data/seed.json.gz \
  --database data/vgc_mb.duckdb

# Añadir torneos finalizados nuevos
uv run vgc-analytics sync --database data/vgc_mb.duckdb --raw data/raw

# Verificar invariantes estructurales y estadísticas
uv run vgc-analytics verify --database data/vgc_mb.duckdb

# Tests deterministas
uv run pytest
```

## Desarrollo del frontend

La interfaz está implementada con React, TypeScript y Vite. FastAPI continúa
sirviendo la API y el build de producción como una única aplicación.

```bash
# Terminal 1
uv run vgc-analytics serve --database data/vgc_mb.duckdb

# Terminal 2
cd frontend
npm run dev
```

Antes de publicar cambios del frontend, genera los assets versionados que
FastAPI sirve desde el paquete Python:

```bash
cd frontend
npm test
npm run build
```

## Semántica de los cálculos

Cada partida válida produce dos filas en `match_sides`, una desde cada lado.
Una victoria de A sobre B se representa como `A: W/1.0` y `B: L/0.0`; un
empate produce dos filas `T/0.5`.

El win rate mostrado es `victorias / (victorias + derrotas)`. Los empates se
conservan en el record, pero no alteran ese porcentaje.

Se excluyen por defecto byes, dobles derrotas, resultados inválidos y partidas
en las que alguno de los dos jugadores no tiene una teamlist pública válida.
Los problemas de origen se conservan en `data_quality_issues`.

## Consulta de cores

Los cores se consultan directamente sobre los seis Pokémon normalizados de
cada equipo. Por ejemplo:

```text
Basculegion + Sneasler + Kingambit
vs Tyranitar + Excadrill
solo torneos con al menos 21 participantes
```

se resuelve filtrando los Pokémon de cada lado y agregando `match_sides`. No
se almacenan combinaciones derivadas y el orden de los Pokémon no altera el
resultado.

## Garantías del Refresh

- Append-only por `tournament_id`.
- Transacción completa por torneo.
- Idempotente: repetir un Refresh no duplica filas.
- La frontera solo avanza cuando el torneo queda ingerido.
- Los torneos activos se vuelven a comprobar en el siguiente Refresh.
- Cada respuesta nueva se conserva comprimida en `data/raw` usando SHA-256.
- Si una validación o inserción falla, DuckDB hace rollback y el torneo se
  vuelve a intentar en el siguiente Refresh.

## Datos y servicios externos

`data/seed.json.gz` es un snapshot reproducible obtenido el **18 de julio de
2026** mediante los [endpoints documentados de torneos de Play
Limitless](https://docs.limitlesstcg.com/developer/tournaments). Reúne 192
torneos públicos de VGC M-B con fecha entre el 20 de junio y el 18 de julio de
2026. Conserva clasificaciones, emparejamientos y teamlists, pero elimina los
nombres y países de los jugadores y sustituye sus identificadores por aliases
locales a cada torneo mediante `scripts/anonymize_seed.py`.

Los datos proceden de Play Limitless y siguen sujetos a sus [términos de
servicio](https://play.limitlesstcg.com/tos) y [política de
privacidad](https://play.limitlesstcg.com/privacy). Cualquier licencia aplicada
al código de este repositorio no concede derechos adicionales sobre estos datos
de terceros. La base DuckDB y las respuestas descargadas durante **Refresh** se
generan localmente y están excluidas de Git.

Las imágenes de Pokémon se cargan en el navegador desde una versión fijada del
repositorio de sprites de [PokéAPI](https://github.com/PokeAPI/sprites) a través
de jsDelivr.

Este es un proyecto comunitario no oficial y no está afiliado con Nintendo,
Game Freak, The Pokémon Company, Play Limitless ni PokéAPI.
