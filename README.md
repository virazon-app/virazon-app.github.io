# Virazón

Página de viento para el Club Náutico San Isidro, con alertas opcionales por Telegram. Se actualiza sola cada 15 minutos en GitHub, gratis.

**La página:** `https://virazon-app.github.io/`

**Qué mira:**

- Estación Windguru del **Club Náutico San Isidro** (viento real en el club)
- **Pilote Norden** (CARP): viento y marea
- **AySA Palermo**: viento y nivel del río
- **Windguru GFS 13 km**: pronóstico ("lo que debería pasar")

**Qué muestra:** nuestra apuesta de nudos, la probabilidad de que entre el SE, las brújulas, el gráfico medido vs. Windguru vs. apuesta, el agua (sube/baja y a cuántos cm/h), la virazón y el historial de las últimas 24 h.

## Alertas por Telegram (opcional)

1. En Telegram, escribile `/newbot` a **@BotFather** y guardá el token que te da.
2. En este proyecto: **Settings → Secrets and variables → Actions → New repository secret**. Name: `TELEGRAM_TOKEN`, Secret: el token.
3. Mandale `/start` a tu bot. En la próxima corrida te llega la bienvenida.

Te avisa cuando entra SE en Norden, cuando sopla 12 kn o más en el club (y cuando se corta), cuando rota el viento, cuando el agua cambia de subir a bajar, cuando nuestra apuesta da para salir y todas las mañanas a las 8. Con `/estado` te manda el tablero. Entre las 23 y las 7 no manda nada.

## Ajustes

En `config.json` (abrí el archivo y tocá el lápiz):

| Ajuste | Qué hace | Inicial |
|---|---|---|
| `umbral_salir_kn` | Nudos para "da para salir" | 12 |
| `norden.alerta_kn` | Nudos de SE en Norden para avisar | 12 |
| `norden.sector_se_desde/hasta` | Qué cuenta como SE (grados) | 100–170 |
| `norden.factor_llega_al_club` | Qué parte del viento de Norden llega al club | 0.6 |
| `norden.demora_horas` | Cuánto tarda en llegar | 2 |
| `horas_silencio` | Sin alertas | 23 a 7 |

## Notas

- **Costo $0:** GitHub Actions y GitHub Pages son gratis en proyectos públicos.
- **Público:** el código y el historial de viento. El token del bot queda oculto.
- **Historial:** `data/historial.csv` guarda cada corrida, para recalibrar la apuesta con datos reales.
- **Norden:** la CARP publica el viento con ~1,5 h de demora (la marea viene al día).
- **Si una fuente se cae,** la app sigue con las otras.
- **Probar sin internet:** `DRY_RUN=1 python -m tests.prueba`.
