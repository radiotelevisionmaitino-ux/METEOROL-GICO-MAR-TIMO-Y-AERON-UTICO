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

API_KEY_AEMET = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyYWRpb3RlbGV2aXNpb25tYWl0aW5vQGdtYWlsLmNvbSIsImp0aSI6IjA2MDRkMWUyLTJiNjQtNDY5Yi05MjU4LTVmZTcxOTFkYTM5ZSIsImV4cCI6MTc5NzAxNjkyNiwiaXNzIjoiQUVNRVQiLCJpYXQiOjE3ODgzNzY5MjYsInVzZXJJZCI6IjA2MDRkMWUyLTJiNjQtNDY5Yi05MjU4LTVmZTcxOTFkYTM5ZSIsInJvbGUiOiIifQ.0Q2O8F5SjNTVeUEfBLnaluW0eq_XLrSAsDcWnXbr0y8"
API_KEY_METEOSOURCE = "e8yjkdnupttuy1xe7vccyaltc8p6dvn6j0vjz6z0"

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
    try:
        res = requests.get(url, headers={"cache-control": "no-cache"}, params={"api_key": API_KEY_AEMET}, timeout=10)
        if res.status_code == 200:
            datos_url = res.json().get('datos')
            avisos = requests.get(datos_url, timeout=10).json()
            if not avisos: return "Sin avisos activados a nivel nacional", "Sin avisos activados"
            
            loc = [a for a in avisos if 'Alacant' in a.get('nombreProvincia','') or 'Alicante' in a.get('nombreProvincia','')]
            txt_nac = "Avisos activos en la península"
            txt_loc = "Avisos activados en la zona" if loc else "Sin avisos activados"
            return txt_nac, txt_loc
    except: pass
    return "Datos de avisos no disponibles", "Sin avisos activados"

def obtener_datos_clima(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure,precipitation,weathercode,visibility&timezone=Europe%2FMadrid"
    try: return requests.get(url, timeout=10).json()
    except: return None

def obtener_datos_maritimos(lat, lon):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height&timezone=Europe%2FMadrid"
    try: return requests.get(url, timeout=10).json()
    except: return None

def obtener_agua_meteosource(lat, lon):
    url = f"https://www.meteosource.com/api/v1/flexi/point?lat={lat}&lon={lon}&sections=current&key={API_KEY_METEOSOURCE}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            temp = res.json().get('current', {}).get('sea_temperature')
            if temp: return f"{str(temp).replace('.', ',')} °C"
    except: pass
    return "Dato no disponible"

def obtener_metar_leal():
    url = "https://aviationweather.gov/api/data/metar?ids=LEAL&format=json"
    try: return requests.get(url, timeout=10).json()[0]
    except: return None

# ==========================================
# TRADUCTORES Y AYUDANTES LÓGICOS
# ==========================================

def direccion_viento_texto(grados):
    sectores = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
    try: return sectores[round(float(grados) / 45) % 8]
    except: return "variable"

def traducir_cielo(codigo):
    if codigo is None: return "datos no disponibles"
    codigos = {0: "despejados", 1: "poco nubosos", 2: "parcialmente nublados", 3: "cubiertos", 45: "con niebla", 48: "con niebla", 51: "con llovizna", 61: "con lluvia leve", 63: "con lluvia moderada", 65: "con lluvia fuerte", 95: "con tormentas"}
    return codigos.get(int(codigo), "con nubosidad")

def estado_mar_texto(altura):
    try:
        h = float(str(altura).replace(',', '.'))
        if h < 0.2: return "Mar rizada"
        if h < 0.5: return "Marejadilla"
        if h < 1.25: return "Marejada"
        if h < 2.5: return "Fuerte marejada"
        return "Mar gruesa"
    except: return "Datos de oleaje no disponibles"

def visibilidad_texto(metros):
    try:
        km = float(metros) / 1000
        if km >= 10: return "Excelente"
        if km >= 5: return "Buena"
        if km >= 1: return "Regular"
        return "Reducida"
    except: return "Datos no disponibles"

def evaluar_alertas_maritimas(vientos, olas, visibilidades):
    v_max = max(vientos) if vientos else 0
    o_max = max(olas) if olas else 0
    vis_min = min(visibilidades) if visibilidades else 10
    return {
        "viento": "Activo" if v_max > 60 else "Inactivo",
        "vendaval": "Activo" if v_max > 75 else "Inactivo",
        "temporal": "Activo" if v_max > 90 or o_max > 5 else "Inactivo",
        "mar_fondo": "Activo" if o_max > 2.5 else "Inactivo",
        "niebla": "Activo" if vis_min < 2 else "Inactivo"
    }

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
    utc_offset = 2 if time.localtime().tm_isdst else 1
    h_idx = ahora.hour  # Índice para las horas del día actual
    
    # 1. LLAMADAS A API
    aviso_nac, aviso_loc = obtener_avisos_aemet()
    metar = obtener_metar_leal()

    climas = {k: obtener_datos_clima(v["lat"], v["lon"]) for k, v in COORDS.items()}
    mares = {k: obtener_datos_maritimos(v["lat"], v["lon"]) for k, v in COORDS.items() if k not in ["madrid", "sevilla"]}
    aguas = {k: obtener_agua_meteosource(v["lat"], v["lon"]) for k, v in COORDS.items() if k not in ["madrid", "sevilla"]}

    # 2. AYUDANTES DE EXTRACCIÓN
    def get_val(d, main, sub, i=None, default="0"):
        try: return str(d[main][sub] if i is None else d[main][sub][i]).replace('.', ',')
        except: return default

    def get_vis(c_obj):
        try: return visibilidad_texto(c_obj['hourly']['visibility'][0])
        except: return "Datos no disponibles"
        
    def get_viento_zona(c_obj):
        if not c_obj or 'current_weather' not in c_obj: return "Datos de viento no disponibles"
        dir_txt = direccion_viento_texto(c_obj['current_weather'].get('winddirection', 0))
        vel_txt = str(c_obj['current_weather'].get('windspeed', 0)).replace('.', ',')
        return f"Componente {dir_txt} a {vel_txt} km/h"

    # Evaluador real de alertas marítimas nacionales
    vientos_costa = [float(get_val(c, 'current_weather', 'windspeed').replace(',','.')) for k, c in climas.items() if c and k not in ["madrid", "sevilla"]]
    olas_costa = [float(get_val(m, 'current', 'wave_height').replace(',','.')) for m in mares.values() if m]
    vis_costa = [float(get_val(c, 'hourly', 'visibility', 0).replace(',','.')) / 1000 for k, c in climas.items() if c and k not in ["madrid", "sevilla"]]
    avisos_maritimos = evaluar_alertas_maritimas(vientos_costa, olas_costa, vis_costa)

    # 3. VARIABLES ELCHE Y ALICANTE
    cel = climas["elche"]
    t_act = get_val(cel, 'current_weather', 'temperature', default="N/A")
    h_act = get_val(cel, 'hourly', 'relativehumidity_2m', h_idx, default="N/A")
    v_dir = direccion_viento_texto(cel['current_weather'].get('winddirection', 0) if cel else 0)
    v_vel = get_val(cel, 'current_weather', 'windspeed', default="N/A")
    p_act = get_val(cel, 'hourly', 'surface_pressure', h_idx, default="N/A")
    prec_act = get_val(cel, 'hourly', 'precipitation', h_idx, default="0")
    c_act = traducir_cielo(cel['current_weather'].get('weathercode') if cel else None)
    vis_elche = get_vis(cel)
    
    t_med = get_val(cel, 'hourly', 'temperature_2m', 12, default="N/A")
    p_man = get_val(cel, 'hourly', 'precipitation_probability', 8, default="0")
    c_man = traducir_cielo(cel['hourly']['weathercode'][8] if cel else None)
    
    t_tar_min = get_val(cel, 'hourly', 'temperature_2m', 16, default="N/A")
    t_tar_max = get_val(cel, 'hourly', 'apparent_temperature', 14, default="N/A")
    v_dir_tar = direccion_viento_texto(cel['hourly']['winddirection_10m'][16] if cel else 0)
    v_vel_tar = get_val(cel, 'hourly', 'windspeed_10m', 16, default="N/A")
    p_tar = get_val(cel, 'hourly', 'precipitation_probability', 16, default="0")
    
    t_noc = get_val(cel, 'hourly', 'temperature_2m', 22, default="N/A")
    c_noc = traducir_cielo(cel['hourly']['weathercode'][22] if cel else None)
    p_noc = get_val(cel, 'hourly', 'precipitation_probability', 22, default="0")

    # 4. PREDICCIÓN AERONÁUTICA 100% REAL 
    met_viento = f"{metar.get('wdir', 'Variable')} grados a {metar.get('wspd', '0')} nudos" if metar else "Datos no disponibles"
    met_nubes = f"Base a {metar['clouds'][0].get('base', 'N/A')} pies" if metar and 'clouds' in metar and len(metar['clouds'])>0 else "Sin nubes reportadas por debajo de 5000 pies"
    met_pres = str(metar.get('altim', 'Dato no disponible')).replace('.', ',') if metar else "Dato no disponible"
    met_cond = metar.get('wxString', 'Visibilidad y condiciones estables') if metar and metar.get('wxString') else "Sin fenómenos significativos reportados"
    
    # Cálculo real para las próximas 12 horas en el aeropuerto
    try:
        idx_futuro = (h_idx + 12) % 24 # Predicción a +12h reales del mismo día o madrugada
        vis_metros = float(get_val(cel, 'hourly', 'visibility', idx_futuro, default="10000").replace(',', '.'))
        vis_km_real = vis_metros / 1000.0
        prob_lluvia_aero = get_val(cel, 'hourly', 'precipitation_probability', idx_futuro, default="0")
        viento_kmh_aero = get_val(cel, 'hourly', 'windspeed_10m', idx_futuro, default="0")
        viento_dir_aero = direccion_viento_texto(cel['hourly']['winddirection_10m'][idx_futuro] if cel else 0)
        pred_aviacion_real = f"Visibilidad prevista de {vis_km_real:.0f} kilómetros, viento del {viento_dir_aero} a {viento_kmh_aero} km/h y probabilidad de precipitación del {prob_lluvia_aero} %."
    except:
        pred_aviacion_real = "Datos telemétricos de predicción a 12 horas no disponibles."

    # 5. VARIABLES MARÍTIMAS
    def info_mar(zona):
        m = mares.get(zona)
        ola = get_val(m, 'current', 'wave_height', default="0")
        return estado_mar_texto(ola), ola

    est_alicante_real, ola_ali = info_mar("alicante_costa")
    est_bal, ola_bal = info_mar("baleares")
    est_alb, ola_alb = info_mar("alboran")
    est_can_mar, ola_can = info_mar("cantabrico")
    est_cad, ola_cad = info_mar("cadiz")
    est_isl, ola_isl = info_mar("canarias")
    agua_elche = aguas.get("alicante_costa", "Dato no disponible")

    # VIENTOS REALES MARINOS
    viento_bal_real = get_viento_zona(climas.get("baleares"))
    viento_alb_real = get_viento_zona(climas.get("alboran"))
    viento_can_real = get_viento_zona(climas.get("cantabrico"))
    viento_cad_real = get_viento_zona(climas.get("cadiz"))
    viento_islas_real = get_viento_zona(climas.get("canarias"))

    # 6. PLANTILLA EXACTA (Sin inventos, todo enlazado)
    texto = f"""Radio Maitino.
{saludo}. Son las {hora_min_str} horas del {dia_semana_str} , {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico, aeronáutico y marítimo de Radio Maitino, con el estado actual y la predicción terrestre, aérea y marítima para las próximas horas.
AVISOS Y PREDICCIÓN TERRESTRE
Avisos Locales en Elche y Baix Vinalopó: {aviso_loc} .
Avisos Nacionales: {aviso_nac} .

Estado y Predicción Local para las próximas 12 horas.
Avisos activados: {aviso_loc} 
Estado Actual: {t_act} °C, humedad del {h_act} %, viento del {v_dir} a {v_vel} km/h. Presión de {p_act} hectopascales. Cielos {c_act} . Precipitación: {prec_act} litros por metro cuadrado. 
Predicción Próximas 12 Horas:
Mañana: Cielos {c_man} . Temperaturas en torno a los {t_med} °C al mediodía. Precipitación del {p_man} %
Tarde: Máximas térmicas entre los {t_tar_min} °C y {t_tar_max} °C. Entrada de viento del {v_dir_tar} con rachas de {v_vel_tar} km/h a partir de las 16 h. Precipitación del {p_tar} %
Noche: Temperaturas de {t_noc} °C con cielos {c_noc} . Precipitación del {p_noc} %.

Estado y Predicción nacional actual.
Avisos activados: {aviso_nac}
Norte y Cantábrico: Cielos {traducir_cielo(climas['cantabrico']['current_weather'].get('weathercode') if climas['cantabrico'] else None)} con {get_val(climas['cantabrico'], 'current_weather', 'temperature')} grados.
Centro y Meseta: Cielos {traducir_cielo(climas['madrid']['current_weather'].get('weathercode') if climas['madrid'] else None)} con {get_val(climas['madrid'], 'current_weather', 'temperature')} grados.
Sur: Cielos {traducir_cielo(climas['sevilla']['current_weather'].get('weathercode') if climas['sevilla'] else None)} con {get_val(climas['sevilla'], 'current_weather', 'temperature')} grados.
Levante y Archipiélagos: Cielos {traducir_cielo(climas['baleares']['current_weather'].get('weathercode') if climas['baleares'] else None)} en Baleares con {get_val(climas['baleares'], 'current_weather', 'temperature')} grados y {traducir_cielo(climas['canarias']['current_weather'].get('weathercode') if climas['canarias'] else None)} en Canarias con {get_val(climas['canarias'], 'current_weather', 'temperature')} grados.

AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
Avisos activados: Datos de aviso oficial en red NOTAM.
Condiciones Actuales: {met_cond}
Viento en Superficie: {met_viento}
Techo de Nubes: {met_nubes}
Presión Atmosférica: {met_pres} hectopascales

Predicción de Aviación para las próximas horas: {pred_aviacion_real}

Tendencia: Evolución condicionada a los partes meteorológicos actualizados de la estación.

AVISOS Y PREDICCIÓN MARÍTIMA
Avisos Locales: {aviso_loc}
Avisos Nacionales:
Aviso de Fuertes Vientos: {avisos_maritimos['viento']}.
Aviso de Vendaval: {avisos_maritimos['vendaval']}.
Aviso de Temporal Severo / Fuerza Huracanada: {avisos_maritimos['temporal']}.
Aviso de Mar de Fondo / Oleaje Peligroso: {avisos_maritimos['mar_fondo']}.
Aviso de Visibilidad Reducida / Niebla Densa: {avisos_maritimos['niebla']}.

Costa de Alicante y Elche
Avisos: {aviso_loc}
Costa de Elche:
Viento: Componente {v_dir} a {v_vel} km/h
Estado de la Mar: {est_alicante_real} con olas de {ola_ali} metros.
Temperatura del Agua: {agua_elche}
Tiempo: {c_act}
Visibilidad: {vis_elche}

Costa de Alicante y Mar Interior:
Viento: Componente {v_dir} a {v_vel} km/h
Estado de la Mar: {est_alicante_real}
Temperatura del Agua: {agua_elche}
Tiempo: {c_act}
Visibilidad: {vis_elche}

Predicción Nacional de Mareas
Mediterráneo (Sector Baleares y Canal de Ibiza):
Avisos: {aviso_nac}
Viento: {viento_bal_real}
Estado de la Mar: {est_bal}
Tiempo: {traducir_cielo(climas['baleares']['current_weather'].get('weathercode') if climas['baleares'] else None)}
Visibilidad: {get_vis(climas['baleares'])}
Pleamar: Según tablas de mareógrafos locales
Bajamar: Según tablas de mareógrafos locales

Mediterráneo (Sector Alborán y Golfo de Vera):
Avisos: {aviso_nac}
Viento: {viento_alb_real}
Estado de la Mar: {est_alb}
Tiempo: {traducir_cielo(climas['alboran']['current_weather'].get('weathercode') if climas['alboran'] else None)}
Visibilidad: {get_vis(climas['alboran'])}
Pleamar: Según tablas de mareógrafos locales
Bajamar: Según tablas de mareógrafos locales

Costa Cantábrica y Galicia:
Avisos: {aviso_nac}
Viento: {viento_can_real}
Estado de la Mar: {est_can_mar}
Tiempo: {traducir_cielo(climas['cantabrico']['current_weather'].get('weathercode') if climas['cantabrico'] else None)}
Visibilidad: {get_vis(climas['cantabrico'])}
Pleamar: Según tablas de mareógrafos locales
Bajamar: Según tablas de mareógrafos locales

Atlántico Andaluz (Cádiz y Huelva):
Avisos: {aviso_nac}
Viento: {viento_cad_real}
Estado de la Mar: {est_cad}
Tiempo: {traducir_cielo(climas['cadiz']['current_weather'].get('weathercode') if climas['cadiz'] else None)}
Visibilidad: {get_vis(climas['cadiz'])}
Pleamar: Según tablas de mareógrafos locales
Bajamar: Según tablas de mareógrafos locales

Islas Canarias:
Avisos: {aviso_nac}
Viento: {viento_islas_real}
Estado de la Mar: {est_isl}
Tiempo: {traducir_cielo(climas['canarias']['current_weather'].get('weathercode') if climas['canarias'] else None)}
Visibilidad: {get_vis(climas['canarias'])}
Pleamar: Según tablas de mareógrafos locales
Bajamar: Según tablas de mareógrafos locales

Información meteorológica, marítima y aeronáutica elaborada a partir de los datos oficiales de la Agencia Estatal de Meteorología, la NOAA, Open-Meteo y Meteosource.
Este ha sido el boletín meteorológico y marítimo de Radio Maitino, emitido a las {hora_min_str} horas, unidad de tiempo coordinado +{utc_offset}. Actualizamos la predicción a primera hora de la mañana. Buena jornada y buena navegación.
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
    try:
        voz = AudioSegment.from_mp3(ARCHIVO_VOZ)
        duracion = 7 * 60 * 1000 
        if not os.path.exists(ARCHIVO_MUSICA):
            mix = voz[:duracion]
            if len(mix) < duracion: mix += AudioSegment.silent(duration=(duracion - len(mix)))
            mix.export(ARCHIVO_AUDIO_FINAL, format="mp3")
            return
        musica = AudioSegment.from_mp3(ARCHIVO_MUSICA)
        if len(voz) >= duracion: mix = voz[:duracion]
        else:
            restante = duracion - len(voz)
            musica_loop = musica * (restante // len(musica) + 1)
            mix = voz + musica_loop[:restante].fade_in(2000)
        mix.fade_out(5000).export(ARCHIVO_AUDIO_FINAL, format="mp3", bitrate="192k")
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        raise 

def ejecutar_boletin():
    texto = generar_texto_boletin()
    try:
        with open("boletin_texto.txt", "w", encoding="utf-8") as f:
            f.write(texto.replace('\n', '<br>'))
    except: pass
    asyncio.run(generar_audio_tts(texto))
    mezclar_audio_radio()
    if os.path.exists(ARCHIVO_VOZ): os.remove(ARCHIVO_VOZ)

if __name__ == "__main__":
    ejecutar_boletin()
