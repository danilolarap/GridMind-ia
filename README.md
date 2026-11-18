# GridMind IA

API Flask para estimar consumo energetico a partir de lecturas historicas.

## Instalacion y ejecucion

Requiere Python 3.11 o posterior.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

El servidor escucha en el puerto 5000; la variable PORT permite cambiarlo.
El servidor integrado de Flask es para desarrollo. En produccion se debe usar
un servidor WSGI compatible con la plataforma.

## API

- GET /health: estado del servicio.
- POST /predict: recibe JSON con history, un arreglo de objetos con timestamp
  (fecha ISO 8601, preferiblemente con zona horaria) y consumption (numero finito
  mayor o igual a cero). Las fechas sin zona horaria se interpretan como UTC.
  Datos invalidos devuelven HTTP 400 con un campo error. Un historial vacio devuelve cero.

Ejemplo de cuerpo:

```json
{"history":[{"timestamp":"2026-11-12T12:00:00Z","consumption":0.002}]}
```

La respuesta contiene current_total (suma de las lecturas recibidas),
predicted_next_30_days y confidence_score.

## Supuestos del modelo

Cada lectura representa la **energia consumida en 10 segundos**, usando siempre
la misma unidad. Si los sensores entregan potencia en watts, hay que convertirla
a energia antes de enviar las lecturas. Se asume un muestreo regular cada 10 segundos.

Se conservan las lecturas en cero para reflejar la inactividad. Las lecturas
iguales o superiores a 20 veces la mediana de los valores positivos se excluyen
del pronostico, pero siguen incluidas en current_total.

Con menos de 20 lecturas o menos de 5 minutos de historial se proyecta el
promedio; con mas historial se utiliza regresion lineal. Una tendencia prolongada
durante 30 dias puede producir estimaciones poco realistas: conviene validar el
modelo con datos reales antes de usarlo para decisiones.
confidence_score conserva el valor fijo 0.85 por compatibilidad; no es una
medicion estadistica de confianza.

## Pruebas

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## Docker

```powershell
docker build -t gridmind-ia .
docker run --rm -p 5000:5000 gridmind-ia
```

La imagen usa gunicorn y escucha en `PORT` (5000 por defecto). Con `BIND_HOST=::` escucha
también por IPv6. Para levantar el esqueleto completo, usa `compose.yaml` del repo GridMind-backend.
