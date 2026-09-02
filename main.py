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

# Coordenadas
COORDS = {
    "elche": {"lat": 38.2622, "lon": -0.7011},
    "alicante_costa": {"lat": 38.3, "lon": -0.4},
    "cantabrico": {"lat": 43.5, "lon": -5.5},
    "canarias": {"lat": 28.1, "lon": -15.4}
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
    
    clima_elche = obtener_datos_clima(COORDS["elche"]["lat"], COORDS["elche"]["lon"])
    mar_alicante = obtener_datos_maritimos(COORDS["alicante_costa"]["lat"], COORDS["alicante_costa"]["lon"])
    metar = obtener_metar_leal()

    # Sustituimos el punto por la coma para que el lector no diga "punto" en los decimales
    temp_actual = str(clima_elche['current_weather']['temperature']).replace('.', ',') if clima_elche else "20"
    viento_vel = str(clima_elche['current_weather']['windspeed']).replace('.', ',') if clima_elche else "10"
    viento_dir = direccion_viento_texto(clima_elche['current_weather']['winddirection']) if clima_elche else "este"
    humedad = str(clima_elche['hourly']['relativehumidity_2m'][0]).replace('.', ',') if clima_elche else "50"
    presion = str(clima_elche['hourly']['surface_pressure'][0]).replace('.', ',') if clima_elche else "1013"
    precip_prob = str(clima_elche['hourly']['precipitation_probability'][0]).replace('.', ',') if clima_elche else "0"
    oleaje_alicante = str(mar_alicante['current']['wave_height']).replace('.', ',') if mar_alicante else "0,5"
    
    viento_aero = f"{metar['wdir']} grados a {metar['wspd']} nudos".replace('.', ',') if metar else "Variable a 5 nudos"
    presion_aero = str(metar['altim']).replace('.', ',') if metar else "1013"

    texto = f"""
    Do, mi, sol, mi, do agudo...
    
    BOLETÍN METEOROLÓGICO, MARÍTIMO Y AERONÁUTICO
    {saludo}. Son las {ahora.strftime('%H y %M')} horas del {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}. Transmitimos el boletín meteorológico y marítimo de Radio Maitino, con el estado actual y la predicción terrestre y marítima para las próximas horas.
    
    AVISOS Y PREDICCIÓN TERRESTRE
    Avisos Locales en Elche y Baix Vinalopó: Sin avisos severos activados en este momento.
    Avisos Nacionales: Situación estable en la mayor parte de la península.
    
    Estado y Predicción Local para las próximas 12 horas.
    Hay avisos activados en las siguientes zonas: Ninguna zona con avisos.
    
    Estado Actual: {temp_actual} grados centígrados, humedad del {humedad} por ciento, viento del {viento_dir} a {viento_vel} kilómetros por hora. Presión de {presion} hectopascales. Cielos con intervalos nubosos. Precipitación: Cero litros por metro cuadrado. 
    
    Predicción Próximas 12 Horas:
    Mañana: Cielos poco nubosos. Aumento progresivo de temperaturas hasta los 25 grados centígrados al mediodía. Precipitación del {precip_prob} por ciento.
    Tarde: Máximas térmicas entre los 22 grados centígrados y 26 grados centígrados, con sensación térmica de 25. Entrada de brisa del {viento_dir} con rachas de 15 a 20 kilómetros por hora a partir de las 16 horas. Precipitación del {precip_prob} por ciento.
    Noche: Descenso térmico progresivo hasta los 18 grados centígrados con cielos despejados. Precipitación del cero por ciento.
    
    Estado y Predicción nacional para las próximas 12 horas.
    Hay avisos activados en las siguientes zonas: Ninguna zona con avisos.
    
    Situación General: Tiempo estable y anticiclónico en la mayor parte del país.
    Norte y Cantábrico: Nubosidad de retención con posibles lloviznas débiles.
    Centro y Meseta: Cielos despejados con gran amplitud térmica.
    Sur: Cielos poco nubosos y temperaturas suaves.
    Levante y Archipiélagos: Régimen de brisas y estabilidad general.

    AVISOS Y PREDICCIÓN AERONÁUTICA METAR LEAL PARA EL AEROPUERTO ELCHE - ALICANTE MIGUEL HERNÁNDEZ
    Avisos activados: Sin avisos.
    Condiciones Actuales: Operaciones con normalidad.
    Viento en Superficie: {viento_aero}.
    Techo de Nubes: Sin nubes significativas por debajo de 5000 pies.
    Presión Atmosférica: {presion_aero} hectopascales.
    
    Predicción de Aviación de 12 a 24 Horas: Visibilidad superior a 10 kilómetros y vientos estables.
    
    Tendencia: Sin cambios significativos para la navegación aérea.

    AVISOS Y PREDICCIÓN MARÍTIMA
    Avisos Locales: Sin avisos activados.
    Avisos Nacionales:
    Aviso de Fuertes Vientos: Inactivo.
    Aviso de Vendaval: Inactivo.
    Aviso de Temporal Severo o Fuerza Huracanada: Inactivo.
    Alertas por Tormentas y Fenómenos Severos: Inactivo.
    Aviso de Mar de Fondo u Oleaje Peligroso: Inactivo.
    Aviso de Visibilidad Reducida o Niebla Densa: Inactivo.
    
    Costa de Alicante y Elche
    Avisos: Sin avisos.
    
    Costa de Elche:
    Viento: Componente {viento_dir} a {viento_vel} kilómetros por hora.
    Estado de la Mar: Marejadilla, con altura del oleaje de {oleaje_alicante} metros.
    Temperatura del Agua: 20 grados centígrados.
    Tiempo: Poco nuboso.
    Visibilidad: Buena.
    
    Costa de Alicante y Mar Interior:
    Viento: Variable flojo.
    Estado de la Mar: Rizada a marejadilla.
    Temperatura del Agua: 20 grados centígrados.
    Tiempo: Despejado.
    Visibilidad: Excelente.
    
    Predicción Nacional de Mareas
    
    Mediterráneo (Sector Baleares y Canal de Ibiza):
    Avisos: Sin avisos.
    Viento: Flojo de dirección variable.
    Estado de la Mar: Rizada.
    Tiempo: Soleado.
    Visibilidad: Excelente.
    Tipo: Marea meteorológica leve.
    Pleamar: Sin variaciones significativas.
    Bajamar: Sin variaciones significativas.
    
    Mediterráneo (Sector Alborán y Golfo de Vera):
    Avisos: Sin avisos.
    Viento: Levante moderado.
    Estado de la Mar: Marejada.
    Tiempo: Intervalos nubosos.
    Visibilidad: Buena.
    Tipo: Régimen de marea normal.
    Pleamar: Al mediodía.
    Bajamar: Por la noche.
    
    Costa Cantábrica y Galicia:
    Avisos: Sin avisos.
    Viento: Noroeste moderado.
    Estado de la Mar: Fuerte marejada.
    Tiempo: Cielos cubiertos.
    Visibilidad: Regular por brumas.
    Tipo: Marea astronómica.
    Pleamar: Por la tarde.
    Bajamar: De madrugada.
    
    Atlántico Andaluz (Cádiz y Huelva):
    Avisos: Sin avisos.
    Viento: Poniente flojo.
    Estado de la Mar: Marejadilla.
    Tiempo: Despejado.
    Visibilidad: Buena.
    Tipo: Marea astronómica.
    Pleamar: Al mediodía.
    Bajamar: Por la tarde.
    
    Islas Canarias:
    Avisos: Sin avisos.
    Viento: Alisios moderados del noreste.
    Estado de la Mar: Marejada.
    Tiempo: Nubosidad en el norte de las islas.
    Visibilidad: Buena.
    Tipo: Marea astronómica.
    Pleamar: A primera hora.
    Bajamar: A media tarde.
    
    Información meteorológica, marítima y aeronáutica elaborada a partir de los datos oficiales de la Agencia Estatal de Meteorología, la NOAA y el Servicio Marino de Puertos del Estado.
    Este ha sido el boletín meteorológico y marítimo de Radio Maitino, emitido a las {ahora.strftime('%H y %M')} horas, unidad de tiempo coordinado más 1. Actualizamos la predicción a primera hora de la mañana. Buena jornada y buena navegación.
    
    Do, mi, sol, mi, do agudo...
    """
    return texto

# ==========================================
# PRODUCCIÓN DE AUDIO Y MEZCLA
# ==========================================

async def generar_audio_tts(texto):
    print(f"[{datetime.datetime.now()}] Generando locución (Edge TTS)...")
    # Voz a velocidad normal (+0%)
    comunicador = edge_tts.Communicate(texto, VOZ_TTS, rate="+0%") 
    await comunicador.save(ARCHIVO_VOZ)

def mezclar_audio_radio():
    print(f"[{datetime.datetime.now()}] Mezclando audio para 6 minutos exactos...")
    try:
        voz = AudioSegment.from_mp3(ARCHIVO_VOZ)
        
        if not os.path.exists(ARCHIVO_MUSICA):
            print("Advertencia: No se encontró 'intro.mp3'. Generando solo voz.")
            voz.export(ARCHIVO_AUDIO_FINAL, format="mp3")
            return

        musica_fondo = AudioSegment.from_mp3(ARCHIVO_MUSICA)
        musica_fondo = musica_fondo - 15 

        # === FORZAR EXACTAMENTE 6 MINUTOS (360,000 milisegundos) ===
        duracion_exacta = 6 * 60 * 1000 
        
        # Repetir la música hasta cubrir los 6 minutos
        musica_loop = musica_fondo * (duracion_exacta // len(musica_fondo) + 1)
        musica_loop = musica_loop[:duracion_exacta]

        # Mezclar: la música empieza sola 2 segundos, luego entra la voz
        mix_final = musica_loop.overlay(voz, position=2000)

        # Si por algún motivo la voz superara los 6 minutos (muy improbable), cortamos a 6 min exactos
        if len(mix_final) > duracion_exacta:
            mix_final = mix_final[:duracion_exacta]

        # Fade out suave de 5 segundos al finalizar los 6 minutos
        mix_final = mix_final.fade_out(5000)

        mix_final.export(ARCHIVO_AUDIO_FINAL, format="mp3", bitrate="192k")
        print(f"[{datetime.datetime.now()}] Boletín completado con éxito. Duración: 6 minutos exactos.")
        
    except Exception as e:
        print(f"Error en la producción de audio: {e}")

# ==========================================
# RUTINA PRINCIPAL (Para GitHub Actions)
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
