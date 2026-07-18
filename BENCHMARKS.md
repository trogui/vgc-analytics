# Benchmarks

Medidos sobre el snapshot del 18 de julio de 2026 en el equipo local, usando
192 torneos, 13.757 equipos válidos y 37.134 partidas.

| Consulta | Partidas | Resultado | Latencia |
|---|---:|---:|---:|
| Basculegion | 16.199 | 9.757–9.025–23; 51,95% | 13,8 ms |
| Basculegion sin mirror, torneos ≥21 | 13.207 | 6.940–6.255–12; 52,60% | 15,7 ms |
| Basculegion + Sneasler + Kingambit vs Tyranitar + Excadrill, torneos ≥21 | 53 | 30–23–0; 56,60% | 17,8 ms |

Treinta repeticiones calientes de la segunda consulta:

- mínimo: 15,3 ms
- mediana: 15,7 ms
- p95: 24,0 ms
- máximo: 33,7 ms

Los tiempos incluyen la apertura read-only de DuckDB y la consulta de partidas.
