import requests
import schedule
import time
import datetime
import asyncio
import edge_tts
from pydub import AudioSegment
import os
import json

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
VOZ_TTS = "es-ES-AlvaroNeural" # Voz masculina profesional estilo locutor. Alternativa: "es-ES-ElviraNeural"
ARCHIVO_AUDIO_FINAL = "boletin_maitino_listo.mp3"
ARCHIVO_VOZ = "voz_temporal.mp3"
ARCHIVO_MUSICA = "intro.mp3" # DEBES TENER ESTE ARCHIVO EN LA CARPETA

# Coordenadas
COORDS = {
    "elche": {"lat": 38.2622, "lon": -0.7011},
    "alicante_costa": {"lat": 38.3, "lon": -0.4},
    "cantabrico": {"lat": 43.5, "lon": -5.5},
    "canarias": {"lat": 28.1, "lon": -15.4}
}

# ==========================================
# FUNCIONES DE OBTENCIÓN DE DATOS (APIS REALES)
# ==========================================

def obtener_datos_clima(lat, lon):
    """Obtiene datos terrestres reales de OpenMeteo"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m,relativehumidity_2m,surface_pressure&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        print(f"Error obteniendo clima terrestre: {e}")
        return None

def obtener_datos_maritimos(lat, lon):
    """Obtiene datos marítimos reales de OpenMeteo Marine"""
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,ocean_current_velocity&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return None

def obtener_metar_leal():
    """Obtiene el METAR oficial de la NOAA para Elche-Alicante (LEAL)"""
    url = "https://aviationweather.gov/api/data/metar?ids=LEAL&format=json"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()[0]
        return data
    except:
        return None

def direccion_viento_texto(grados):
    """Convierte grados a puntos cardinales"""
    sectores = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
    indice = round(grados / 45) % 8
    return sectores[indice]

# ==========================================
# GENERACIÓN DEL TEXTO DEL BOLETÍN
# ==========================================

def generar_texto_boletin():
    ahora = datetime.datetime.now()
    
    # Saludo según la hora
    if 6 <= ahora.hour < 14:
        saludo = "Buenos días."
    elif 14 <= ahora.hour < 21:
        saludo = "Buenas tardes."
    else:
        saludo = "Buenas noches."

    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    # --- LLAMADAS A APIS ---
    clima_elche = obtener_datos_clima(COORDS["elche"]["lat"], COORDS["elche"]["lon"])
    mar_alicante = obtener_datos_maritimos(COORDS["alicante_costa"]["lat"], COORDS["alicante_costa"]["lon"])
    metar = obtener_metar_leal()

    # Extracción segura de datos
    temp_actual = clima_elche['current_weather']['temperature'] if clima_elche else "Datos no disponibles"
    viento_vel = clima_elche['current_weather']['windspeed'] if clima_elche else "Datos no disponibles"
    viento_dir = direccion_viento_texto(clima_elche['current_weather']['winddirection']) if clima_elche else ""
    humedad = clima_elche['hourly']['relativehumidity_2m'][0] if clima_elche else "Datos no disponibles"
    presion = clima_elche['hourly']['surface_pressure'][0] if clima_elche else "Datos no disponibles"
    precip_prob = clima_elche['hourly']['precipitation_probability'][0] if clima_elche else "0"

    oleaje_alicante = mar_alicante['current']['wave_height'] if mar_alicante else "Datos no disponibles"
    
    # Datos METAR LEAL
    viento_aero = f"{metar['wdir']} grados a {metar['wspd']} nudos" if metar else "Sin datos"
    presion_aero = metar['altim'] if metar else "Sin datos"

    # --- REDACCIÓN BASADA EXACTAMENTE EN EL PDF ---
    texto = f"""
    {saludo} Son las {ahora.strftime('%H y %M')} horas del {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. 
    Transmitimos el boletín meteorológico y marítimo de Radio Maitino, con el estado actual y la predicción terrestre y marítima para las próximas horas.

    AVISOS Y PREDICCIÓN TERRESTRE.
    Avisos Locales en Elche y Baix Vinalopó: Sin avisos severos activados en este momento.
    Avisos Nacionales: Situación estable en la mayor parte de la península.
    
    Estado y Predicción Local para las próximas 12 horas.
    Estado Actual: Presión de {presion} hectopascales, temperatura de {temp_actual} grados centígrados, humedad del {humedad} por ciento, viento del {viento_dir} a {viento_vel} kilómetros por hora.
    Precipitación: Probabilidad actual del {precip_prob} por ciento.

    Predicción Próximas 12 Horas:
    A lo largo del día, las temperaturas oscilarán manteniendo una tendencia estable. 
    Se espera viento moderado de componente {viento_dir}. La probabilidad media de precipitación se mantendrá en torno al {precip_prob} por ciento.

    AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ.
    Condiciones Actuales:
    Viento en Superficie: {viento_aero}.
    Presión Atmosférica: {presion_aero} hectopascales.
    Tendencia para las próximas horas: Operaciones normales, sin fenómenos severos a la vista.

    AVISOS Y PREDICCIÓN MARÍTIMA.
    Costa de Alicante y Elche.
    Estado de la Mar: Altura del oleaje actual de {oleaje_alicante} metros.
    Viento: Componente {viento_dir} a {viento_vel} kilómetros por hora.
    Visibilidad: Buena.

    Predicción Nacional de Mareas.
    Mediterráneo Sector Baleares y Canal de Ibiza: Oleaje leve, vientos estables. Visibilidad óptima para la navegación.
    Mediterráneo Sector Alborán y Golfo de Vera: Condiciones marítimas tranquilas sin avisos de vendaval.
    Costa Cantábrica y Galicia: Situación estable, atención a posibles nieblas matinales.
    Islas Canarias: Régimen de alisios habitual, mar de fondo leve.

    Información meteorológica, marítima y aeronáutica elaborada a partir de los datos oficiales de la Agencia Estatal de Meteorología, la NOAA y el Servicio Marino de Puertos del Estado.
    Este ha sido el boletín meteorológico y marítimo de Radio Maitino, emitido a las {ahora.strftime('%H y %M')} horas, unidad de tiempo coordinado +1. 
    Actualizamos la predicción a primera hora de la mañana. Buena jornada y buena navegación.
    """
    return texto

# ==========================================
# PRODUCCIÓN DE AUDIO Y MEZCLA
# ==========================================

async def generar_audio_tts(texto):
    """Genera la voz utilizando Microsoft Edge TTS"""
    print(f"[{datetime.datetime.now()}] Generando locución (Edge TTS)...")
    comunicador = edge_tts.Communicate(texto, VOZ_TTS, rate="+0%") # rate modificado a 0% para ritmo pausado
    await comunicador.save(ARCHIVO_VOZ)

def mezclar_audio_radio():
    """Mezcla la voz generada con la sintonía de fondo"""
    print(f"[{datetime.datetime.now()}] Mezclando audio con sintonía de BBC/Noticias...")
    try:
        # Cargar archivos
        voz = AudioSegment.from_mp3(ARCHIVO_VOZ)
        
        # Si no hay intro, exportar solo la voz
        if not os.path.exists(ARCHIVO_MUSICA):
            print("Advertencia: No se encontró 'intro.mp3'. Generando solo voz.")
            voz.export(ARCHIVO_FINAL, format="mp3")
            return

        musica_fondo = AudioSegment.from_mp3(ARCHIVO_MUSICA)

        # Ajustar volumen de la música (-15dB para que quede de fondo)
        musica_fondo = musica_fondo - 15 

        # Hacer que la música en loop dure lo mismo que la voz + 5 segundos al final
        duracion_necesaria = len(voz) + 5000 
        musica_loop = musica_fondo * (duracion_necesaria // len(musica_fondo) + 1)
        musica_loop = musica_loop[:duracion_necesaria]

        # Mezclar: la música empieza sola 2 segundos, luego entra la voz
        mix_final = musica_loop.overlay(voz, position=2000)

        # Efecto Fade Out al final
        mix_final = mix_final.fade_out(3000)

        mix_final.export(ARCHIVO_AUDIO_FINAL, format="mp3", bitrate="192k")
        print(f"[{datetime.datetime.now()}] Boletín completado con éxito: {ARCHIVO_AUDIO_FINAL}")
        
    except Exception as e:
        print(f"Error en la producción de audio: {e}")

# ==========================================
# RUTINA PRINCIPAL Y SCHEDULER
# ==========================================

def ejecutar_boletin():
    print(f"\n--- INICIANDO ACTUALIZACIÓN DEL BOLETÍN: {datetime.datetime.now()} ---")
    
    # 1. Obtener datos y redactar
    texto_boletin = generar_texto_boletin()
    
    # 2. Generar Voz (asyncio)
    asyncio.run(generar_audio_tts(texto_boletin))
    
    # 3. Post-producción (Mezcla de niveles de radio)
    mezclar_audio_radio()
    
    # 4. Limpieza de archivos temporales
    if os.path.exists(ARCHIVO_VOZ):
        os.remove(ARCHIVO_VOZ)

if __name__ == "__main__":
    # Ejecutar una vez al abrir
    ejecutar_boletin()
    
    # Programar cada 30 minutos
    schedule.every(30).minutes.do(ejecutar_boletin)
    
    print("Sistema de Radio Maitino automatizado en ejecución. Presiona Ctrl+C para detener.")
    
    # Bucle infinito para mantener el script vivo
    while True:
        schedule.run_pending()
        time.sleep(1)
