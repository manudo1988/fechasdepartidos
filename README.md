# Calendario de partidos

Página web gratuita con los partidos de **Liga Deportiva Alajuelense**, **Boca Juniors**,
**Inter Miami** y **FC Barcelona**: calendario mensual, día de hoy marcado, rival, competencia,
escudos y hora de Costa Rica.

Los datos salen de la API pública de ESPN, que no pide llave ni registro.

## Cómo publicarla gratis (GitHub Pages, ~10 minutos)

1. Crear una cuenta en [github.com](https://github.com) y luego un repositorio nuevo, público,
   llamado por ejemplo `calendario-partidos`.
2. Subir estos archivos al repositorio (botón **Add file → Upload files**):
   `index.html`, `partidos.json`, `manuales.json`, `README.md` y, si querés la tarea automática,
   `actualizar_partidos.py` y la carpeta `.github`.
   Si el explorador de archivos no deja arrastrar carpetas ocultas, se puede crear el archivo
   a mano con **Add file → Create new file** y escribir la ruta
   `.github/workflows/actualizar.yml` antes de pegar el contenido.
3. En **Settings → Pages**, en *Source* elegir `Deploy from a branch`, rama `main`, carpeta `/ (root)`
   y guardar. En un par de minutos GitHub muestra la dirección pública, del tipo
   `https://tu-usuario.github.io/calendario-partidos/`.
4. En **Settings → Actions → General → Workflow permissions**, marcar
   `Read and write permissions` y guardar. Esto le permite a la tarea semanal guardar los partidos.
5. En la pestaña **Actions**, entrar a *Actualizar partidos* y correrla una vez con
   **Run workflow** para dejar el archivo `fixtures.json` listo.

Listo: la dirección se puede abrir desde el celular y guardar en la pantalla de inicio.

> Si se abre el `index.html` con doble clic en la computadora (dirección `file://`), el calendario
> se ve pero sin partidos: el navegador bloquea la consulta a ESPN. Hay que publicarla en un sitio
> web real (GitHub Pages, Netlify Drop, Vercel).

## De dónde salen los datos

Hay dos capas, y la página usa la primera que tenga cada partido:

1. **`manuales.json`** — lo que escribís a mano. Manda sobre todo lo demás.
2. **`fixtures.json`** — lo genera la tarea semanal de GitHub Actions.
3. **`partidos.json`** — el calendario revisado a mano el 9 de setiembre, que sirve de respaldo
   permanente: aunque las fuentes automáticas fallen, la página nunca queda vacía.

### La actualización automática

`actualizar_partidos.py` lee los calendarios **.ics de [Fixtur.es](https://fixtur.es)**, un
servicio gratuito que publica un archivo por equipo con *todas* sus competencias y lo mantiene al
día solo (si cambia una hora, cambia en el archivo). No pide llave ni registro, y al ser un archivo
de texto plano no bloquea a los servidores de GitHub como sí hace ESPN.

| Equipo | Fuente automática |
| --- | --- |
| Boca Juniors | `ics.fixtur.es/v2/boca-juniors.ics` — Liga Profesional, Copa Argentina, Libertadores, Sudamericana |
| Inter Miami | `ics.fixtur.es/v2/inter-miami-cf.ics` — MLS, Leagues Cup, Concacaf, US Open Cup |
| Barcelona | `ics.fixtur.es/v2/fc-barcelona.ics` — LaLiga, Champions, Copa del Rey, Supercopa |
| Alajuelense | ESPN a través de un proxy público; puede fallar |

**Alajuelense es la excepción.** Fixtur.es no cubre la Primera División de Costa Rica ni la Copa
Centroamericana, y ESPN bloquea a los servidores de GitHub. El script lo intenta por tres caminos
(directo, allorigins y r.jina.ai) y si ninguno responde, simplemente deja lo que ya está en
`partidos.json`. Al final de la página, en «Competencias consultadas», se ve cuál respondió.

Para saber si funcionó: pestaña **Actions → Actualizar partidos**, entrás a la última corrida y
abrís el paso *Descargar partidos*; ahí se lista cuántos partidos trajo cada fuente.

### Verificación de las fuentes manuales

El calendario de `partidos.json` se armó revisando: laliga.com y fcbarcelona.es (Barcelona),
intermiamicf.com y MLS (Inter Miami), la Liga Profesional vía La Nación de Argentina y bocastats
(Boca), y Unafut vía La Nación de Costa Rica, es.concacaf.com, Teletica y CRHoy (Alajuelense).

Los escudos de los cuatro equipos se cargan como imágenes desde el CDN de ESPN, que sí funciona
sin API ni permisos.

## Qué revisar cada tanto

Con la tarea funcionando, Boca, Inter Miami y Barcelona se actualizan solos, incluidos los partidos
nuevos de copas y los cambios de hora. Para Alajuelense conviene revisar Unafut y Concacaf una vez
por semana y, si hay algo nuevo, agregarlo en `manuales.json`:

```json
{
  "partidos": [
    { "equipo": "lda", "fecha": "2026-10-15", "hora": "20:00", "rival": "Puntarenas FC",
      "torneo": "Torneo de Copa", "local": true, "sede": "Estadio Alejandro Morera Soto" }
  ]
}
```

Si un partido de `manuales.json` cae el mismo día que uno automático, gana el de `manuales.json`,
así que también sirve para corregir una hora equivocada sin tocar los otros archivos.

## Competencias que trae cada equipo

| Equipo | Competencias consultadas |
| --- | --- |
| Alajuelense | Primera División, Torneo de Copa, Copa Centroamericana, Concacaf Champions Cup, amistosos |
| Boca Juniors | Liga Profesional, Copa Argentina, Libertadores, Sudamericana, Recopa, amistosos |
| Inter Miami | MLS, Leagues Cup, Concacaf Champions Cup, Campeones Cup, US Open Cup, amistosos |
| Barcelona | LaLiga, Champions League, Copa del Rey, Supercopa de España, Supercopa de Europa, Mundial de Clubes, Joan Gamper, amistosos |

Esa lista aplica solo si reactivás ESPN. Con el calendario propio, cada partido lleva escrito el
nombre del torneo tal como aparece en `partidos.json`.

## Agregar partidos a mano

Para lo que la fuente no traiga, está el archivo `manuales.json`. Se edita directo en GitHub
(clic en el archivo → el lápiz → *Commit changes*) y los partidos aparecen en el calendario
mezclados con los demás, marcados como «agregado a mano»:

```json
{
  "partidos": [
    {
      "equipo": "lda",
      "fecha": "2026-10-15",
      "hora": "20:00",
      "rival": "Puntarenas FC",
      "torneo": "Torneo de Copa",
      "local": true,
      "sede": "Estadio Alejandro Morera Soto"
    }
  ]
}
```

`equipo` es `lda`, `boca`, `miami` o `barca`. La hora se escribe en formato de 24 horas y en tiempo
de Costa Rica; si todavía no se confirma, se puede omitir y la página muestra «Por confirmar».

## Cambiar equipos o competencias

Los equipos están definidos en dos lugares, con la misma estructura: la lista `EQUIPOS` dentro de
`index.html` y la lista `EQUIPOS` de `actualizar_partidos.py`. Cada equipo tiene su liga local
(para encontrar su identificador en ESPN), sus nombres alternativos y la lista de torneos.

Los códigos de torneo son los de ESPN: `crc.1` (Primera División de Costa Rica), `arg.1`,
`usa.1` (MLS), `esp.1` (LaLiga), `uefa.champions`, `conmebol.libertadores`,
`concacaf.champions`, `club.friendly`, y así. Se pueden ver en las direcciones de las páginas de
ESPN, por ejemplo `espn.com/futbol/equipo/_/id/83/esp.1`. Si un código no existe o el equipo no
juega ese torneo, el programa lo salta sin fallar.

## Detalle técnico

- `index.html` — página completa (HTML, CSS y JavaScript en un solo archivo, sin dependencias).
- `actualizar_partidos.py` — descarga los partidos y escribe `fixtures.json`. Solo usa la
  biblioteca estándar de Python.
- `.github/workflows/actualizar.yml` — tarea semanal de GitHub Actions.
- `partidos.json` — el calendario verificado; es la fuente principal.
- `manuales.json` — correcciones y partidos sueltos; tiene prioridad sobre `partidos.json`.
- `fixtures.json` — lo escribe la tarea semanal; no hay que editarlo.

La API de ESPN es pública pero no oficial: puede cambiar sin avisar. Si algún día un equipo
deja de aparecer, casi siempre se arregla actualizando los códigos de torneo.
