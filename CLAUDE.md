# Instrucciones del proyecto

## Este repositorio es PÚBLICO

Cualquiera puede leer todo lo que se commitee acá, y el historial de git queda
aunque después se borre el archivo. Antes de agregar cualquier cosa al repo,
verificá que sea información que no te importe publicar.

### Nunca commitear

- **Credenciales de cualquier tipo**: tokens, API keys, contraseñas, cookies de
  sesión, headers de autenticación capturados del navegador. Si alguna fuente
  llegara a necesitar autenticación, la credencial va en **GitHub Secrets** y se
  lee con `os.environ`; nunca escrita en el código ni en un archivo de config.
- **Archivos `.env`** de este ni de ningún otro proyecto.
- **Datos personales del usuario**: dirección, sucursal donde compra, qué
  tarjetas o bancos tiene realmente, cuánto gasta, cuánto tope consumió.
  Esas preferencias viven en `localStorage` del navegador **por diseño**, y ahí
  se quedan. No moverlas a un archivo del repo ni a la salida de la ingesta.
- **Volcados crudos de páginas o respuestas de API** sin revisar. Pueden traer
  identificadores de sesión o datos de otras personas.

### Qué sí es público y está bien

- El código de la ingesta y del frontend.
- `docs/datos/promos.json`: son promociones publicadas por bancos y comercios.
- `datos/comercios-santa-fe.yml`: nombres de cadenas de supermercados.
- `datos/estado-anterior.json`: la corrida previa, para calcular novedades.

`datos/cache/` está en `.gitignore` a propósito: son páginas de detalle
descargadas, se regeneran solas y no aportan nada al historial.

### Al agregar una fuente nueva

1. Que sea una página o endpoint **público**, accesible sin iniciar sesión. No
   scrapear detrás de un login ni reusar la sesión del usuario.
2. Identificarse con el `User-Agent` del proyecto y no golpear el servidor más
   de lo necesario. La ingesta corre una vez por día: alcanza.
3. Si la fuente no publica tope o compra mínima, dejar `limites_conocidos` en
   `False`. La app distingue "sin tope" de "no informado" y eso no se negocia:
   afirmar un límite que no conocemos es el error que hace perder plata.

## Sobre el dominio

- La app es para **Santa Fe capital**. Las fuentes son nacionales o
  provinciales, así que `datos/comercios-santa-fe.yml` es lo que filtra. Un
  comercio nuevo entra ahí a mano, con `confirmado: false` hasta verificarlo.
- Banco Santa Fe opera en toda la provincia: sus promos pueden ser de Rosario,
  Rafaela o Reconquista. No asumir que son de la capital.
- Al comparar nombres de comercios, usar `zona.contiene()`: exige palabras
  completas y contiguas. La comparación por subcadena suelta ya causó falsos
  positivos reales ("dia" dentro de "diarco", "vea" dentro de "alvear").

## Verificar un cambio

```bash
python -m ingesta.main        # corre la ingesta completa
python -m ingesta.explorar    # lista los comercios que publica MODO hoy
python -m http.server 8765 --directory docs
```

Después de tocar el filtro de zona, revisar el mapeo comercio por comercio
antes de dar por buena la corrida: que el total baje no significa que esté mal,
y que suba no significa que esté bien.
