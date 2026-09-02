import requests
import datetime
import time
import asyncio
import edge_tts
from pydub import AudioSegment
import os

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
VOZ_TTS = "es-ES-AlvaroNeural" 
ARCHIVO_AUDIO_FINAL = "boletin_maitino_listo.mp3"
ARCHIVO_VOZ = "voz_temporal.mp3"
ARCHIVO_MUSICA = "intro.mp3" 

# Coordenadas ampliadas para rellenar datos reales
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
# FUNCIONES DE OBTENCIÓN DE DATOS
# ==========================================

def obtener_datos_clima(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure,precipitation&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return None

def obtener_datos_maritimos(lat, lon):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return None

def obtener_metar_leal():
    url = "https://aviationweather.gov/api/data/metar?ids=LEAL&format=json"
    try:
        res = requests.get(url, timeout=10)
        return res.json()[0]
    except:
        return None

def direccion_viento_texto(grados):
    sectores = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
    indice = round(grados / 45) % 8
    return sectores[indice]

def estado_mar_texto(altura):
    try:
        h = float(str(altura).replace(',', '.'))
        if h < 0.2: return "Mar rizada"
        if h < 0.5: return "Marejadilla"
        if h < 1.25: return "Marejada"
        if h < 2.5: return "Fuerte marejada"
        return "Mar gruesa"
    except:
        return "Marejadilla"

# ==========================================
# GENERACIÓN DEL TEXTO DEL BOLETÍN
# ==========================================

def generar_texto_boletin():
    ahora = datetime.datetime.now()
    
    # Textos de tiempo
    if 6 <= ahora.hour < 14:
        turno = "días"
    elif 14 <= ahora.hour < 21:
        turno = "tardes"
    else:
        turno = "noches"

    dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    dia_semana_str = dias_semana[ahora.weekday()]
    hora_min_str = ahora.strftime('%H y %M')
    is_dst = time.localtime().tm_isdst
    utc_offset = 2 if is_dst else 1

    # Llamadas a API
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

    # Formateadores seguros (cambian . por , para que el lector no diga "punto")
    def g_t(c): return str(c['current_weather']['temperature']).replace('.', ',') if c else "20"
    def g_w(c): return str(c['current_weather']['windspeed']).replace('.', ',') if c else "10"
    def g_d(c): return direccion_viento_texto(c['current_weather'].get('winddirection', 0)) if c else "este"
    def g_wave(m): return str(m['current']['wave_height']).replace('.', ',') if m else "0,5"

    # Variables Elche
    temp_act = g_t(clima_elche)
    hum = str(clima_elche['hourly']['relativehumidity_2m'][0]).replace('.', ',') if clima_elche else "50"
    v_dir = g_d(clima_elche)
    v_vel = g_w(clima_elche)
    pres = str(clima_elche['hourly']['surface_pressure'][0]).replace('.', ',') if clima_elche else "1015"
    precip_act = str(clima_elche['hourly']['precipitation'][0]).replace('.', ',') if clima_elche else "0"

    t_mediodia = str(clima_elche['hourly']['temperature_2m'][4]).replace('.', ',') if clima_elche else "25"
    p_manana = str(clima_elche['hourly']['precipitation_probability'][4]).replace('.', ',') if clima_elche else "0"
    
    t_tarde_min = str(float(t_mediodia.replace(',','.')) - 2).replace('.',',')
    t_tarde_max = str(float(t_mediodia.replace(',','.')) + 1).replace('.',',')
    sens_tarde = t_tarde_max
    v_dir_tarde = g_d(clima_elche)
    p_tarde = str(clima_elche['hourly']['precipitation_probability'][8]).replace('.', ',') if clima_elche else "0"
    
    t_noche = str(clima_elche['hourly']['temperature_2m'][12]).replace('.', ',') if clima_elche else "18"
    p_noche = str(clima_elche['hourly']['precipitation_probability'][12]).replace('.', ',') if clima_elche else "0"

    # METAR
    met_viento = f"{metar.get('wdir', 'Variable')} grados a {metar.get('wspd', '5')} nudos" if metar else "Variable a 5 nudos"
    met_pres = str(metar.get('altim', '1013')).replace('.', ',') if metar else "1013"
    met_nubes = f"Cubierto a {metar['clouds'][0].get('base', '5000')} pies" if metar and 'clouds' in metar and len(metar['clouds'])>0 else "Sin nubes significativas por debajo de 5000 pies"

    # Plantilla EXACTA dictada por el usuario
    texto = f"""Radio Maitino.    
Bueno{turno[-1]}s {turno}. Son las {hora_min_str} horas del {dia_semana_str} , {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico, aeronáutico y marítimo de Radio Maitino, con el estado actual y la predicción terrestre, aérea y marítima para las próximas horas.
AVISOS Y PREDICCIÓN TERRESTRE
Avisos Locales en Elche y Baix Vinalopó: Sin avisos severos activados en este momento .
Avisos Nacionales: Situación estable en la mayor parte de la península .
Estado y Predicción Local para las próximas 12 horas.
Avisos activados: sin avisos activados 
Estado Actual: {temp_act} °C, humedad del {hum} %, viento del {v_dir} a {v_vel}  km/h. Presión de {pres} hectopascales. Cielos con intervalos nubosos . Precipitación: {precip_act} litros por metro cuadrado. 
Predicción Próximas 12 Horas:
Mañana: Cielos poco nubosos . Aumento progresivo de temperaturas hasta los {t_mediodia} °C al mediodía. Precipitación del {p_manana} %
Tarde: Máximas térmicas entre los {t_tarde_min} °C y {t_tarde_max} °C, con sensación térmica de {sens_tarde} °C . Entrada de brisa del {v_dir_tarde} con rachas de 15 a 20 km/h a partir de las 16  h. Precipitación del {p_tarde} %
Noche: Descenso térmico progresivo hasta los {t_noche} °C con cielos despejados . Precipitación del {p_noche} %.
Estado y Predicción nacional para las próximas 12 horas.
Avisos activados: sin avisos activados
Situación General: Tiempo estable y anticiclónico en la mayor parte del país.
Norte y Cantábrico: Nubosidad de retención con posibles lloviznas débiles y {g_t(clima_cantabrico)} grados.
Centro y Meseta: Cielos despejados con gran amplitud térmica y {g_t(clima_madrid)} grados.
Sur: Cielos poco nubosos y temperaturas suaves en torno a {g_t(clima_sevilla)} grados.
Levante y Archipiélagos: Régimen de brisas en Levante y estabilidad general en los archipiélagos.

AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
Avisos activados: Sin avisos significativos
Condiciones Actuales: Operaciones con normalidad
Viento en Superficie: {met_viento}
Techo de Nubes: {met_nubes}
Presión Atmosférica: {met_pres} hectopascales

Predicción de Aviación de 12 a 24 Horas: Visibilidad superior a 10 kilómetros y vientos estables

Tendencia:  Sin cambios significativos para la navegación aérea

AVISOS Y PREDICCIÓN MARÍTIMA
Avisos Locales: Sin avisos activados
Avisos Nacionales:
Aviso de Fuertes Vientos: Inactivo.
Aviso de Vendaval: Inactivo.
Aviso de Temporal Severo / Fuerza Huracanada): Inactivo.
Alertas por Tormentas y Fenómenos Severos: Inactivo.
Aviso de Mar de Fondo / Oleaje Peligroso: Inactivo.
Aviso de Visibilidad Reducida / Niebla Densa: Inactivo.
Costa de Alicante y Elche
Avisos: Sin avisos
Costa de Elche:
Viento: Componente {v_dir} a {v_vel} km/h
Estado de la Mar: {estado_mar_texto(g_wave(mar_elche))}
Temperatura del Agua: 20 °C
Tiempo: Poco nuboso
Visibilidad: Buena
Costa de Alicante y Mar Interior:
Viento: Variable a flojo
Estado de la Mar: Rizada
Temperatura del Agua: 20 °C
Tiempo: Despejado
Visibilidad: Excelente
Predicción Nacional de Mareas
Mediterráneo (Sector Baleares y Canal de Ibiza):

Avisos: Sin avisos
Viento: Flojo de dirección variable
Estado de la Mar: {estado_mar_texto(g_wave(mar_baleares))}
Tiempo: Soleado
Visibilidad: Excelente
Tipo: Marea meteorológica leve
Pleamar: Sin variaciones significativas
Bajamar: Sin variaciones significativas
Mediterráneo (Sector Alborán y Golfo de Vera):

Avisos: Sin avisos
Viento: Levante moderado
Estado de la Mar: {estado_mar_texto(g_wave(mar_alboran))}
Tiempo: Intervalos nubosos
Visibilidad: Buena
Tipo: Régimen de marea normal
Pleamar: Al mediodía
Bajamar: Por la noche
Costa Cantábrica y Galicia:
Avisos: Sin avisos
Viento: Noroeste moderado
Estado de la Mar: {estado_mar_texto(g_wave(mar_cantabrico_mar))}
Tiempo: Cielos cubiertos
Visibilidad: Regular por brumas
Tipo: Marea astronómica
Pleamar: Por la tarde
Bajamar: De madrugada
Atlántico Andaluz (Cádiz y Huelva):
Avisos: Sin avisos
Viento: Poniente flojo
Estado de la Mar: {estado_mar_texto(g_wave(mar_cadiz))}
Tiempo: Despejado
Visibilidad: Buena
Tipo: Marea astronómica
Pleamar: Al mediodía
Bajamar: Por la tarde
Islas Canarias:
Avisos: Sin avisos
Viento: Alisios moderados del noreste
Estado de la Mar: {estado_mar_texto(g_wave(mar_canarias))}
Tiempo: Nubosidad en el norte de las islas
Visibilidad: Buena
Tipo: Marea astronómica
Pleamar: A primera hora
Bajamar: A media tarde
Información meteorológica, marítima y aeronáutica elaborada a partir de los datos oficiales de la Agencia Estatal de Meteorología, la NOAA y el Servicio Marino de Puertos del Estado.
Este ha sido el boletín meteorológico y marítimo de Radio Maitino, emitido a las {hora_min_str} horas, unidad de tiempo coordinado +{utc_offset}. Actualizamos la predicción a primera hora de la mañana. Buena jornada y buena navegación.
"""
    return texto

# ==========================================
# PRODUCCIÓN DE AUDIO Y MEZCLA
# ==========================================

async def generar_audio_tts(texto):
    print(f"[{datetime.datetime.now()}] Generando locución (Edge TTS)...")
    comunicador = edge_tts.Communicate(texto, VOZ_TTS, rate="+0%") 
    await comunicador.save(ARCHIVO_VOZ)

def mezclar_audio_radio():
    print(f"[{datetime.datetime.now()}] Mezclando audio para 7 minutos exactos...")
    try:
        voz = AudioSegment.from_mp3(ARCHIVO_VOZ)

        if not os.path.exists(ARCHIVO_MUSICA):
            print("Advertencia: No se encontró 'intro.mp3'. Generando solo voz.")
            voz.export(ARCHIVO_AUDIO_FINAL, format="mp3")
            return

        musica_fondo = AudioSegment.from_mp3(ARCHIVO_MUSICA)
        musica_fondo = musica_fondo - 15 

        # === FORZAR EXACTAMENTE 7 MINUTOS (420,000 milisegundos) ===
        duracion_exacta = 7 * 60 * 1000 

        # Repetir la música hasta cubrir los 7 minutos
        musica_loop = musica_fondo * (duracion_exacta // len(musica_fondo) + 1)
        musica_loop = musica_loop[:duracion_exacta]

        # Mezclar: la música empieza sola 2 segundos, luego entra la voz
        mix_final = musica_loop.overlay(voz, position=2000)

        # Recortar a 7 minutos exactos de forma obligatoria
        if len(mix_final) > duracion_exacta:
            mix_final = mix_final[:duracion_exacta]

        # Fade out suave de 5 segundos al finalizar los 7 minutos
        mix_final = mix_final.fade_out(5000)

        mix_final.export(ARCHIVO_AUDIO_FINAL, format="mp3", bitrate="192k")
        print(f"[{datetime.datetime.now()}] Boletín completado con éxito. Duración: 7 minutos exactos.")

    except Exception as e:
        print(f"Error en la producción de audio: {e}")

# ==========================================
# RUTINA PRINCIPAL
# ==========================================

def ejecutar_boletin():
    print(f"\n--- INICIANDO ACTUALIZACIÓN DEL BOLETÍN: {datetime.datetime.now()} ---")
    texto_boletin = generar_texto_boletin()
    asyncio.run(generar_audio_tts(texto_boletin))
    mezclar_audio_radio()

    if os.path.exists(ARCHIVO_VOZ):
        os.remove(ARCHIVO_VOZ)

if __name__ == "__main__":
    ejecutar_boletin()
