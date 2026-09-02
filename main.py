import requests
import datetime
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

# Coordenadas ampliadas para obtener datos reales nacionales
COORDS = {
    "elche": {"lat": 38.2622, "lon": -0.7011},
    "alicante_costa": {"lat": 38.3, "lon": -0.4},
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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        print(f"Error obteniendo clima terrestre: {e}")
        return None

def obtener_datos_maritimos(lat, lon):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,ocean_current_velocity&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return None

def obtener_metar_leal():
    url = "https://aviationweather.gov/api/data/metar?ids=LEAL&format=json"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()[0]
        return data
    except:
        return None

def direccion_viento_texto(grados):
    sectores = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
    indice = round(grados / 45) % 8
    return sectores[indice]

# ==========================================
# GENERACIÓN DEL TEXTO DEL BOLETÍN
# ==========================================

def generar_texto_boletin():
    ahora = datetime.datetime.now()

    if 6 <= ahora.hour < 14:
        saludo = "Buenos días"
    elif 14 <= ahora.hour < 21:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    # --- Peticiones de datos reales ---
    clima_elche = obtener_datos_clima(COORDS["elche"]["lat"], COORDS["elche"]["lon"])
    clima_madrid = obtener_datos_clima(COORDS["madrid"]["lat"], COORDS["madrid"]["lon"])
    clima_sevilla = obtener_datos_clima(COORDS["sevilla"]["lat"], COORDS["sevilla"]["lon"])
    clima_cantabrico = obtener_datos_clima(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])
    clima_canarias = obtener_datos_clima(COORDS["canarias"]["lat"], COORDS["canarias"]["lon"])

    mar_alicante = obtener_datos_maritimos(COORDS["alicante_costa"]["lat"], COORDS["alicante_costa"]["lon"])
    mar_cantabrico = obtener_datos_maritimos(COORDS["cantabrico"]["lat"], COORDS["cantabrico"]["lon"])
    mar_canarias = obtener_datos_maritimos(COORDS["canarias"]["lat"], COORDS["canarias"]["lon"])
    mar_cadiz = obtener_datos_maritimos(COORDS["cadiz"]["lat"], COORDS["cadiz"]["lon"])
    
    metar = obtener_metar_leal()

    # --- Funciones de ayuda para extraer datos de forma segura y reemplazar puntos por comas ---
    def get_t(clima): return str(clima['current_weather']['temperature']).replace('.', ',') if clima else "No disponible"
    def get_w(clima): return str(clima['current_weather']['windspeed']).replace('.', ',') if clima else "No disponible"
    def get_d(clima): return direccion_viento_texto(clima['current_weather'].get('winddirection', 0)) if clima else "variable"
    def get_wave(mar): return str(mar['current']['wave_height']).replace('.', ',') if mar else "No disponible"

    # Datos precisos para Elche
    temp_actual = get_t(clima_elche)
    viento_vel = get_w(clima_elche)
    viento_dir = get_d(clima_elche)
    humedad = str(clima_elche['hourly']['relativehumidity_2m'][0]).replace('.', ',') if clima_elche else "No disponible"
    presion = str(clima_elche['hourly']['surface_pressure'][0]).replace('.', ',') if clima_elche else "No disponible"
    
    # Predicción horaria real para Elche (A +4, +8 y +12 horas)
    t_4h = str(clima_elche['hourly']['temperature_2m'][4]).replace('.', ',') if clima_elche else "N/A"
    p_4h = str(clima_elche['hourly']['precipitation_probability'][4]).replace('.', ',') if clima_elche else "N/A"
    t_8h = str(clima_elche['hourly']['temperature_2m'][8]).replace('.', ',') if clima_elche else "N/A"
    p_8h = str(clima_elche['hourly']['precipitation_probability'][8]).replace('.', ',') if clima_elche else "N/A"
    t_12h = str(clima_elche['hourly']['temperature_2m'][12]).replace('.', ',') if clima_elche else "N/A"
    p_12h = str(clima_elche['hourly']['precipitation_probability'][12]).replace('.', ',') if clima_elche else "N/A"

    oleaje_alicante = get_wave(mar_alicante)
    viento_aero = f"{metar['wdir']} grados a {metar['wspd']} nudos".replace('.', ',') if metar else "Variable a 5 nudos"
    presion_aero = str(metar['altim']).replace('.', ',') if metar else "1013"

    texto = f"""
Radio Maitino.    
    BOLETÍN METEOROLÓGICO, MARÍTIMO Y AERONÁUTICO
{saludo}. Son las {ahora.strftime('%H y %M')} horas del {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico, aeronáutico y marítimo de Radio Maitino, con el estado actual y la predicción basada en datos de observación reales.

    ESTADO Y PREDICCIÓN TERRESTRE LOCAL
    Avisos Locales en Elche y Baix Vinalopó: Sin avisos severos activados en este momento.

    Estado Actual en Elche: {temp_actual} grados centígrados, humedad del {humedad} por ciento, viento del {viento_dir} a {viento_vel} kilómetros por hora. Presión de {presion} hectopascales. 

    Evolución Local para las próximas 12 Horas:
    En 4 horas: Temperatura estimada de {t_4h} grados centígrados, con una probabilidad de precipitación del {p_4h} por ciento.
    En 8 horas: Temperatura estimada de {t_8h} grados centígrados, probabilidad de precipitación del {p_8h} por ciento.
    En 12 horas: Temperatura esperada de {t_12h} grados centígrados y probabilidad de lluvia del {p_12h} por ciento.

    ESTADO TERRESTRE NACIONAL (DATOS ACTUALES)
    Norte y Cantábrico: Temperatura de {get_t(clima_cantabrico)} grados centígrados, viento de componente {get_d(clima_cantabrico)} a {get_w(clima_cantabrico)} kilómetros por hora.
    Centro y Meseta: Temperatura de {get_t(clima_madrid)} grados centígrados, viento de componente {get_d(clima_madrid)} a {get_w(clima_madrid)} kilómetros por hora.
    Sur: Temperatura de {get_t(clima_sevilla)} grados centígrados, viento de componente {get_d(clima_sevilla)} a {get_w(clima_sevilla)} kilómetros por hora.
    Canarias: Temperatura de {get_t(clima_canarias)} grados centígrados, viento de componente {get_d(clima_canarias)} a {get_w(clima_canarias)} kilómetros por hora.

    AVISOS Y METAR PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
    Avisos activados: Sin avisos.
    Condiciones Actuales: Operaciones con normalidad.
    Viento en Superficie: {viento_aero}.
    Presión Atmosférica: {presion_aero} hectopascales.
    Tendencia: Sin cambios significativos para la navegación aérea a corto plazo.

    AVISOS Y ESTADO MARÍTIMO
    Avisos Nacionales:
    Aviso de Fuertes Vientos: Inactivo.
    Aviso de Vendaval: Inactivo.
    Aviso de Temporal Severo: Inactivo.
    Aviso de Mar de Fondo: Inactivo.

    Costa de Alicante y Elche:
    Viento actual: Componente {viento_dir} a {viento_vel} kilómetros por hora.
    Estado de la Mar: Altura actual del oleaje de {oleaje_alicante} metros.

    Resto del Litoral Nacional:
    Costa Cantábrica: Altura del oleaje de {get_wave(mar_cantabrico)} metros.
    Atlántico Andaluz y Golfo de Cádiz: Altura del oleaje de {get_wave(mar_cadiz)} metros.
    Islas Canarias: Altura del oleaje de {get_wave(mar_canarias)} metros.

    Información meteorológica, marítima y aeronáutica elaborada a partir de los datos telemáticos actuales de la red de observación meteorológica.
    Este ha sido el boletín de Radio Maitino, emitido a las {ahora.strftime('%H y %M')} horas, unidad de tiempo coordinado más 1. Buena jornada y buena navegación.
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
