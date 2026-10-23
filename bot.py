import asyncio
from contextlib import suppress
import datetime
import os

from pyrogram import Client, filters
from pyrogram.handlers.message_handler import MessageHandler
import pyrogram

from utils.config import (
    OWNER_ID, NAME, API_ID, API_HASH, MOBILE_NUMBER,
    VERSION, ENGINE, SESSION_STRING
)
from utils.logging import get_logger
from utils.validators import is_owner

logger = get_logger(__name__)

bot = Client(
    f"{NAME}",
    api_id=API_ID,
    api_hash=API_HASH,
    #phone_number=MOBILE_NUMBER,
    session_string=os.environ.get("SESSION_STRING", SESSION_STRING),
    app_version=VERSION,
    device_model=ENGINE
)


def owner_filter(_, __, message):
    return message.from_user and message.from_user.id in OWNER_ID

owner_only = filters.create(owner_filter)


from plugins.admin.commands import start, help_command, ping, changelog, clear
from plugins.admin.server_cmd import server_command
from plugins.admin.join import join_chat, leave_chat
from plugins.downloads.url_commands import url_queue_status, url_cancel_task, urlsave_handler, url_delete_task
from plugins.utils.info import userinfo, get_chat_info, save_handler
from plugins.utils.afk import set_afk, unset_afk, collect_afk_messages, auto_unset_afk
from plugins.ia.commands import gemini, reset
from plugins.media.commands import download_cartoon, download_music, stop_download_music, handle_premium_emoji
from plugins.media.story import upload_to_story
from plugins.media.stream import stream_video, stop_stream
from plugins.fun.commands import (
    troll_add, troll_del, troll_list, troll_toggle, responder_trolls,
    reaccion_add, reaccion_del, reaccion_list, reaccion_toggle, responder_reacciones,
    send_quote, toggle_daily_quotes
)
from plugins.downloads.terabox import terabox_download_handler, terabox_cancel_handler, terabox_status_handler
from plugins.downloads.instagram import instagram_download_handler, instagram_cancel_handler, instagram_status_handler
from plugins.downloads.mega_downloader import mega_download_handler, mega_cancel_handler
from plugins.downloads.facebook import facebook_download_handler, facebook_cancel_handler
from plugins.utils.filters import filter_add, filter_del, filter_list, filter_clear
from plugins.utils.msg_mass import msg_mass, msg_cancel
from plugins.utils.msg_mass import init_db as init_msgmass_db, resume_pending_msgmass
from utils.cleaner import limpiar_handler


bot.add_handler(MessageHandler(start, filters.command("start", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(help_command, filters.command("help", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(ping, filters.command("ping", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(server_command, filters.command("server", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(changelog, filters.command("changelog", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(clear, filters.command("clear", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(join_chat, filters.command("join", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(leave_chat, filters.command("leave", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(url_queue_status, filters.command("urlqueue", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(url_cancel_task, filters.command("urlcancel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(urlsave_handler, filters.command("urlsave", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(url_delete_task, filters.command("urldelete", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(userinfo, filters.command("userinfo", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(get_chat_info, filters.command("chatinfo", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(save_handler, filters.command("save", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(set_afk, filters.command("afk", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(unset_afk, filters.command("unafk", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(gemini, filters.command("ai", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(gemini, filters.command("ia", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(reset, filters.command("reset", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(download_cartoon, filters.command("cartoon", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(download_music, filters.command("dlmusic", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(stop_download_music, filters.command("stopdl", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(upload_to_story, filters.command("story", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(stream_video, filters.command("stream", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(stop_stream, filters.command("stopstream", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(troll_add, filters.command("trolladd", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(troll_del, filters.command("trolldel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(troll_list, filters.command("trolllist", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(troll_toggle, filters.command("trolltoggle", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(responder_trolls, filters.text & ~filters.me), group=1)

bot.add_handler(MessageHandler(reaccion_add, filters.command("reac", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(reaccion_del, filters.command("reacdel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(reaccion_list, filters.command("reaclist", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(reaccion_toggle, filters.command("reactoggle", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(responder_reacciones, ~filters.me), group=2)

bot.add_handler(MessageHandler(send_quote, filters.command("quote", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(toggle_daily_quotes, filters.command("quotedaily", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(terabox_download_handler, filters.command("tdl", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(terabox_cancel_handler, filters.command("tcancel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(terabox_status_handler, filters.command("tstatus", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(instagram_download_handler, filters.command("ig", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(instagram_cancel_handler, filters.command("igcancel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(instagram_status_handler, filters.command("igstatus", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(mega_download_handler, filters.command("mega", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(mega_cancel_handler, filters.command("mcancel", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(facebook_download_handler, filters.command("fb", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(facebook_cancel_handler, filters.command("fbcancel", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(msg_mass, filters.command("msgmass", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(msg_cancel, filters.command("msgcancel", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(limpiar_handler, filters.command("limpiar", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(filter_add, filters.command("filteradd", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(filter_del, filters.command("filterdel", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(filter_list, filters.command("filterlist", prefixes=['-']) & owner_only))
bot.add_handler(MessageHandler(filter_clear, filters.command("filterclear", prefixes=['-']) & owner_only))

bot.add_handler(MessageHandler(handle_premium_emoji, filters.private & owner_only))

bot.add_handler(MessageHandler(collect_afk_messages, ((filters.group & filters.mentioned) | filters.private) & ~filters.me))
bot.add_handler(MessageHandler(auto_unset_afk, filters.me))


async def startup_message():
    from utils.constants import get_emoji
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        startup_text = f"""{get_emoji('joker')} **Bot Iniciado**
┎ Estado: Operativo
┠ Fecha: {current_time}
┠ Versión: {VERSION}
┖ Engine: {ENGINE}
"""
        
        async def send_startup_message(owner_id):
            try:
                msg = await bot.send_message(owner_id, startup_text)
                await asyncio.sleep(30)
                await msg.delete()
            except Exception as e:
                print(f"Error enviando mensaje de inicio a {owner_id}: {e}")
        
        for owner in OWNER_ID:
            asyncio.create_task(send_startup_message(owner))
            
    except Exception as e:
        print(f"Error en startup_message: {e}")

async def main():
    await bot.start()
    print("👾 Bot Started...")
    
    from plugins.fun.troll import init_db as init_troll_db
    from plugins.fun.reactions import init_db as init_reactions_db
    from plugins.fun.quotes import init_db as init_quotes_db
    from plugins.downloads.url_save_queue import init_db as init_url_save_db
    from plugins.utils.filters import init_db as init_filters_db
    from plugins.downloads.url_save_queue import get_pending_tasks, url_save_queue, add_task, update_task_status, TASK_STATUS
    
    init_troll_db()
    init_reactions_db()
    init_quotes_db()
    init_url_save_db()
    init_filters_db()
    init_msgmass_db()
    
    url_save_queue.set_client(bot)
    
    from plugins.downloads.instagram import instagram_queue
    instagram_queue.set_client(bot)
    await instagram_queue.start()
    
    pending_tasks = get_pending_tasks(limit=10)
    print(f"[URL Save] Se encontraron {len(pending_tasks)} tareas pendientes")
    
    await url_save_queue.start()
    
    if pending_tasks:
        for task in pending_tasks:
            task_id_str = str(task["_id"])
            task_status = task.get("status")
            processed_count = task.get("processed_count", 0)
            total_count = task.get("count", 0)
            source_chat_id = task.get("source_chat_id")

            # Cambiar tareas PROCESSING o CANCELLED a PENDING al retomar
            if task_status in [TASK_STATUS["PROCESSING"], TASK_STATUS["CANCELLED"]]:
                update_task_status(task_id_str, TASK_STATUS["PENDING"])
            
            # Enviar mensaje de tarea retomada si tiene progreso
            if source_chat_id and processed_count > 0:
                try:
                    progress_text = (
                        f"![🔄](tg://emoji?id=5258043150110301407) **Tarea retomada**\n"
                        f"![⏳](tg://emoji?id=5258258882022612173) **Progreso:** `{processed_count}/{total_count}`\n"
                        f"![🎭](tg://emoji?id=5258330865674494479) **Tarea:** `{task_id_str}...`\n\n"
                        f"Continuando procesamiento..."
                    )
                    await bot.send_message(source_chat_id, progress_text)
                except Exception as e:
                    print(f"[URL Save] Error enviando mensaje de reanudación: {e}")
            
            await add_task(task_id_str)
    
    from plugins.fun.quotes import start_daily_quotes
    asyncio.create_task(start_daily_quotes(bot))
    asyncio.create_task(startup_message())
    
    asyncio.create_task(resume_pending_msgmass(bot))
    
    await pyrogram.idle()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    with suppress(KeyboardInterrupt):
        loop.run_until_complete(main())
