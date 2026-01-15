import asyncio
from contextlib import suppress
import subprocess
import os, json
import shutil
import re
import threading
import queue
import math
import time
import uuid
import ffmpeg
import datetime
import aiohttp_cors
from aiohttp import web
import traceback
import humanize
import requests
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
import pyrogram
from pyrogram.errors import (
    ChannelBanned,
    ChannelInvalid,
    ChannelPrivate,
    ChatIdInvalid,
    ChatInvalid,
    FloodWait
)

import yt_dlp

from spotdl import Spotdl
from spotdl.utils.spotify import SpotifyClient
from spotdl.download.downloader import Downloader
from spotdl.utils.config import DEFAULT_CONFIG
from spotdl.types.song import Song
from spotdl.types.options import DownloaderOptions
from spotdl.utils.config import get_config_file

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from modules.config import OWNER_ID, NAME, API_ID, API_HASH, MOBILE_NUMBER, TARGET_CHANNEL, LOG_CHANNEL, VERSION, ENGINE, SESSION_STRING, GROQ
from modules.gemini import *
from modules.groq_chat import GroqChatSession
from modules.quotes import get_quote
from modules.lacartoon import Cartoons

cartoon = Cartoons()

groq_session = GroqChatSession(api_key=os.environ.get('GROQ', GROQ))

# Diccionario global para almacenar procesos de streaming activos
active_streams = {}

# Crear un filtro personalizado para verificar si el usuario es el propietario
def owner_filter(_, __, message):
    return message.from_user and message.from_user.id in OWNER_ID

owner_only = filters.create(owner_filter)

start_time = 0
last_update_time = 0
last_current = 0
update_time = 5  # segundos

# Crear el cliente del bot
bot = Client(
    f"{NAME}",
    api_id=API_ID,
    api_hash=API_HASH,
    phone_number=MOBILE_NUMBER,
    session_string=os.environ.get("SESSION_STRING", SESSION_STRING),
    app_version=VERSION,
    device_model=ENGINE
)

# Decorador para manejar errores comunes
def handle_errors(func):
    async def wrapper(client, message):
        try:
            await func(client, message)
        except Exception as e:
            await message.reply(f"**[⛔]** Error: `{str(e)}`")
    return wrapper

# -----------------------------------------------------

@handle_errors
async def start(client: Client, message: Message):
    if message.from_user.id in OWNER_ID:
        bienvenida = f"""
**[👾]** __👋🏻 Hola {message.from_user.mention} te doy la bienvenida a {ENGINE} un super bot creado con el objetivo de hacerte la vida más fácil papu.__

**⛶ Características ⛶**
__- Corregidos los errores de la ia__
__- Reformato de las historias__
__- Agregada la descarga de videos de la Cartoon__

**⛶ Pronto ⛶**
__- Ejecución de comandos en la terminal__
__- Ejecución de comandos de python orientados a telegram__
__- Descarga de archivos de la web__

**Titan** __v{VERSION}__
"""
        await message.reply(
            text=bienvenida
        )

# --------------------Ayuda del bot
@handle_errors
async def help(client: Client, message: Message):
    await message.delete()
    if message.from_user.id in OWNER_ID:
        help = f"""
<b>Comandos del User-bot</b>

<code>-start</code>
└ Inicia el User-bot

<code>-userinfo</code> <i>reply</i> | <i>user_id</i>
└ Muestra información de un usuario

<code>-chatinfo</code> <i>reply</i> | <i>chat_id</i>
└ Muestra información de un chat

<code>-ai</code> <i>texto</i>
└ Genera una respuesta de la IA

<code>-aiaudio</code>
└ Genera una respuesta de la IA en audio

<code>-cartoon</code> <i>url</i>
└ Descarga la serie de La Cartoon a partir de la url

<code>-reset</code>
└ Resetea el chat con la IA

<code>-stream</code> <i>stream_url</i> <i>stream_key</i>
└ Inicia un stream de video

<code>-stopstream</code> <i>stream_id</i>
└ Detiene un stream en progreso

<code>-urlsave</code> <i>enlace</i> <i>cantidad</i> <i>channel_id</i> <i>topic_id</i>
└ Guarda mensajes de un enlace de Telegram

<code>-save</code> <i>id chanel</i> <i>cantidad</i> <i>channel_id</i> <i>topic_id</i>
└ Renvio masivo de mensajes de un canal a otro

<code>-clear</code>
└ Limpia la carpeta de descargas

<code>-story</code> <i>reply</i>
└ Sube un archivo multimedia a tu historia

<code>-afk</code>
└ Activa/desactiva el modo AFK
"""
        await message.reply(
            text=help
        )

# -----------------------------------------------------
@handle_errors
async def ping(client: Client, message: Message):
    if message.from_user.id in OWNER_ID:
        start = datetime.datetime.now()
        end = datetime.datetime.now()
        ms = (end - start).microseconds / 1000
        await message.reply(f"**[👾] Pong!** `{ms} ms`", quote=True)

# -----------------------------------------------------
# Función para determinar el tipo de archivo basado en la extensión
def determine_media_type(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]:
        return "photo"
    elif extension in [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv",".webm", ".m4v"]:
        return "video"
    else:
        return "document"

def extract_urls(text):
    if not text:
        return []
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def get_video_info(media_path):
    try:
        # Obtener toda la información del archivo
        probe = ffmpeg.probe(media_path)
        
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        return {
            'duration': float(video_stream.get('duration', 0)) if video_stream else 0,
            'width': int(video_stream.get('width', 0)) if video_stream else 0,
            'height': int(video_stream.get('height', 0)) if video_stream else 0,
            'video_codec': video_stream.get('codec_name', 'h264') if video_stream else 'h264',
            'audio_codec': audio_stream.get('codec_name', 'aac') if audio_stream else 'aac',
            'pix_fmt': video_stream.get('pix_fmt', 'yuv420p') if video_stream else 'yuv420p',
            'fps': eval(video_stream.get('r_frame_rate', '30/1')) if video_stream else 30
        }

    except Exception as e:
        print(f"Error con ffmpeg.probe: {e}")
        # Fallback mínimo
        return {
            'duration': 0,
            'width': 0,
            'height': 0,
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'pix_fmt': 'yuv420p',
            'fps': 30
        }

async def userinfo(client: Client, message: Message):
    if message.from_user.id in OWNER_ID:
        dc_id = {
        1: "Miami FL | USA",
        2: "Amsterdam | NL",
        3: "Miami FL | USA",
        4: "Amsterdam | NL",
        5: "Singapore | SG"}
        
        msg = await message.reply("**[👾]** Wait For Info...")
        if message.reply_to_message:
            user = message.reply_to_message.from_user.id
        elif len(message.command) > 1:
            user = message.command[1]
        else:
            return await msg.edit("**[⛔]** Invalid User")
        try:
            ui = await client.get_users(user)
        except Exception as ex:
            return await msg.edit(f"**[⛔]** Error\nEX:\n`{ex}`")
        
        dcid = f"{ui.dc_id} | {dc_id[ui.dc_id]}" if ui.dc_id else "Unknown"
        button = InlineKeyboardButton(text="GOOGLE", url=f"https://www.google.com/")
        keyboard = InlineKeyboardMarkup([[button]])
        ui_text = [
            f"┎ User {ui.mention}\n",
            f"┠ Firstname : {ui.first_name}\n",
            f"┠ Lastname : {ui.last_name}\n" if ui.last_name else "",
            f"┠ Username : @{ui.username}\n"if ui.username else "",
            f"┠ ID: `{ui.id}`\n",
            f"┠ DCID: {dcid}\n",
            f"┠ Premium: {'Si' if ui.is_premium else 'No'}\n"
            f"┠ Status: {(str(ui.status)).split('.')[-1]}\n",
            f"┠ Bot: {'Si' if ui.is_bot else 'No'}\n",
            f"┠ Scam: {'Si' if ui.is_scam else 'No'}\n",
            f"┠ Contacto: {'Si' if ui.is_contact else 'No'}\n",
            f"┠ Verificado: {'Si' if ui.is_verified else 'No'}\n",
            f"┖ Chats en Común: {len(await ui.get_common_chats())}",
        ]
        pic = ui.photo.big_file_id if ui.photo else None
        if pic is not None:
            await msg.delete()
            photo = await client.download_media(pic)
            await message.reply_photo(
                photo=photo,
                caption="".join(ui_text),
                reply_markup=keyboard,
            )
            if os.path.exists(photo):
                os.remove(photo)
        else:
            await bot.send_message(message.chat.id, text="".join(ui_text))


async def get_chat_info(client: Client, message: Message):
    if message.from_user.id in OWNER_ID:
        msg = await message.reply("**[👾]** Wait For Info...")
        reply = message.reply_to_message
        if reply:
            chat_id = reply.chat.id
        elif len(message.command) > 1:
            chat_id = message.command[1]
        else:
            await msg.edit("**[⛔]** Debes proporcionar un ID de chat o responder a un mensaje.")
            return
        try:
            chat_info = await client.get_chat(chat_id)
        except Exception as ex:
            return await msg.edit(f"**[⛔]** Error fetching chat info.\nEX:\n`{ex}`")
        
        chat_info_text = [
            f"┎ Info {chat_info.title}\n",
            f"┠ Username : @{chat_info.username}\n" if chat_info.username is not None else "",
            f"┠ ID: `{chat_info.id}`\n",
            f"┠ Miembros: {chat_info.members_count}\n",
            f"┠ Scam: {'Si' if chat_info.is_scam else 'No'}\n",
            f"┠ Soporte: {'Si' if (chat_info.is_support) else 'No'}\n"
            f"┠ Verificado: {'Si' if (chat_info.is_verified) else 'No'}\n",
            f"┠ Chat Type: {(str(chat_info.type)).split('.')[-1]}\n",
            f"┖ Descripción:\n{chat_info.description}" if chat_info.description is not None else "",
        ]
        pic = chat_info.photo.big_file_id if chat_info.photo else None
        if pic is not None:
            photo = await bot.download_media(pic)
            await bot.send_photo(
                message.chat.id,
                photo,
                caption="".join(chat_info_text),
                reply_to_message_id=message.id,
            )
            os.remove(photo)
            await msg.delete()
            return
        else:
            await bot.send_message(message.chat.id, text="".join(chat_info_text))

def get_listado():
    url = "https://datafacil.vercel.app/listado.json"
    response = requests.get(url)
    frases = response.json()
    return frases

@handle_errors
async def upload_to_story(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return

    # Verificar que sea una respuesta a un mensaje con video o imagen
    if not message.reply_to_message or (not message.reply_to_message.video and not message.reply_to_message.photo):
        await message.reply("**[⛔]** Debes responder a un video o una imagen.")
        return

    try:
        await message.delete()
        # Descargar el archivo (video o imagen)
        status_msg = await message.reply("**[👾]** Descargando archivo...")
        media = message.reply_to_message.video if message.reply_to_message.video else message.reply_to_message.photo
        media_path = await client.download_media(
            media,
        )

        # Extraer el texto del mensaje, si lo hay (opcional, puede estar vacío)
        caption = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None

        await status_msg.edit("**[👾]** Procesando media...")

        if message.reply_to_message.video:
            video_info = get_video_info(media_path)
            duration = video_info['duration']

            if duration > 60:
                num_segments = math.ceil(duration / 60)
                for i in range(num_segments):
                    start = i * 60
                    segment_duration = min(60, duration - start)
                    output_path = f"{media_path}_part{i+1}.mp4"

                    await status_msg.edit(f"**[👾]** Procesando parte {i+1}/{num_segments}...")

                    # Cortar y convertir segmento
                    (
                        ffmpeg
                        .input(media_path, ss=start, t=segment_duration)
                        .output(output_path, vcodec='libx264', acodec='aac', vf='scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black', preset='fast', crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )

                    # Subir a historia
                    await client.send_story(
                        chat_id="me",
                        media=output_path,
                        caption=caption
                    )

                    os.remove(output_path)
            else:
                # Video corto, convertir y subir
                output_path = f"{media_path}_converted.mp4"
                (
                    ffmpeg
                    .input(media_path)
                    .output(output_path, vcodec='libx264', acodec='aac', vf='scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black', preset='fast', crf=23)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

                await client.send_story(
                    chat_id="me",
                    media=output_path,
                    caption=caption
                )

                os.remove(output_path)

        elif message.reply_to_message.photo:
            output_path = f"{media_path}_processed.png"
            # Procesar imagen: escalar y agregar padding superior transparente
            (
                ffmpeg
                .input(media_path)
                .filter('scale', '720', '1280', force_original_aspect_ratio='decrease')
                .filter('pad', '720', '1280', '(ow-iw)/2', '(oh-ih)/2', '0x00000000')  # Centrar imagen horizontal y verticalmente
                .output(output_path)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            await client.send_story(
                chat_id="me",
                media=output_path,
                caption=caption
            )

            os.remove(output_path)

        # Limpiar archivo original
        if os.path.exists(media_path):
            os.remove(media_path)

        # Confirmar subida
        await status_msg.edit("**[✅]** Archivo(s) subido(s) a tu historia exitosamente.")
        await asyncio.sleep(5)
        await status_msg.delete()

    except Exception as ex:
        await message.reply(f"**[⛔]** Error al subir a la historia: {ex}")

def limpiar_caption(caption):
    if not caption:
        return caption
        
    texto_limpio = caption
    for frase in get_listado():
        texto_limpio = texto_limpio.replace(frase, "").strip()
    
    # Eliminar líneas vacías múltiples
    while "\n\n\n" in texto_limpio:
        texto_limpio = texto_limpio.replace("\n\n\n", "\n\n")
    
    return texto_limpio.strip()

def limpiar_nombre_archivo(nombre):
    """Limpia el nombre del archivo eliminando las frases no deseadas y agrega @XMedia_Oficial antes de la extensión"""
    nombre_limpio = nombre
    for frase in get_listado():
        nombre_limpio = nombre_limpio.replace(frase, "").strip()
    
    # Eliminar espacios múltiples
    while "  " in nombre_limpio:
        nombre_limpio = nombre_limpio.replace("  ", " ")
    
    # Separar el nombre y la extensión del archivo
    nombre_sin_ext, ext = os.path.splitext(nombre_limpio)
    
    # Agregar @XMedia_Oficial antes de la extensión
    nombre_limpio = f"{nombre_sin_ext}{ext}"
    
    return nombre_limpio.strip()

@handle_errors
async def save_and_forward_message(client: Client, message: Message):
    if not message.from_user.id in OWNER_ID:
        return
    
    try:
        # Verificar si se proporcionó un enlace
        if len(message.command) < 2:
            await message.reply("**[⛔]** Uso: `-urlsave [enlace de Telegram] [cantidad opcional] [channel_id opcional] [topic_id opcional]`")
            return

        link = message.command[1]
        
        # Parsear parámetros opcionales
        count = 1  # valor por defecto
        target_channel = TARGET_CHANNEL  # valor por defecto
        target_topic = None  # valor por defecto
        
        if len(message.command) >= 3:
            count = int(message.command[2])
        if len(message.command) >= 4:
            target_channel = int(message.command[3])
        if len(message.command) >= 5:
            target_topic = int(message.command[4])

        info_msg = await message.reply(
            f"**[👾]** Procesando enlace:\n{link}\n"
            f"Cantidad: {count}\n"
            f"Canal destino: {target_channel}\n"
            f"Topic ID: {target_topic if target_topic else 'No especificado'}", 
            disable_web_page_preview=True
        )

        status_msg = await message.reply(f"**[👾]** Sacando contenido...")

        # Patrones para diferentes tipos de enlaces
        private_with_topic = r"https?://t\.me/c/(\d+)/(\d+)/(\d+)"  # Enlaces con topic_id
        private_pattern = r"https?://t\.me/c/(\d+)/(\d+)"  # Enlaces de grupos/canales privados
        public_pattern = r"https?://t\.me/([\w\d_]+)/(\d+)"  # Enlaces de canales públicos
        bot_pattern = r"https?://t\.me/b/([\w\d_]+)/(\d+)"  # Enlaces de bots

        topic_id = None
        if re.match(private_with_topic, link):
            match = re.match(private_with_topic, link)
            chat_id = int("-100" + match.group(1))
            message_id = int(match.group(3))  # El mensaje está en la posición 3
            topic_id = int(match.group(2))    # El topic en la posición 2
        elif re.match(private_pattern, link):
            match = re.match(private_pattern, link)
            chat_id = int("-100" + match.group(1))
            message_id = int(match.group(2))
        elif re.match(public_pattern, link):
            match = re.match(public_pattern, link)
            chat_id = match.group(1)
            message_id = int(match.group(2))
        elif re.match(bot_pattern, link):
            match = re.match(bot_pattern, link)
            chat_id = match.group(1)
            message_id = int(match.group(2))
        else:
            await status_msg.edit("**[⛔]** El enlace proporcionado no es válido.")
            return
        
        # Contadores
        success_count = 0
        error_count = 0
        total_messages = count
        start_time = datetime.datetime.now()

        for i in range(count):
            try:
                # Pausa de 1 minutos cada 50 mensajes
                if success_count > 0 and success_count % 100 == 0:
                    await status_msg.edit(f"**[⏳]** Pausa de 1 minutos para evitar flood después de {success_count} mensajes...")
                    await asyncio.sleep(5)  # 1 minutos = 60 segundos

                current_message_id = message_id + i
                # Obtener información del mensaje
                msg = await client.get_messages(chat_id, current_message_id)

                if not msg:
                    await message.reply(f"**[⛔]** No se pudo obtener el mensaje con ID: `{current_message_id}`.")
                    continue
                
                # Si no hay media y no hay texto, saltar al siguiente mensaje
                if not msg.media and not (msg.text or msg.caption):
                    continue

                # Descargar contenido multimedia si existe
                media_path = None

                if msg.media:
                    media_path = await client.download_media(
                        msg,
                    )
                    await asyncio.sleep(10)  # 1 minutos = 60 segundos
                    if not media_path:
                        await status_msg.edit(f"**[⚠️]** No se pudo descargar el contenido multimedia.")
                        return

                    # Limpiar nombre del archivo si es necesario
                    nombre_original = os.path.basename(media_path)
                    nombre_limpio = limpiar_nombre_archivo(nombre_original)
                    if nombre_original != nombre_limpio:
                        nuevo_path = os.path.join(os.path.dirname(media_path), nombre_limpio)
                        os.rename(media_path, nuevo_path)
                        media_path = nuevo_path

                # Preparar información del mensaje
                text = msg.text or msg.caption
                caption = limpiar_caption(text) if text else None

                # Determinar el tipo de archivo
                media_type = determine_media_type(media_path) if media_path else None

                # Parámetros comunes para todos los tipos de envío
                common_params = {
                    "chat_id": target_channel,
                    "message_thread_id": target_topic
                }

                if media_type == "video":
                    video_info = get_video_info(media_path)
                    # Generar miniatura del video
                    thumbnail_path = f"{media_path}_thumb.jpg"
                    (
                    ffmpeg
                    .input(media_path, ss=video_info['duration']//2 if video_info['duration'] > 0 else 0)
                    .filter('scale', 320, -1)
                    .output(thumbnail_path, vframes=1)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                    )
                    await client.send_video(
                        **common_params,
                        video=media_path,
                        caption=caption,
                        duration=video_info['duration'],
                        width=video_info['width'],
                        height=video_info['height'],
                        thumb=thumbnail_path if os.path.exists(thumbnail_path) else None,
                    )
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                elif media_type == "photo":
                    await asyncio.sleep(1)
                    await client.send_photo(
                        **common_params,
                        photo=media_path,
                        caption=caption
                    )
                elif media_type == "document":
                    await asyncio.sleep(10)
                    await client.send_document(
                        **common_params,
                        document=media_path,
                        caption=caption,
                    )
                elif text:  # Solo enviar mensaje de texto si hay texto
                    await client.send_message(
                        **common_params,
                        text=caption,
                        disable_web_page_preview=True
                    )

                # Eliminar archivo local después de subir
                if media_path and os.path.exists(media_path):
                    os.remove(media_path)
                success_count += 1

                # Actualizar progreso cada 10 mensajes o al final
                if success_count % 1 == 0 or success_count == total_messages:
                    progress = (success_count / total_messages) * 100
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    progress_text = (
                        f"**[👾]** Progreso: {progress:.1f}%\n"
                        f"```\n{progress_bar}```\n"
                        f"✅ Mensajes exitosos: {success_count}/{total_messages}\n"
                        f"⚠️ Errores: {error_count}\n"
                        f"🔄 ID actual: {current_message_id}"
                    )
                    if topic_id:
                        progress_text += f"\n📑 Topic ID: {topic_id}"
                    await status_msg.edit(progress_text)

                await asyncio.sleep(1)
            
            except (
                ChannelBanned,
                ChannelInvalid,
                ChannelPrivate,
                ChatIdInvalid,
                ChatInvalid,
            ):
                await info_msg.edit("Estas unido a ese canal?")
                return

            except FloodWait as e:
                await status_msg.edit(f"**[⏳]** Esperando {e.value} segundos debido a limitaciones de Telegram...")
                await asyncio.sleep(e.value)
            except Exception as ex:
                error_count += 1
            except Exception as ex:
                await status_msg.edit(f"**[⚠️]** Error procesando mensaje ID: `{message_id + i}`. Detalles: {ex}")
                
        # Mensaje final
        elapsed_time = datetime.datetime.now() - start_time
        final_text = (
            f"**[👾]** Proceso completado:\n"
            f"✅ Mensajes exitosos: {success_count}\n"
            f"⚠️ Errores: {error_count}\n"
            f"⏱️ Tiempo total: {str(elapsed_time).split('.')[0]}"
        )
        if topic_id:
            final_text += f"\n📑 Topic ID: {topic_id}"
        final_text += f"\n📅 {datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}"

        await status_msg.edit(final_text)
        
    except Exception as ex:
        await message.reply(f"**[⛔]** Error general: {str(ex)}")

# Stream del contenido --------------------------------
class StreamStatusQueue:
    def __init__(self, message, status_msg, stream_id):
        """
        Initialize the status queue for thread-safe communication
        
        :param message: Original Telegram message
        :param status_msg: Status message to update
        :param stream_id: Unique identifier for the stream
        """
        self.message = message
        self.status_msg = status_msg
        self.stream_id = stream_id  # Nuevo campo para identificar el stream
        self.status_queue = queue.Queue()
        self.stop_event = threading.Event()

def status_monitor(stream_status_queue, client):
    """
    Continuously monitor the status queue and update the message
    
    :param stream_status_queue: StreamStatusQueue instance
    :param client: Telegram client
    """
    while not stream_status_queue.stop_event.is_set():
        try:
            try:
                message_text, is_error = stream_status_queue.status_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                asyncio.run(_update_status(
                    client, 
                    stream_status_queue.message, 
                    stream_status_queue.status_msg, 
                    message_text, 
                    is_error
                ))
            except Exception as e:
                print(f"Error updating status: {e}")
        except Exception as e:
            print(f"Status monitor error: {e}")
    
async def _update_status(client, message, status_msg, message_text, is_error):
    """
    Async function to update the status message
    """
    try:
        await status_msg.edit(message_text)
    except Exception:
        await message.reply(message_text)


def configure_ffmpeg(video_path, output_url):
    """
    Configura FFmpeg para streaming en tiempo real estable desde cualquier contenedor (mkv, mp4).
    """
    video_info = get_video_info(video_path)
    
    # Valores seguros por defecto
    video_codec = video_info.get("video_codec", "h264")
    audio_codec = video_info.get("audio_codec", "aac")
    pix_fmt = video_info.get("pix_fmt", "yuv420p")
    fps = video_info.get("fps", 30)

    # Simula lectura en tiempo real para evitar salto por sobrecarga
    stream = ffmpeg.input(video_path, re=None)

    output_args = {
        "format": "flv",
        "preset": "veryfast",          # mejor balance calidad/CPU
        "crf": "23",                   # calidad constante
        "maxrate": "2500k",            # tasa máxima de bits
        "bufsize": "5000k",            # tamaño de búfer (para suavizar flujo)
        "r": fps,                      # framerate
        "g": int(fps * 2),             # GOP = 2 segundos
        "pix_fmt": "yuv420p",          # formato compatible
        "audio_bitrate": "128k",       # calidad de audio
        "ar": "44100",                 # frecuencia estándar
        "tune": "zerolatency",         # baja latencia
        "threads": "2"
    }

    # Reforzar recodificación para evitar incompatibilidades
    output_args["vcodec"] = "libx264"
    output_args["acodec"] = "aac"

    # Salida configurada
    stream = stream.output(output_url, **output_args)

    # Argumentos globales para estabilidad y sincronía
    stream = stream.global_args(
        "-loglevel", "error",         # usa "info" si quieres más detalle
        "-fflags", "+nobuffer",
        "-flags", "+low_delay",
        "-flush_packets", "1",
        "-vsync", "1",
        "-async", "1"
    )

    return stream

def stream_video_thread(video_path, stream_url, stream_key, stream_status_queue):
    """
    Función de transmisión que se ejecutará en un hilo separado.
    """
    try:
        if not os.path.exists(video_path):
            stream_status_queue.status_queue.put(("**[⛔]** El archivo de video no existe.", True))
            return
        
        output_url = f"{stream_url}{stream_key}"
   
        try:
            stream_status_queue.status_queue.put(("**[👾]** Iniciando transmisión...", False))
            
            # Configurar la transmisión
            stream = configure_ffmpeg(video_path, output_url)
            
            # Ejecutar la transmisión
            ffmpeg.run(stream, overwrite_output=True)
            
            stream_status_queue.status_queue.put(("**[✅]** Transmisión completada.", False))

        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else "Error desconocido en ffmpeg."
            stream_status_queue.status_queue.put((f"**[⛔️]** Error al transmitir: {error_message}", True))
        except Exception as e:
            stream_status_queue.status_queue.put((f"**[⛔️]** Error al transmitir: {str(e)}", True))
    
    finally:
        # Limpiar el archivo de video
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Eliminar este stream de los streams activos
        if stream_status_queue.stream_id in active_streams:
            del active_streams[stream_status_queue.stream_id]
        
        # Indicar que la transmisión ha terminado
        stream_status_queue.stop_event.set()


@handle_errors
async def stream_video(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return
    
    # Verificar que sea una respuesta a un mensaje con video
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply("**[⛔]** Debes responder a un video para transmitir.")
        return
    
    try:
        # Generar un ID único para este stream
        stream_id = str(uuid.uuid4())
        
        # Extraer parámetros de transmisión del comando
        if len(message.command) < 3:
            await message.reply("**[⛔]** Uso: `-stream [stream_url] [stream_key]`")
            return
        
        stream_url = message.command[1]
        stream_key = message.command[2]
        
        # Descargar el video
        status_msg = await message.reply(f"**[👾]** Descargando video para transmisión. ID de Stream: `{stream_id}`")
        print(stream_id)
        await message.reply(f'`-stopstream {stream_id}`')
        video_path = await client.download_media(
            message.reply_to_message.video,
        )
        
        # Validar que el archivo de video exista
        if not os.path.exists(video_path):
            await status_msg.edit("**[⛔]** Error: No se pudo descargar el video.")
            return
        
        # Crear la cola de estado para comunicación entre hilos
        stream_status_queue = StreamStatusQueue(message, status_msg, stream_id)
        
        # Iniciar el monitor de estado en un hilo separado
        monitor_thread = threading.Thread(
            target=status_monitor, 
            args=(stream_status_queue, client),
            daemon=True
        )
        monitor_thread.start()
        
        # Iniciar la transmisión en un hilo separado
        streaming_thread = threading.Thread(
            target=stream_video_thread, 
            args=(video_path, stream_url, stream_key, stream_status_queue),
            daemon=True
        )
        streaming_thread.start()
        
        # Almacenar información del stream activo
        active_streams[stream_id] = {
            'thread': streaming_thread,
            'stop_event': stream_status_queue.stop_event
        }
        
        # Permitir que el bot continúe respondiendo a otros comandos
        await status_msg.edit(f"**[👾]** Transmisión iniciada en segundo plano. ID de Stream: `{stream_id}`")
    
    except Exception as ex:
        await message.reply(f"**[⛔]** Error general: {ex}")

@handle_errors
async def stop_stream(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return
    
    # Verificar que se proporcione un ID de stream
    if len(message.command) < 2:
        await message.reply("**[⛔]** Uso: `-stopstream [stream_id]`")
        return
    
    stream_id = message.command[1]
    
    if stream_id not in active_streams:
        await message.reply(f"**[⛔]** No se encontró un stream con ID: `{stream_id}`")
        return
    
    try:
        # Detener el evento de stop
        active_streams[stream_id]['stop_event'].set()
        
        # Esperar un momento para que el hilo termine
        active_streams[stream_id]['thread'].join(timeout=1)
        
        # Eliminar de los streams activos
        del active_streams[stream_id]
        
        await message.reply(f"**[✅]** Stream con ID `{stream_id}` detenido exitosamente.")
    
    except Exception as ex:
        await message.reply(f"**[⛔]** Error al detener el stream: {ex}")

# Elimina y crear la carpeta downloads
@handle_errors
async def clear(client: Client, message: Message):
    await message.delete()
    msg = await message.reply("**[👾]** Limpiando carpeta downloads...")
    await asyncio.sleep(2)
    try:
        if os.path.exists('downloads'):
            shutil.rmtree('downloads')  # Elimina la carpeta y todo su contenido
            await msg.edit(f'**[✅]** La carpeta downloads ha sido eliminada')
            await asyncio.sleep(2)
            #print(f"La carpeta downloads ha sido eliminada.")
        
        # Crear la carpeta nuevamente
        os.makedirs('downloads')
        #print(f"La carpeta downloads_path ha sido creada nuevamente.")
        await msg.edit(f'**[✅]** Creada la carpeta downloads')
        await asyncio.sleep(2)
        await msg.delete(True)
    except Exception as e:
        await msg.edit(f"**[⛔]** Error al limpiar la carpeta: {str(e)}")
        #print(f"Hubo un error: {e}")

# Función para la AI
@handle_errors
async def gemini(client: Client, message: Message):
    msg = await message.reply("**[👾]** Esperando a la IA...")

    # Obtener el prompt
    if message.reply_to_message:
        prompt = message.reply_to_message.text or message.reply_to_message.caption
    else:
        prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None

    if not prompt:
        await msg.edit("**[⛔]** Por favor proporciona un texto para generar la respuesta.")
        return

    # Audio flag
    try:
        audio = message.text.split("|")[-1].strip()
    except:
        audio = 'no'

    salida_audio = 'respuesta.mp3'

    # Añadir mensaje del usuario al historial
    groq_session.add_user_message(prompt)

    # Obtener respuesta de Groq
    await msg.edit("**[👾]** Generando respuesta...")
    try:
        respuesta = groq_session.chat()  # <-- síncrono, Groq SDK aún no tiene async
    except Exception as e:
        await msg.edit(f"**[⛔]** Error al contactar Groq: `{e}`")
        return

    if audio == 'audio':
        respuesta_formateada = formatear_markdown(respuesta)
        await msg.edit("**[👾]** La IA está grabando un audio...")
        await generar_audio(respuesta_formateada, 'es', salida_audio)
        await msg.delete(True)
        if os.path.exists(salida_audio):
            status_msg = await message.reply("**[👾]** Subiendo...")
            with open(salida_audio, 'rb') as f:
                await message.reply_voice(f)
            os.remove(salida_audio)
            await status_msg.delete(True)
        else:
            await message.reply("**[⛔]** No se pudo generar el archivo de audio.")
    else:
        mm = await msg.edit("**[👾]** Enviando respuesta...")
        respuesta_fragmentos = dividir_respuesta(respuesta)
        for fragmento in respuesta_fragmentos:
            await message.reply(fragmento)
            await asyncio.sleep(1)
        await mm.delete(True)

@handle_errors
async def gemini_audio(client: Client, message: Message):
    msg = await message.reply("**[👾]** Esperando a la IA...")
    if message.reply_to_message:
        prompt = message.reply_to_message.text or message.reply_to_message.caption
    else:
        prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
    if not prompt:
        await msg.edit("**[⛔]** Por favor proporciona un texto para generar la respuesta.")
        return
    try:
        lang = message.text.split("|")[-1]
    except:
        lang = 'es'
    await msg.delete(True)
    audio = await message.reply(f"**[👾]** Generando audio <{lang}>...")
    salida_audio= 'respuesta.wav'
    try:
        await generar_audio(prompt, lang, salida_audio)
        if os.path.exists(salida_audio):
            with open(salida_audio, 'rb') as f:
                await message.reply_voice(f)
            os.remove(salida_audio)
            await audio.delete(True)
        else:
            await message.reply("**[⛔]** No se pudo generar el archivo de audio.")
    except Exception as e:
        await message.reply(f"**[⛔]** Error al generar o subir audio: {str(e)}")

@handle_errors
async def gemini_file(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("**[⛔]** Debes responder a un documento.")
        return
    try:
        try:
            audio = message.text.split("|")[-1]
        except:
            audio = 'no'
        salida_audio= 'respuesta.mp3'
        if audio == 'audio':
            msg = await message.reply("**[👾]** Descargando archivo...")
            media = message.reply_to_message.document
            media_path = await client.download_media(media, file_name=media.file_name)
            prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
            if not prompt:
                await msg.edit("**[⛔]** Por favor proporciona un texto para generar la respuesta.")
                return
            await msg.edit(f"**[👾]** AI analizando el documento {media.file_name}...")
            response = await analizar_files(prompt, media_path)
            respuesta_formateada = formatear_markdown(response)
            await msg.edit("**[👾]** La AI esta grabando un audio...")
            await generar_audio(respuesta_formateada, 'es', salida_audio)
            with open(salida_audio, 'rb') as f:
                await message.reply_voice(f)
            os.remove(salida_audio)
            os.remove(media_path)
            await msg.delete(True)
        else:
            msg = await message.reply("**[👾]** Descargando archivo...")
            media = message.reply_to_message.document
            media_path = await client.download_media(media, file_name=media.file_name)
            prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
            if not prompt:
                await msg.edit("**[⛔]** Por favor proporciona un texto para generar la respuesta.")
                return
            await msg.edit(f"**[👾]** AI analizando el documento {media.file_name}...")
            response = await analizar_files(prompt, media_path)
            await msg.delete(True)
            split = dividir_respuesta(response)
            for fragmento in split:
                await message.reply(fragmento)
                time.sleep(1)
            os.remove(media_path)
    except Exception as ex:
        await message.reply(f"**[⛔]** Error al procesar su archivo: {ex}")

@handle_errors
async def gemini_image(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return
    try:
        msg = await message.reply("**[👾]** pipopi...")
        prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
        if not prompt:
            await msg.edit("**[⛔]** Por favor proporciona un texto para generar la respuesta.")
            return
        time.sleep(5)
        await msg.edit(f"**[👾]** La AI esta generando una imagen...")
        image = await generar_imagen_hf(prompt)
        with open('ai.jpg', 'rb') as f:
            await message.reply_photo(image)
        os.remove('ai.jpg')
        await msg.delete(True)
    except Exception as ex:
        await message.reply(f"**[⛔]** Error al procesar su archivo: {ex}")


# ----------------------AFK comandos

# Variables globales para el estado AFK (agregar al inicio del archivo junto con las otras variables globales)
AFK = False
AFK_REASON = ""
AFK_TIME = ""
USERS = {}
GROUPS = {}

# Funciones auxiliares para AFK (agregar junto con las otras funciones auxiliares)
def get_chat_id(message: Message):
    """Obtiene el ID del chat del mensaje entrante"""
    return message.chat.id

def subtract_time(start, end):
    """Obtiene tiempo humanizado"""
    subtracted = humanize.naturaltime(start - end)
    return str(subtracted)

# Handlers de AFK (agregar junto con los otros handlers)
@handle_errors
async def set_afk(client: Client, message: Message):
    """Establece el estado AFK"""
    global AFK_REASON, AFK, AFK_TIME
    
    cmd = message.command
    afk_text = ""

    if len(cmd) > 1:
        afk_text = " ".join(cmd[1:])

    if isinstance(afk_text, str):
        AFK_REASON = afk_text

    AFK = True
    AFK_TIME = datetime.datetime.now()

    await message.reply(f"**[👾]** Modo AFK activado.\nRazón: `{AFK_REASON}`")
    await message.delete()

@handle_errors
async def unset_afk(client: Client, message: Message):
    """Desactiva el estado AFK"""
    global AFK, AFK_TIME, AFK_REASON, USERS, GROUPS

    if AFK:
        last_seen = subtract_time(datetime.datetime.now(), AFK_TIME).replace("ago", "").strip()
        await message.edit(
            f"**[👾]** Mientras estabas ausente (por {last_seen}), "
            f"recibiste {sum(USERS.values()) + sum(GROUPS.values())} "
            f"mensajes de {len(USERS) + len(GROUPS)} chats"
        )
        AFK = False
        AFK_TIME = ""
        AFK_REASON = ""
        USERS = {}
        GROUPS = {}
        await asyncio.sleep(5)

    await message.delete()

@handle_errors
async def collect_afk_messages(client: Client, message: Message):
    """Maneja los mensajes recibidos mientras el usuario está AFK"""
    if AFK:
        last_seen = subtract_time(datetime.datetime.now(), AFK_TIME)
        is_group = message.chat.type in ["supergroup", "group"]
        CHAT_TYPE = GROUPS if is_group else USERS
        
        if get_chat_id(message) not in CHAT_TYPE:
            text = (
                f"<b>[👾] Este es un mensaje automático.</b>\n\n"
                f"<i>No estoy disponible en este momento.</i>\n"
                f"Última vez visto: {last_seen}\n"
                f"Razón:\n<blockquote expandable>{AFK_REASON}</blockquote>\n"
                f"<b>Te responderé cuando regrese.</b>"
            )
            await message.reply(text)
            CHAT_TYPE[get_chat_id(message)] = 1
            return
            
        if get_chat_id(message) in CHAT_TYPE:
            if CHAT_TYPE[get_chat_id(message)] == 50:
                text = (
                    f"<b>[👾] Este es un mensaje automático.</b>\n\n"
                    f"Última vez visto: {last_seen}\n"
                    f"Esta es la 10ma vez que te digo que estoy AFK...\n"
                    f"Te responderé cuando regrese.\n"
                    f"No más mensajes automáticos para ti."
                )
                await message.reply(text)
            elif CHAT_TYPE[get_chat_id(message)] > 50:
                return
            elif CHAT_TYPE[get_chat_id(message)] % 5 == 0:
                text = (
                    f"<b>[👾] Hey, aún no he vuelto.</b>\n\n"
                    f"Última vez visto: {last_seen}\n"
                    f"Sigo ocupado: \n<blockquote expandable>{AFK_REASON}</blockquote>\n"
                    f"Intenta más tarde."
                )
                await message.reply(text)

        CHAT_TYPE[get_chat_id(message)] += 1

@handle_errors
async def auto_unset_afk(client: Client, message: Message):
    """Desactiva automáticamente el estado AFK cuando el usuario envía un mensaje"""
    global AFK, AFK_TIME, AFK_REASON, USERS, GROUPS
    
    if AFK and not message.text.startswith(('-afk', '-unafk')):
        last_seen = subtract_time(datetime.datetime.now(), AFK_TIME).replace("ago", "").strip()
        reply = await message.reply(
            f"**[👾]** Mientras estabas ausente (por {last_seen}), "
            f"recibiste {sum(USERS.values()) + sum(GROUPS.values())} "
            f"mensajes de {len(USERS) + len(GROUPS)} chats"
        )
        AFK = False
        AFK_TIME = ""
        AFK_REASON = ""
        USERS = {}
        GROUPS = {}
        await asyncio.sleep(5)
        await reply.delete()

@handle_errors
async def save_forward_message(client: Client, message: Message):
    if not message.from_user.id in OWNER_ID:
        return
    
    try:
        # Verificar si se proporcionaron los argumentos necesarios
        if len(message.command) < 4:
            await message.reply("**[⛔]** Uso: `-save [id_canal_origen] [id_mensaje_inicial] [cantidad de mensajes] [id_canal_destino] [topic_id(opcional)]`")
            return
        try:
            source_channel = int(message.command[1])
            start_id = int(message.command[2])
            count = int(message.command[3])
            destination_channel = int(message.command[4])
        except Exception as e:
            await message.reply(f"**[⛔]** Error: {e}")
            return

        # Verificar topic_id
        topic_id = None 
        if len(message.command) > 5:
            try:
                topic_id = int(message.command[5])
            except ValueError:
                await message.reply("**[⛔]** El ID del tema debe ser un número entero.")
                return

        # Mensaje de estado inicial
        status_text = f"**[👾]** Reenviando mensajes desde `{source_channel}` a `{destination_channel}`"
        if topic_id:
            status_text += f" con el tema `{topic_id}`"
        status_text += "..."
        status_msg = await message.reply(status_text)

        # Contadores
        success_count = 0
        error_count = 0
        total_messages = count
        start_time = datetime.datetime.now()

        for current_message_id in range(start_id, start_id + count):
            try:
                # Pausa de 1 minutos cada 500 mensajes
                if success_count > 0 and success_count % 100 == 0:
                    await status_msg.edit(f"**[⏳]** Pausa de 5 segundos para evitar flood después de {success_count} mensajes...")
                    await asyncio.sleep(5)  # 5 minutos = 300 segundos
                
                # Obtener mensaje
                msg = await client.get_messages(source_channel, current_message_id)
                if not msg or msg.empty:
                    print(f"Mensaje {current_message_id} no encontrado o vacío")
                    error_count += 1
                    continue

                # Parámetros de reenvío
                forward_params = {
                    "chat_id": destination_channel,
                    "from_chat_id": source_channel,
                    "message_ids": current_message_id,
                    "disable_notification": True,
                    "hide_sender_name": True
                }
                if topic_id:
                    forward_params["message_thread_id"] = topic_id

                # Reenviar mensaje
                await asyncio.sleep(3)
                await client.forward_messages(**forward_params)
                success_count += 1

                # Actualizar progreso cada 10 mensajes
                if success_count % 1 == 0:
                    progress = (success_count / total_messages) * 100
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    
                    progress_text = (
                        f"**[👾]** Progreso: {progress:.1f}%\n"
                        f"```\n{progress_bar}```\n"
                        f"✅ Reenviados: {success_count}/{total_messages}\n"
                        f"⚠️ Errores: {error_count}\n"
                        f"🔄 ID actual: {current_message_id}"
                    )
                    if topic_id:
                        progress_text += f"\n📑 Topic ID: {topic_id}"
                    
                    await status_msg.edit(progress_text)

            except FloodWait as fw:
                await status_msg.edit(f"**[⏳]** Esperando {fw.x} segundos debido a limitaciones de Telegram...")
                await asyncio.sleep(fw.value)
            except Exception as e:
                error_count += 1
                print(f"Error reenviando mensaje {current_message_id}: {str(e)}")
                continue

        # Mensaje final
        elapsed_time = datetime.datetime.now() - start_time
        final_text = (
            f"**[👾]** Tarea completada!\n"
            f"✅ Mensajes reenviados: {success_count}\n"
            f"⚠️ Errores: {error_count}\n"
            f"⏱️ Tiempo total: {str(elapsed_time).split('.')[0]}"
        )
        if topic_id:
            final_text += f"\n📑 Topic ID: {topic_id}"
        final_text += f"\n📅 {datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}"
        
        await status_msg.edit(final_text)

    except Exception as e:
        await message.reply(f"**[⛔]** Error: {e}")

def is_playlist(url):
    return "/playlist/" in url

def spotuserinfo():
    try:
        with open(get_config_file(), "r") as file:
            userinfo = json.load(file)
            client_id = userinfo["client_id"]
            client_secret = userinfo["client_secret"]
            file.close()
        print(f"client_id: {client_id}\nclient_secret: {client_secret}")
        return client_id, client_secret
    except:
        os.system("echo Y | spotdl --generate-config")

async def reset(client: Client, message: Message):
    """ Resetea el chat con la IA """
    if message.from_user.id not in OWNER_ID:
        return
    try:
        if groq_session:
            groq_session.reset()
            msg = await message.reply("**[👾]** Chat con la IA reseteado.")
            await asyncio.sleep(2)
            await msg.delete(True)
        else:
            msg = await message.reply("**[⛔]** No hay chat con la IA para resetear.")
            await asyncio.sleep(2)
            await msg.delete(True)
    except Exception as e:
        msg = await message.reply(f"**[⛔]** Error al resetear el chat: {str(e)}")
        await asyncio.sleep(2)
        await msg.delete(True)
    await message.delete()
    


@handle_errors
async def download_music(client: Client, message: Message):
    if message.from_user.id in OWNER_ID:
        if len(message.command) < 2:
            await message.reply(
                "**[❌] Error:** Debes proporcionar una URL de Spotify.\n**Uso:** `-dlmusic URL`",
                quote=True
            )
            return

        url = message.command[1]
        status_msg = await message.reply("**[🔍] Procesando enlace...**", quote=True)
        temp_dir = "downloads"

        try:
            client_id, client_secret = spotuserinfo()
            print(f"client_id: {client_id}\nclient_secret: {client_secret}")
            # Evita inicializarlo múltiples veces
            if not SpotifyClient._instance:
                spotdl = Spotdl(
                    client_id=client_id, client_secret=client_secret
                )

            options = DownloaderOptions(
                output=temp_dir,
                format="mp3",
                quality="best",
                save_file=False,
                overwrite="skip",
                log_level="CRITICAL",
                log_level_console="ERROR",  # Evita problemas con el live display
                simple_tui=True
            )

            # Obtener la canción
            # Si es una playlist, extraer todas las canciones
            if is_playlist(url):
                await status_msg.edit("**[📂] Detectada playlist, obteniendo canciones...**")

                songs = spotdl.search(url)  # Obtiene todas las canciones
                print(songs)
                if not songs:
                    await message.reply("**[❌] No se encontraron canciones en la playlist.**", quote=True)
                    return
            else:
                # Si no es una playlist, descargar la canción individualmente
                songs = [Song.from_url(url)]

            await status_msg.edit("**[🎵] Canción encontrada**\n**[⏬] Iniciando descarga...**")
            processed = 0

            # Función para descargar la canción en un hilo separado con su propio event loop
            def sync_download_song(song, options):
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Crear el Downloader en este hilo, de modo que se asocie al nuevo loop
                    local_downloader = Downloader(options)
                    return local_downloader.download_song(song)
                finally:
                    new_loop.close()

            for song in songs:
                await status_msg.edit(f"**[⏬] Descargando:** `{song.name}` - `{song.artists[0]}`")
                file_path_str = None  # Inicializar antes del try
                try:
                    download_path = await asyncio.to_thread(sync_download_song, song, options)
                    _, file_path = download_path  # Extrae solo la ruta del archivo
                    file_path_str = str(file_path) if file_path else None # Convierte a string si es necesario
                    print(download_path)
                except Exception as e:
                    print(f"Error al descargar {song.name}: {e}")
                    download_path = None

                if file_path_str and os.path.exists(file_path_str):
                    await status_msg.edit(f"**[📤] Subiendo:** `{song.name}` - `{song.artists[0]}`")
                    try:
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=file_path_str,
                            caption=f"**Título:** `{song.name}`\n**Artista:** `{song.artists[0]}`\n**Álbum:** `{song.album_name}`",
                            title=song.name,
                            performer=song.artists[0]
                        )
                        processed += 1
                    except Exception as upload_error:
                        await message.reply(
                            f"**[❌] Error al subir:** `{str(upload_error)}`", quote=True
                        )

                    try:
                        os.remove(file_path_str)
                    except Exception as file_error:
                        print(f"Error al eliminar archivo: {file_error}")
                else:
                    await message.reply(
                        f"**[❌] Error al descargar:** `{song.name}`", quote=True
                    )

            if processed > 0:
                await status_msg.edit(
                    f"**[✅] Descarga completada:** {processed}/{len(songs)} canción(es) procesada(s)."
                )
            else:
                await status_msg.edit("**[❌] No se pudo descargar ninguna canción.**")

        except Exception as e:
            error_msg = str(e)
            print(f"Error en download_music: {error_msg}")
            await status_msg.edit(f"**[❌] Error:** `{error_msg}`")
            
# -----------------------------------------------------
# TROLEO A ENIGMO
# Estado en memoria
ID_GRUPO_OBJETIVO = -1002509194290
RANDOM = {"activo": False}
UF = {"activo": False}

# Diccionario con múltiples usuarios y sus mensajes personalizados
usuarios_respuestas = {
    8001145481: {"mensaje": "CHIVATON, COMUNISTA, CAREPINGA, DOBLE  MORAL, TRIPLEHIJUEPUTA", "activo": False}
}

# Comando para activar
async def activar_respuesta(_, message: Message):
    # Verificamos si ya todos están activos
    if all(user["activo"] for user in usuarios_respuestas.values()):
        for user in usuarios_respuestas.values():
            user["activo"] = False
        msg = await message.reply_text("**[❌]** HA SIDO DESACTIVADO")
        #await message.delete()
        await asyncio.sleep(5)
        await msg.delete(True)
    # Activamos todos
    else:
        for user in usuarios_respuestas.values():
            user["activo"] = True
        msg = await message.reply_text("**[✅]** ACTIVADO.")
        #await message.delete()
        await asyncio.sleep(5)
        await msg.delete(True)
        
# Función para la AI
@handle_errors
async def autoia(client: Client, message: Message):
    prompt = message.text

    status = await message.reply("Pera")
    await status.delete(True)

    try:
        groq_session.add_user_message(prompt)
        respuesta = groq_session.chat()
    except Exception as e:
        return

    fragmentos = dividir_respuesta(respuesta)
    for frag in fragmentos:
        await message.reply(frag)
        await asyncio.sleep(1)


# Escucha mensajes en el grupo y responde si corresponde
'''@bot.on_message(filters.chat(ID_GRUPO_OBJETIVO))
async def responder_auto(_, message: Message):
    user_id = message.from_user.id
    datos = usuarios_respuestas.get(user_id)
    if datos and datos["activo"]:
        await message.reply_text(datos["mensaje"])
    elif RANDOM["activo"]:
        quote = await get_quote()
        print(quote)
        await message.reply_text(quote)'''
        
@bot.on_message((filters.group | filters.channel) & ~filters.me & filters.reply & filters.text)
async def responder_a_replies(client: Client, message: Message):
    if not UF.get("activo"):
        return

    # Verifica si respondieron a un mensaje tuyo
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
        await autoia(client, message)

# -----------------------------------------------------
# MENSAGES RANDOM PARA EL GRUPO
async def active_random(_, message: Message):
    # Verificamos si ya todos están activos
    if RANDOM["activo"]:
        RANDOM["activo"] = False
        msg = await message.reply_text("**[❌]** HA SIDO DESACTIVADO")
        #await message.delete()
        await asyncio.sleep(5)
        await msg.delete(True)
    # Activamos todos
    else:
        RANDOM["activo"] = True
        msg = await message.reply_text("**[✅]** ACTIVADO.")
        #await message.delete()
        await asyncio.sleep(5)
        await msg.delete(True)
        
# -----------------------------------------------------
# MENSAGES IA PARA EL GRUPO
async def active_uf(_, message: Message):
    # Verificamos si ya todos están activos
    if UF["activo"]:
        UF["activo"] = False
        msg = await message.reply_text("**[❌]** HA SIDO DESACTIVADO")
        #await message.delete()
        await asyncio.sleep(5)
        await msg.delete(True)
    # Activamos todos
    else:
        UF["activo"] = True
        msg = await message.reply_text("**[✅]** ACTIVADO.")
        await asyncio.sleep(5)
        await msg.delete(True)

# -----------------------------------------------------
# Descarga de animados de Cartoon

async def send_plantilla(name, desc, cap, year, lang, image, points):
    """Envía información de la serie a Telegram"""
    #chat_id = bot.get_chat(chat)
    text = (f'**📺 Serie:** {name}\n'
            f'**📅 Año:** {year}\n'
            f'**🌎Idioma:** {lang}\n'
            f'**🎬 Episodios:** {cap}\n'
            f'**⭐️Puntuacion:** {points}/10\n\n'
            f'**📝 SINOPSIS**\n>{desc}')
    msg = await bot.send_photo(LOG_CHANNEL, image, text)
    return msg

def format_to_windows_filename(input_string):
    """Limpia nombres de archivos para Windows"""
    invalid_chars = r'[<>:"/\\|?*]'
    reserved_names = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    cleaned_string = re.sub(invalid_chars, '_', input_string)
    cleaned_string = cleaned_string.rstrip(' .')
    if cleaned_string.upper() in reserved_names:
        cleaned_string += '_file'
    return cleaned_string if cleaned_string else 'default_file'

def create_progress_bar(current, total, status_msg, operation, length=15):
    if total == 0:
        text = f'┎ **{operation}**\n┠ **PROCESSED:** {humanize.naturalsize(current)} (Size Unknown)\n┖ **ENGINE:** __#ELDEOENELANO__'
        return text
    filled_length = int(length * current // total)
    bar = '⬢' * filled_length + '⬡' * (length - filled_length)
    percentage = round((current / total) * 100, 2)
    text = f'┎ **{operation}**\n┠[{bar}]\n┠PERCENTAGE: {percentage}%\n┠ **PROCESSED:** {humanize.naturalsize(current)}/{humanize.naturalsize(total)}\n┖ **ENGINE:** __#ELDEOENELANO__'
    return text

async def progress_callback(current, total, status_msg, operation):
    global last_update_time
    if time.time() - last_update_time > update_time:
        last_update_time = time.time()
        progress_bar = create_progress_bar(current, total, status_msg, operation)
        print(progress_bar)
        if status_msg:
            await status_msg.edit(text=f"{progress_bar}")

async def upload_video(path, status_msg=None):
    global filename
    filename = os.path.basename(path)
    """Sube un video a Telegram"""
    try:
        # Obtener información del video
        probe = ffmpeg.probe(path)
        duration = int(float(probe.get('format', {}).get('duration', 0)))

        # Generar miniatura
        thumbnail_path = f"{path}_thumb.jpg"
        try:
            (
            ffmpeg
            .input(path, ss=duration//2 if duration > 0 else 0)
            .filter('scale', 320, -1)
            .output(thumbnail_path, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
            )
        except Exception:
            print(f"Error generando miniatura para {path}")
            thumbnail_path = None

        # Subir video
        message = await bot.send_video(
            LOG_CHANNEL,
            path,
            caption=os.path.basename(path),
            duration=duration,
            thumb=thumbnail_path if thumbnail_path else None,
            progress=progress_callback,
            progress_args=(status_msg, "UPLOADING")
        )
        # Limpiar archivos temporales
        os.unlink(path)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.unlink(thumbnail_path)
        return
    except Exception as e:
        print(f"Error subiendo video {path}: {str(e)}")
        return None

async def descargar_video(url, folder, nombre, status_msg):
    """Descarga un video de una URL"""
    nombre_clean = nombre.replace('\n','').replace('  ', '')

    opciones = {
        'format': 'best',
        'outtmpl': f'downloads/{nombre_clean}.%(ext)s',
        'downloader': 'ffmpeg',
        'hls-use-mpegts': True,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(progress_callback(d['downloaded_bytes'], d.get('total_bytes', 0), status_msg, "DOWNLOADING"), bot.loop)]
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            if not os.path.exists(f'downloads/{nombre_clean}.mp4'):
                info_dict = ydl.extract_info(url, download=True)
                video_url = ydl.prepare_filename(info_dict)
                if video_url.split('.')[-1] == 'unknown_video':
                    os.unlink(video_url)
                    return None
                return video_url
    except Exception as e:
        print(f"Error descargando {nombre_clean}: {str(e)}")
        return None
    

@handle_errors
async def download_cartoon(client: Client, message: Message):
    if message.from_user.id not in OWNER_ID:
        return
    if len(message.command) < 2:
        await message.reply("**[⛔]** Uso: `-cartoon [enlace serie]`")
        return
    url = message.command[1]
    status_msg = await message.reply("**[👾]** Procesando enlace...")
    await bot.pin_chat_message(chat_id=message.chat.id, message_id=status_msg.id, disable_notification=True)
    try:
        cartoons = Cartoons()
        details = cartoons.get_series_details(url)
        folder = format_to_windows_filename(details['title'].split('\n')[0])

        msg = await send_plantilla(details['title'], details['review'], details['episodes_count'], details['year'], details['language'], details['image'], details['rating'])
        await bot.pin_chat_message(chat_id=LOG_CHANNEL, message_id=msg.id, disable_notification=True)
        await status_msg.edit(f"**[👾]** Descargando {details['title']}...")
        for episode in details['episodes']:
            await status_msg.edit(f"**[👾]** Descargando episodio: {episode['title']}")
            try:
                if not os.path.exists(f'downloads/{format_to_windows_filename(episode["title"])}.mp4'):
                    download_path = await descargar_video(episode['iframe'], folder, format_to_windows_filename(episode['title']), status_msg)
                    if download_path:
                        await upload_video(download_path, status_msg)
                else:
                    await status_msg.edit(f'YA DESCARGADO {episode["title"]}')
            except Exception as e:
                await status_msg.edit(f"Error descargando episodio: {str(e)}")
                continue

        await status_msg.edit("**[✅]** Descarga completada.")
    except Exception as ex:
        await message.reply(f"**[⛔]** Error general: {str(ex)}")



# -----------------------------------------------------
# Registrar los handlers
bot.add_handler(MessageHandler(
    ping,
    filters.command("ping", prefixes=['.']) & owner_only
))
bot.add_handler(MessageHandler(
    start,
    filters.command("start", prefixes=['-']) & owner_only
))
async def urlsave_handler(client, message):
    asyncio.create_task(save_and_forward_message(client, message))

bot.add_handler(MessageHandler(
    urlsave_handler,
    filters.command("urlsave", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    userinfo, 
    filters.command("userinfo", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    get_chat_info, 
    filters.command("chatinfo", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    upload_to_story,
    filters.command("story", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    clear,
    filters.command("clear", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    stream_video,
    filters.command("stream", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    stop_stream,
    filters.command("stopstream", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    gemini,
    filters.command("ai", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(gemini_audio,
    filters.command("aiaudio", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(gemini_file,
    filters.command("aifile", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(gemini_image,
    filters.command("aiimage", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    set_afk,
    filters.command("afk", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    unset_afk,
    filters.command("unafk", prefixes=['-']) & owner_only
))
async def save_handler(client, message):
    asyncio.create_task(save_forward_message(client, message))

bot.add_handler(MessageHandler(
    save_handler,
    filters.command("save", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    download_music,
    filters.command("dlmusic", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    help,
    filters.command("help", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    reset,
    filters.command("reset", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    activar_respuesta,
    filters.command("troll", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    active_random,
    filters.command("random", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    active_uf,
    filters.command("uf", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    download_cartoon,
    filters.command("cartoon", prefixes=['-']) & owner_only
))
bot.add_handler(MessageHandler(
    collect_afk_messages,
    ((filters.group & filters.mentioned) | filters.private) & ~filters.me
))
bot.add_handler(MessageHandler(
    auto_unset_afk,
    filters.me
))

# -------------Inicio del bot
async def startup_message():
    """Envía un mensaje al propietario cuando el bot inicia"""
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        startup_text = f"""**[👾] Bot Iniciado**
        
┎ Estado: Operativo
┠ Fecha: {current_time}
┠ Versión: {VERSION}
┖ Engine: {ENGINE}
"""
        
        # Enviar mensaje a cada propietario definido en OWNER_ID
        for owner in OWNER_ID:
            try:
                await bot.send_message(owner, startup_text)
            except Exception as e:
                print(f"Error enviando mensaje de inicio a {owner}: {e}")
                
    except Exception as e:
        print(f"Error en startup_message: {e}")

def web_home(request):
    resp = requests.get('https://v2.jokeapi.dev/joke/Programming?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&format=txt&type=single').text
    return web.Response(text=f"👾 {resp} 👾")

async def server():
    # Configuración de la aplicación
    app = web.Application()
    
    # Configuración de CORS en aiohttp
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )
    
    app.router.add_get("/", web_home)

    # Añadir soporte de CORS a cada ruta
    for route in list(app.router.routes()):
        cors.add(route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 7860))  # Puerto dinámico para Heroku
    site = web.TCPSite(runner, "0.0.0.0", port)

    #print("Starting server")
    #await site.start()
    #await asyncio.Future()  # run forever

# Configuración para la gestión de errores y desconexión
async def main():
    await bot.start()
    print("👾 Bot Started...")
    bot.loop.create_task(startup_message())  # Programar la tarea de inicio
    #asyncio.create_task(server())  # Iniciar el servidor web
    
    # Mantener el bot en ejecución hasta que se detenga
    await pyrogram.idle()

if __name__ == "__main__":
    # Configurar el bucle de eventos para ejecutar el bot de manera asíncrona
    loop = asyncio.get_event_loop()
    with suppress(KeyboardInterrupt):
        loop.run_until_complete(main())
