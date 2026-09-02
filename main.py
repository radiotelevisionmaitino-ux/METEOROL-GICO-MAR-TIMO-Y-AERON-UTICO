import requests
import datetime
import time
import asyncio
import edge_tts
from pydub import AudioSegment
import os

# ==========================================
# CONFIGURACIÓN GENERAL Y CLAVES
# ==========================================
VOZ_TTS = "es-ES-AlvaroNeural" 
ARCHIVO_AUDIO_FINAL = "boletin_maitino_listo.mp3"
ARCHIVO_VOZ = "voz_temporal.mp3"
ARCHIVO_MUSICA = "intro.mp3" 

# TU CLAVE OFICIAL DE AEMET OPENDATA
API_KEY_AEMET = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyYWRpb3RlbGV2aXNpb25tYWl0aW5vQGdtYWlsLmNvbSIsImp0aSI6IjA2MDRkMWUyLTJiNjQtNDY5Yi05MjU4LTVmZTcxOTFkYTM5ZSIsImV4cCI6MTc5NzAxNjkyNiwiaXNzIjoiQUVNRVQiLCJpYXQiOjE3ODgzNzY5MjYsInVzZXJJZCI6IjA2MDRkMWUyLTJiNjQtNDY5Yi05MjU4LTVmZTcxOTFkYTM5ZSIsInJvbGUiOiIifQ.0Q2O8F5SjNTVeUEfBLnaluW0eq_XLrSAsDcWnXbr0y8"

COORDS = {
    "elche": {"lat": 38.2622, "lon": -0.7011},
    "alicante_costa": {"lat": 38.3, "lon": -0.4},
    "baleares": {"lat": 39.5, "lon": 2.5},
    "alboran": {"lat": 36.0, "lon": -3.0},
    "cantabrico": {"lat": 43.5, "lon": -5.5},
    "canarias": {"lat": 28.1, "lon": -15.4},
    "madrid": {"lat": 40.4165, "lon": -3.7026},
    "sevilla": {"lat": 37.3828, "lon": -5.9731},
    "cadiz": {"lat": 36.5, "lon": -6.2}
}

# ==========================================
# FUNCIONES DE OBTENCIÓN DE DATOS REALES
# ==========================================

def obtener_avisos_aemet():
    url = "https://opendata.aemet.es/opendata/api/avisos/nacional"
    querystring = {"api_key": API_KEY_AEMET}
    headers = {"cache-control": "no-cache"}
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            datos_url = response.json().get('datos')
            res_datos = requests.get(datos_url, timeout=10)
            avisos = res_datos.json()
            
            if not avisos:
                return "Sin avisos activados en el territorio nacional", "Sin avisos activados"
                
            nacionales = []
            locales_alicante = []
            
            for aviso in avisos:
                provincia = aviso.get('nombreProvincia', '')
                nivel = aviso.get('nivelAviso', '')
                desc = aviso.get('descripcionTerminoMunicipal', '') or aviso.get('tipoAviso', '')
                
                info = f"Aviso {nivel} por {desc} en {provincia}"
                nacionales.append(info)
                
                if 'Alacant' in provincia or 'Alicante' in provincia:
                    locales_alicante.append(f"Aviso {nivel} por {desc}")
                    
            txt_nacional = "Avisos activos en varias provincias, consulte fuentes de AEMET para más detalles" if nacionales else "Sin avisos activados a nivel nacional"
            txt_local = ", ".join(locales_alicante) if locales_alicante else "Sin avisos activados"
            
            return txt_nacional, txt_local
    except Exception:
        pass
    return "Datos de avisos nacionales no disponibles", "Datos de avisos locales no disponibles"

def obtener_datos_clima(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure,precipitation,weathercode,apparent_temperature,visibility&timezone=Europe%2FMadrid"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return None

def obtener_datos_maritimos(lat, lon):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction&timezone=Europe%2FMadrid"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return None

def obtener_metar_leal():
    url = "https://aviationweather.gov/api/data/metar?ids=LEAL&format=json"
    try:
        return requests.get(url, timeout=10).json()[0]
    except:
        return None

def direccion_viento_texto(grados):
    sectores = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
    try:
        indice = round(float(grados) / 45) % 8
        return sectores[indice]
    except:
        return "variable"

def traducir_cielo(codigo):
    if codigo is None: return "datos no disponibles"
    codigos = {
        0: "despejados", 1: "poco nubosos", 2: "parcialmente nublados", 3: "cubiertos",
        45: "con niebla", 48: "con bancos de niebla",
        51: "con llovizna ligera", 53: "con llovizna", 55: "con llovizna densa",
        61: "con lluvia leve", 63: "con lluvia moderada", 65: "con lluvia fuerte",
        71: "con nieve leve", 73: "con nieve moderada", 75: "con nieve fuerte",
        95: "con tormentas"
    }
    return codigos.get(int(codigo), "con nubosidad")

def estado_mar_texto(altura):
    try:
        h = float(str(altura).replace(',', '.'))
        if h < 0.2: return "Mar rizada"
        if h < 0.5: return "Marejadilla"
        if h < 1.25: return "Marejada"
        if h < 2.5: return "Fuerte marejada"
        return "Mar gruesa"
    except:
        return "Datos de mar no disponibles"

def visibilidad_texto(metros):
    try:
        km = float(metros) / 1000
        if km >= 10: return "Excelente, superior a 10 kilómetros"
        if km >= 5: return f"Buena, de {km:.0f} kilómetros"
        if km >= 1: return f"Regular, de {km:.1f} kilómetros"
        return f"Reducida por debajo de 1 kilómetro"
    except:
        return "Datos de visibilidad no disponibles"

# ==========================================
# GENERACIÓN DE TEXTO
# ==========================================

def generar_texto_boletin():
    ahora = datetime.datetime.now()
    
    if 6 <= ahora.hour < 14: saludo = "Buenos días"
    elif 14 <= ahora.hour < 21: saludo = "Buenas tardes"
    else: saludo = "Buenas noches"

    dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    dia_semana_str = dias_semana[ahora.weekday()]
    hora_min_str = ahora.strftime('%H y %M')
    is_dst = time.localtime().tm_isdst
    utc_offset = 2 if is_dst else 1
    
    # DATOS REALES AEMET
    aviso_nacional, aviso_local = obtener_avisos_aemet()

    # DATOS REALES CLIMA POR ZONA
    clima_elche = obtener_datos_clima(COORDS["elche"]["lat"], COORDS["elche"]["lon"])
    clima_madrid = obtener_datos_clima(COORDS["madrid"]["lat"], COORDS["madrid"]["lon"])
    clima_sevilla = obtener_datos_clima(COORDS["sevilla"]["lat"], COORDS["sevilla"]["lon"])
    clima_cantabrico = obtener_datos_clima(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])
    clima_baleares = obtener_datos_clima(COORDS["baleares"]["lat"], COORDS["baleares"]["lon"])
    clima_alboran = obtener_datos_clima(COORDS["alboran"]["lat"], COORDS["alboran"]["lon"])
    clima_cadiz = obtener_datos_clima(COORDS["cadiz"]["lat"], COORDS["cadiz"]["lon"])
    clima_canarias = obtener_datos_clima(COORDS["canarias"]["lat"], COORDS["canarias"]["lon"])

    # DATOS REALES MAR POR ZONA
    mar_elche = obtener_datos_maritimos(COORDS["alicante_costa"]["lat"], COORDS["alicante_costa"]["lon"])
    mar_baleares = obtener_datos_maritimos(COORDS["baleares"]["lat"], COORDS["baleares"]["lon"])
    mar_alboran = obtener_datos_maritimos(COORDS["alboran"]["lat"], COORDS["alboran"]["lon"])
    mar_cantabrico_mar = obtener_datos_maritimos(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])
    mar_cadiz = obtener_datos_maritimos(COORDS["cadiz"]["lat"], COORDS["cadiz"]["lon"])
    mar_canarias_mar = obtener_datos_maritimos(COORDS["canarias"]["lat"], COORDS["canarias"]["lon"])

    # DATOS METAR
    metar = obtener_metar_leal()

    def g_val(d, k, subk, i=None):
        try:
            val = d[k][subk] if i is None else d[k][subk][i]
            return str(val).replace('.', ',')
        except: return "datos no disponibles"

    def get_cielo(clima_obj):
        if not clima_obj: return "datos no disponibles"
        return traducir_cielo(clima_obj['current_weather'].get('weathercode'))

    def get_vis(clima_obj):
        if not clima_obj: return "datos no disponibles"
        try:
            return visibilidad_texto(clima_obj['hourly']['visibility'][0])
        except:
            return "datos no disponibles"

    def get_viento_texto(clima_obj):
        if not clima_obj: return "Datos de viento no disponibles"
        v_dir = direccion_viento_texto(clima_obj['current_weather'].get('winddirection'))
        v_vel = str(clima_obj['current_weather'].get('windspeed', '0')).replace('.', ',')
        return f"Componente {v_dir} a {v_vel} km/h"

    # --- Variables Elche ---
    temp_act = g_val(clima_elche, 'current_weather', 'temperature')
    hum_act = g_val(clima_elche, 'hourly', 'relativehumidity_2m', 0)
    v_dir = direccion_viento_texto(clima_elche['current_weather'].get('winddirection', 0)) if clima_elche else "variable"
    v_vel = g_val(clima_elche, 'current_weather', 'windspeed')
    pres_act = g_val(clima_elche, 'hourly', 'surface_pressure', 0)
    precip_act = g_val(clima_elche, 'hourly', 'precipitation', 0)
    cielo_act = get_cielo(clima_elche)
    vis_elche = get_vis(clima_elche)

    t_med = g_val(clima_elche, 'hourly', 'temperature_2m', 12)
    p_manana = g_val(clima_elche, 'hourly', 'precipitation_probability', 8)
    cielo_manana = traducir_cielo(clima_elche['hourly']['weathercode'][8]) if clima_elche else "datos no disponibles"
    
    t_tarde_min = g_val(clima_elche, 'hourly', 'temperature_2m', 16)
    t_tarde_max = g_val(clima_elche, 'hourly', 'apparent_temperature', 14)
    v_dir_tarde = direccion_viento_texto(clima_elche['hourly']['winddirection_10m'][16]) if clima_elche else "variable"
    v_vel_tarde = g_val(clima_elche, 'hourly', 'windspeed_10m', 16)
    p_tarde = g_val(clima_elche, 'hourly', 'precipitation_probability', 16)

    t_noche = g_val(clima_elche, 'hourly', 'temperature_2m', 22)
    cielo_noche = traducir_cielo(clima_elche['hourly']['weathercode'][22]) if clima_elche else "datos no disponibles"
    p_noche = g_val(clima_elche, 'hourly', 'precipitation_probability', 22)

    # --- Variables Aviación (METAR REAL SIN INVENTAR TENDENCIAS) ---
    met_viento = f"{metar.get('wdir', 'Variable')} grados a {metar.get('wspd', '0')} nudos" if metar else "Datos no disponibles"
    met_nubes = f"Base a {metar['clouds'][0].get('base', 'N/A')} pies" if metar and 'clouds' in metar and len(metar['clouds'])>0 else "Sin nubes reportadas"
    met_pres = str(metar.get('altim', 'Dato no disponible')).replace('.', ',') if metar else "Dato no disponible"
    met_fenomenos = metar.get('wxString', 'Sin fenómenos meteorológicos significativos') if metar else "Datos no disponibles"

    # --- Variables Marítimas ---
    def info_mar(mar_obj):
        if not mar_obj: return "Dato no disponible", "Dato no disponible"
        ola = str(mar_obj['current'].get('wave_height', '0')).replace('.', ',')
        estado = estado_mar_texto(mar_obj['current'].get('wave_height', 0))
        return ola, estado

    ola_elche, est_elche = info_mar(mar_elche)
    ola_bal, est_bal = info_mar(mar_baleares)
    ola_alb, est_alb = info_mar(mar_alboran)
    ola_can, est_can = info_mar(mar_cantabrico_mar)
    ola_cad, est_cad = info_mar(mar_cadiz)
    ola_islas, est_islas = info_mar(mar_canarias_mar)

    texto = f"""{saludo}. Son las {hora_min_str} horas del {dia_semana_str} , {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico, aeronáutico y marítimo de Radio Maitino, con el estado actual y la predicción para las próximas horas.

AVISOS Y PREDICCIÓN TERRESTRE
Avisos Locales en Elche y Baix Vinalopó: {aviso_local}.
Avisos Nacionales: {aviso_nacional}.

Estado y Predicción Local para las próximas 12 horas.
Estado Actual: {temp_act} °C, humedad del {hum_act} %, viento del {v_dir} a {v_vel} km/h. Presión de {pres_act} hectopascales. Cielos {cielo_act}. Precipitación registrada: {precip_act} litros por metro cuadrado. 

Predicción Próximas 12 Horas:
Mañana: Cielos {cielo_manana}. Temperaturas en torno a los {t_med} °C al mediodía. Precipitación del {p_manana} %.
Tarde: Temperaturas entre los {t_tarde_min} °C y {t_tarde_max} °C. Viento de componente {v_dir_tarde} con rachas de {v_vel_tarde} km/h a partir de las 16 horas. Precipitación del {p_tarde} %.
Noche: Temperaturas de {t_noche} °C con cielos {cielo_noche}. Precipitación del {p_noche} %.

Estado y Predicción nacional actual.
Norte y Cantábrico: Cielos {get_cielo(clima_cantabrico)} con {g_val(clima_cantabrico, 'current_weather', 'temperature')} grados.
Centro y Meseta: Cielos {get_cielo(clima_madrid)} con {g_val(clima_madrid, 'current_weather', 'temperature')} grados.
Sur: Cielos {get_cielo(clima_sevilla)} con {g_val(clima_sevilla, 'current_weather', 'temperature')} grados.

AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
Condiciones Actuales: {met_fenomenos}.
Viento en Superficie: {met_viento}.
Techo de Nubes: {met_nubes}.
Presión Atmosférica: {met_pres} hectopascales.

AVISOS Y PREDICCIÓN MARÍTIMA
Costa de Alicante y Elche
Viento: {get_viento_texto(clima_elche)}.
Estado de la Mar: {est_elche} con altura de ola de {ola_elche} metros.
Tiempo: {cielo_act}.
Visibilidad: {vis_elche}.

Predicción Nacional Marítima
Mediterráneo (Sector Baleares y Canal de Ibiza):
Viento: {get_viento_texto(clima_baleares)}.
Estado de la Mar: {est_bal} con altura de ola de {ola_bal} metros.
Tiempo: {get_cielo(clima_baleares)}.
Visibilidad: {get_vis(clima_baleares)}.

Mediterráneo (Sector Alborán y Golfo de Vera):
Viento: {get_viento_texto(clima_alboran)}.
Estado de la Mar: {est_alb} con altura de ola de {ola_alb} metros.
Tiempo: {get_cielo(clima_alboran)}.
Visibilidad: {get_vis(clima_alboran)}.

Costa Cantábrica y Galicia:
Viento: {get_viento_texto(clima_cantabrico)}.
Estado de la Mar: {est_can} con altura de ola de {ola_can} metros.
Tiempo: {get_cielo(clima_cantabrico)}.
Visibilidad: {get_vis(clima_cantabrico)}.

Atlántico Andaluz (Cádiz y Huelva):
Viento: {get_viento_texto(clima_cadiz)}.
Estado de la Mar: {est_cad} con altura de ola de {ola_cad} metros.
Tiempo: {get_cielo(clima_cadiz)}.
Visibilidad: {get_vis(clima_cadiz)}.

Islas Canarias:
Viento: {get_viento_texto(clima_canarias)}.
Estado de la Mar: {est_islas} con altura de ola de {ola_islas} metros.
Tiempo: {get_cielo(clima_canarias)}.
Visibilidad: {get_vis(clima_canarias)}.

Información meteorológica, marítima y aeronáutica elaborada a partir de los datos telemáticos en tiempo real de la Agencia Estatal de Meteorología, Open-Meteo y AviationWeather.
Este ha sido el boletín de Radio Maitino, emitido a las {hora_min_str} horas, unidad de tiempo coordinado +{utc_offset}. Actualizamos la predicción en próximos espacios. Buena jornada y buena navegación.
"""
    return texto

# ==========================================
# PRODUCCIÓN DE AUDIO
# ==========================================
async def generar_audio_tts(texto):
    print(f"[{datetime.datetime.now()}] Generando locución (Edge TTS)...")
    comunicador = edge_tts.Communicate(texto, VOZ_TTS, rate="+0%") 
    await comunicador.save(ARCHIVO_VOZ)

def mezclar_audio_radio():
    print(f"[{datetime.datetime.now()}] Ensamblando audio...")
    try:
        voz = AudioSegment.from_mp3(ARCHIVO_VOZ)
        duracion_exacta = 7 * 60 * 1000 

        if not os.path.exists(ARCHIVO_MUSICA):
            mix_final = voz[:duracion_exacta]
            if len(mix_final) < duracion_exacta:
                silencio = AudioSegment.silent(duration=(duracion_exacta - len(mix_final)))
                mix_final = mix_final + silencio
            mix_final.export(ARCHIVO_AUDIO_FINAL, format="mp3")
            return

        musica = AudioSegment.from_mp3(ARCHIVO_MUSICA)

        if len(voz) >= duracion_exacta:
            mix_final = voz[:duracion_exacta]
        else:
            tiempo_restante = duracion_exacta - len(voz)
            musica_loop = musica * (tiempo_restante // len(musica) + 1)
            musica_necesaria = musica_loop[:tiempo_restante].fade_in(2000)
            mix_final = voz + musica_necesaria

        mix_final = mix_final.fade_out(5000)
        mix_final.export(ARCHIVO_AUDIO_FINAL, format="mp3", bitrate="192k")
    except Exception as e:
        print(f"ERROR CRÍTICO en la producción de audio: {e}")
        raise 

def ejecutar_boletin():
    print(f"\n--- INICIANDO ACTUALIZACIÓN DEL BOLETÍN ---")
    texto_boletin = generar_texto_boletin()
    
    try:
        texto_html = texto_boletin.replace('\n', '<br>')
        with open("boletin_texto.txt", "w", encoding="utf-8") as f:
            f.write(texto_html)
    except Exception as e:
        print(f"Error guardando el texto: {e}")

    asyncio.run(generar_audio_tts(texto_boletin))
    mezclar_audio_radio()

    if os.path.exists(ARCHIVO_VOZ):
        os.remove(ARCHIVO_VOZ)

if __name__ == "__main__":
    ejecutar_boletin()
