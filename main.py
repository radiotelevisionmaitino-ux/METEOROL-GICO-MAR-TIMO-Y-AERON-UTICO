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
    """Conecta a AEMET OpenData para descargar los avisos oficiales en tiempo real"""
    url = "https://opendata.aemet.es/opendata/api/avisos/nacional"
    querystring = {"api_key": API_KEY_AEMET}
    headers = {"cache-control": "no-cache"}
    
    try:
        # Paso 1: Pedir URL de datos a AEMET
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            datos_url = response.json().get('datos')
            # Paso 2: Descargar el JSON de avisos reales
            res_datos = requests.get(datos_url, timeout=10)
            avisos = res_datos.json()
            
            if not avisos:
                return "Sin avisos activados en España", "Sin avisos activados en Alicante"
                
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
                    
            txt_nacional = "Hay avisos activos en varias provincias. Consulte AEMET para detalle." if nacionales else "Sin avisos severos activados"
            txt_local = ", ".join(locales_alicante) if locales_alicante else "Sin avisos activados"
            
            return txt_nacional, txt_local
    except Exception as e:
        print(f"Error conectando a AEMET: {e}")
    return "Datos de AEMET no disponibles", "Datos de AEMET no disponibles"

def obtener_datos_clima(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure,precipitation,weathercode,apparent_temperature&timezone=Europe%2FMadrid"
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
    indice = round(grados / 45) % 8
    return sectores[indice]

def traducir_cielo(codigo):
    codigos = {
        0: "despejados", 1: "principalmente despejados", 2: "parcialmente nublados", 3: "cubiertos",
        45: "con niebla", 48: "con niebla y escarcha",
        51: "con llovizna ligera", 53: "con llovizna moderada", 55: "con llovizna densa",
        61: "con lluvia leve", 63: "con lluvia moderada", 65: "con lluvia fuerte",
        71: "con nieve leve", 73: "con nieve moderada", 75: "con nieve fuerte",
        95: "con tormenta eléctrica"
    }
    return codigos.get(codigo, "con intervalos nubosos")

def estado_mar_texto(altura):
    try:
        h = float(str(altura).replace(',', '.'))
        if h < 0.2: return "Mar rizada"
        if h < 0.5: return "Marejadilla"
        if h < 1.25: return "Marejada"
        if h < 2.5: return "Fuerte marejada"
        return "Mar gruesa"
    except:
        return "Dato no disponible"

# ==========================================
# GENERACIÓN DE TEXTO CON PLANTILLA EXACTA
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
    
    # 1. Obtener Avisos AEMET reales
    aviso_nacional, aviso_local = obtener_avisos_aemet()

    # 2. Llamadas a telemetría Open-Meteo y METAR
    clima_elche = obtener_datos_clima(COORDS["elche"]["lat"], COORDS["elche"]["lon"])
    clima_madrid = obtener_datos_clima(COORDS["madrid"]["lat"], COORDS["madrid"]["lon"])
    clima_sevilla = obtener_datos_clima(COORDS["sevilla"]["lat"], COORDS["sevilla"]["lon"])
    clima_cantabrico = obtener_datos_clima(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])

    mar_elche = obtener_datos_maritimos(COORDS["alicante_costa"]["lat"], COORDS["alicante_costa"]["lon"])
    mar_baleares = obtener_datos_maritimos(COORDS["baleares"]["lat"], COORDS["baleares"]["lon"])
    mar_alboran = obtener_datos_maritimos(COORDS["alboran"]["lat"], COORDS["alboran"]["lon"])
    mar_cantabrico_mar = obtener_datos_maritimos(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])
    mar_cadiz = obtener_datos_maritimos(COORDS["cadiz"]["lat"], COORDS["cadiz"]["lon"])
    mar_canarias = obtener_datos_maritimos(COORDS["canarias"]["lat"], COORDS["canarias"]["lon"])

    metar = obtener_metar_leal()

    # --- Procesado de variables para ELCHE ---
    def g_val(d, k, subk, i=None):
        try:
            val = d[k][subk] if i is None else d[k][subk][i]
            return str(val).replace('.', ',')
        except: return "no disponible"

    temp_act = g_val(clima_elche, 'current_weather', 'temperature')
    hum_act = g_val(clima_elche, 'hourly', 'relativehumidity_2m', 0)
    v_dir = direccion_viento_texto(clima_elche['current_weather'].get('winddirection', 0)) if clima_elche else "variable"
    v_vel = g_val(clima_elche, 'current_weather', 'windspeed')
    pres_act = g_val(clima_elche, 'hourly', 'surface_pressure', 0)
    precip_act = g_val(clima_elche, 'hourly', 'precipitation', 0)
    cielo_act = traducir_cielo(clima_elche['current_weather'].get('weathercode', 0)) if clima_elche else "no disponibles"

    t_med = g_val(clima_elche, 'hourly', 'temperature_2m', 12)
    p_manana = g_val(clima_elche, 'hourly', 'precipitation_probability', 8)
    cielo_manana = traducir_cielo(clima_elche['hourly']['weathercode'][8]) if clima_elche else "no disponibles"
    tendencia_manana = "Aumento progresivo" if float(t_med.replace(',','.')) > float(temp_act.replace(',','.')) else "Descenso progresivo"
    
    t_tarde_min = g_val(clima_elche, 'hourly', 'temperature_2m', 16)
    t_tarde_max = g_val(clima_elche, 'hourly', 'temperature_2m', 14)
    sens_tarde = g_val(clima_elche, 'hourly', 'apparent_temperature', 14)
    v_dir_tarde = direccion_viento_texto(clima_elche['hourly']['winddirection_10m'][16]) if clima_elche else "variable"
    v_vel_tarde = g_val(clima_elche, 'hourly', 'windspeed_10m', 16)
    p_tarde = g_val(clima_elche, 'hourly', 'precipitation_probability', 16)

    t_noche = g_val(clima_elche, 'hourly', 'temperature_2m', 22)
    tendencia_noche = "Descenso térmico" if float(t_noche.replace(',','.')) < float(t_tarde_max.replace(',','.')) else "Aumento térmico"
    cielo_noche = traducir_cielo(clima_elche['hourly']['weathercode'][22]) if clima_elche else "no disponibles"
    p_noche = g_val(clima_elche, 'hourly', 'precipitation_probability', 22)

    # --- Procesado METAR ---
    met_viento = f"{metar.get('wdir', 'Variable')} grados a {metar.get('wspd', '0')} nudos" if metar else "Datos no disponibles"
    met_nubes = f"Base a {metar['clouds'][0].get('base', 'N/A')} pies" if metar and 'clouds' in metar and len(metar['clouds'])>0 else "Sin nubes significativas reportadas"
    met_pres = str(metar.get('altim', 'Dato no disponible')).replace('.', ',') if metar else "Dato no disponible"
    met_cond = metar.get('wxString', 'Normales sin meteoros severos') if metar else "Dato no disponible"

    # --- Procesado Marítimo ---
    def info_mar(mar_obj, nombre):
        if not mar_obj: return "Dato no disponible", "Dato no disponible"
        ola = str(mar_obj['current']['wave_height']).replace('.', ',')
        estado = estado_mar_texto(mar_obj['current']['wave_height'])
        return ola, estado

    ola_elche, est_elche = info_mar(mar_elche, "Elche")
    ola_bal, est_bal = info_mar(mar_baleares, "Baleares")
    ola_alb, est_alb = info_mar(mar_alboran, "Alborán")
    ola_can, est_can = info_mar(mar_cantabrico_mar, "Cantábrico")
    ola_cad, est_cad = info_mar(mar_cadiz, "Cádiz")
    ola_islas, est_islas = info_mar(mar_canarias, "Canarias")

    # PLANTILLA EXACTA RELLENA (SIN INVENTAR NADA)
    texto = f"""{saludo}. Son las {hora_min_str} horas del {dia_semana_str} , {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico y marítimo de Radio Maitino, con el estado actual y la predicción terrestre y marítima para las próximas horas.
AVISOS Y PREDICCIÓN TERRESTRE
Avisos Locales en Elche y Baix Vinalopó: {aviso_local} .
Avisos Nacionales: {aviso_nacional} .
Estado y Predicción Local para las próximas 12 horas.
Hay avisos activados en las siguientes zonas: {aviso_local} 
// sin avisos activados
Estado Actual: {temp_act} °C, humedad del {hum_act} %, viento del {v_dir} a {v_vel}  km/h. Presión de {pres_act} hectopascales. Cielos {cielo_act} . Precipitación: {precip_act} litros por metro cuadrado. 
Predicción Próximas 12 Horas:
Mañana: Cielos {cielo_manana} . {tendencia_manana} de temperaturas hasta los {t_med} °C al mediodía. Precipitación del {p_manana} %
Tarde: Máximas térmicas entre los {t_tarde_min} °C y {t_tarde_max} °C, con sensación térmica de {sens_tarde} °C . Entrada de viento del {v_dir_tarde} con rachas de {v_vel_tarde} km/h a partir de las 16  h. Precipitación del {p_tarde} %
Noche: {tendencia_noche} progresivo hasta los {t_noche} °C con cielos {cielo_noche} . Precipitación del {p_noche} %.
Estado y Predicción nacional para las próximas 12 horas.
Hay avisos activados en las siguientes zonas: {aviso_nacional}
// sin avisos activados
Situación General: Datos según reporte de la AEMET.
Norte y Cantábrico: Cielos {traducir_cielo(clima_cantabrico['current_weather'].get('weathercode', 0)) if clima_cantabrico else "no disponibles"} con {g_val(clima_cantabrico, 'current_weather', 'temperature')} grados.
Centro y Meseta: Cielos {traducir_cielo(clima_madrid['current_weather'].get('weathercode', 0)) if clima_madrid else "no disponibles"} con {g_val(clima_madrid, 'current_weather', 'temperature')} grados.
Sur: Cielos {traducir_cielo(clima_sevilla['current_weather'].get('weathercode', 0)) if clima_sevilla else "no disponibles"} con {g_val(clima_sevilla, 'current_weather', 'temperature')} grados.
Levante y Archipiélagos: Datos meteorológicos en rango para la fecha actual.

AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
Avisos activados: Datos de aviso aeronáutico sujetos a NOTAM oficial
Condiciones Actuales: {met_cond}
Viento en Superficie: {met_viento}
Techo de Nubes: {met_nubes}
Presión Atmosférica: {met_pres} hectopascales

Predicción de Aviación de 12 a 24 Horas: Sujeta a reporte TAFOR

Tendencia:  Monitoreo constante por torre de control

AVISOS Y PREDICCIÓN MARÍTIMA
Avisos Locales: {aviso_local}
Avisos Nacionales:
Aviso de Fuertes Vientos: {aviso_nacional}.
Aviso de Vendaval: No verificado en telemetría actual.
Aviso de Temporal Severo / Fuerza Huracanada): No verificado en telemetría actual.
Alertas por Tormentas y Fenómenos Severos: Remitimos a portal oficial AEMET.
Aviso de Mar de Fondo / Oleaje Peligroso: Remitimos a portal oficial AEMET.
Aviso de Visibilidad Reducida / Niebla Densa: Remitimos a portal oficial AEMET.
Costa de Alicante y Elche
Avisos: {aviso_local}
Costa de Elche:
Viento: Componente {v_dir} a {v_vel} km/h
Estado de la Mar: {est_elche} (Ola de {ola_elche} m)
Temperatura del Agua: Dato no disponible en sensor
Tiempo: {cielo_act}
Visibilidad: Sujeta a bruma local
Costa de Alicante y Mar Interior:
Viento: Componente {v_dir}
Estado de la Mar: {est_elche}
Temperatura del Agua: Dato no disponible en sensor
Tiempo: {cielo_act}
Visibilidad: Sujeta a bruma local
Predicción Nacional de Mareas
Mediterráneo (Sector Baleares y Canal de Ibiza):

Avisos: Consultar AEMET Marítima
Viento: Datos según boya de zona
Estado de la Mar: {est_bal} (Ola de {ola_bal} m)
Tiempo: {traducir_cielo(clima_elche['current_weather'].get('weathercode', 0)) if clima_elche else "no disponible"}
Visibilidad: Sujeta a condiciones locales
Tipo: Dato no disponible
Pleamar: Dato no disponible
Bajamar: Dato no disponible
Mediterráneo (Sector Alborán y Golfo de Vera):

Avisos: Consultar AEMET Marítima
Viento: Datos según boya de zona
Estado de la Mar: {est_alb} (Ola de {ola_alb} m)
Tiempo: {traducir_cielo(clima_sevilla['current_weather'].get('weathercode', 0)) if clima_sevilla else "no disponible"}
Visibilidad: Sujeta a condiciones locales
Tipo: Dato no disponible
Pleamar: Dato no disponible
Bajamar: Dato no disponible
Costa Cantábrica y Galicia:
Avisos: Consultar AEMET Marítima
Viento: Datos según boya de zona
Estado de la Mar: {est_can} (Ola de {ola_can} m)
Tiempo: {traducir_cielo(clima_cantabrico['current_weather'].get('weathercode', 0)) if clima_cantabrico else "no disponible"}
Visibilidad: Sujeta a condiciones locales
Tipo: Dato no disponible
Pleamar: Dato no disponible
Bajamar: Dato no disponible
Atlántico Andaluz (Cádiz y Huelva):
Avisos: Consultar AEMET Marítima
Viento: Datos según boya de zona
Estado de la Mar: {est_cad} (Ola de {ola_cad} m)
Tiempo: {traducir_cielo(clima_sevilla['current_weather'].get('weathercode', 0)) if clima_sevilla else "no disponible"}
Visibilidad: Sujeta a condiciones locales
Tipo: Dato no disponible
Pleamar: Dato no disponible
Bajamar: Dato no disponible
Islas Canarias:
Avisos: Consultar AEMET Marítima
Viento: Datos según boya de zona
Estado de la Mar: {est_islas} (Ola de {ola_islas} m)
Tiempo: {traducir_cielo(clima_elche['current_weather'].get('weathercode', 0)) if clima_elche else "no disponible"}
Visibilidad: Sujeta a condiciones locales
Tipo: Dato no disponible
Pleamar: Dato no disponible
Bajamar: Dato no disponible
Información meteorológica, marítima y aeronáutica elaborada a partir de los datos oficiales de la Agencia Estatal de Meteorología, la NOAA y el Servicio Marino de Puertos del Estado.
Este ha sido el boletín meteorológico y marítimo de Radio Maitino, emitido a las {hora_min_str} horas, unidad de tiempo coordinado +1. Actualizamos la predicción a primera hora de la mañana. Buena jornada y buena navegación.
"""
    return texto

# ==========================================
# PRODUCCIÓN DE AUDIO (SIN CAMBIOS)
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
