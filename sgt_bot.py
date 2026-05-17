import logging
import asyncio
import httpx
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = "8997496960:AAHBVGfIGMsSnMFdkcPpJhCCfmnBDRpNZOw"
SUPABASE_URL = "https://vfouthbacsoeqpexhpnf.supabase.co"
SUPABASE_KEY = "sb_publishable_lx3jF7VfUhSRUvgcB8EB5A_9yGPAM7Q"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.WARNING)

def fecha_hoy():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

async def db_insertar(datos):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SUPABASE_URL}/rest/v1/tareas", headers=HEADERS, json=datos)
        return r.json()

async def db_obtener(filtro=""):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/tareas?order=id.desc{filtro}", headers=HEADERS)
        return r.json()

async def db_actualizar(id_tarea, datos):
    async with httpx.AsyncClient() as client:
        await client.patch(f"{SUPABASE_URL}/rest/v1/tareas?id=eq.{id_tarea}", headers=HEADERS, json=datos)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(f"Bienvenido al SGT, {nombre}\nSistema de Gestion de Tareas - Poder Judicial\n\nComandos:\n/nueva [descripcion] - Crear tarea\n/urgente [descripcion] - Tarea alta prioridad\n/mis_tareas - Sus tareas pendientes\n/todas - Todas las tareas activas\n/completar [ID] - Marcar completada\n/estado [ID] [estado] - Actualizar estado\n/ayuda - Ver comandos")

async def cmd_nueva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Ejemplo: /nueva Enviar oficio a Contraloria")
        return
    descripcion = " ".join(context.args)
    autor = update.effective_user.first_name
    result = await db_insertar({"titulo": descripcion, "prioridad": "Media", "estado": "Pendiente", "responsable": autor, "fecha_creacion": fecha_hoy(), "origen": "telegram"})
    tid = result[0]["id"] if isinstance(result, list) and result else "?"
    await update.message.reply_text(f"TAREA #{tid} CREADA\n\n{descripcion}\nResponsable: {autor}\nPrioridad: Media")

async def cmd_urgente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Ejemplo: /urgente Firma del director antes de las 17:00")
        return
    descripcion = " ".join(context.args)
    autor = update.effective_user.first_name
    result = await db_insertar({"titulo": descripcion, "prioridad": "Alta", "estado": "Pendiente", "responsable": autor, "fecha_creacion": fecha_hoy(), "origen": "telegram"})
    tid = result[0]["id"] if isinstance(result, list) and result else "?"
    await update.message.reply_text(f"TAREA URGENTE #{tid} CREADA\n\n{descripcion}\nResponsable: {autor}\nPrioridad: ALTA")

async def cmd_mis_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    autor = update.effective_user.first_name
    tareas = await db_obtener(f"&responsable=eq.{autor}&estado=neq.Completada")
    if not isinstance(tareas, list) or not tareas:
        await update.message.reply_text(f"{autor}, no tiene tareas pendientes.")
        return
    lines = [f"TAREAS DE {autor.upper()}\n"]
    for t in tareas:
        pri = "[ALTA]" if t.get("prioridad") == "Alta" else "[Media]"
        lines.append(f"{pri} #{t['id']} - {t['titulo']}\n     Estado: {t['estado']}")
    await update.message.reply_text("\n".join(lines))

async def cmd_todas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tareas = await db_obtener("&estado=neq.Completada")
    if not isinstance(tareas, list) or not tareas:
        await update.message.reply_text("No hay tareas activas.")
        return
    lines = ["TODAS LAS TAREAS ACTIVAS\n"]
    for t in tareas:
        pri = "[ALTA]" if t.get("prioridad") == "Alta" else "[Media]"
        lines.append(f"{pri} #{t['id']} - {t['titulo']}\n     {t.get('responsable','')} | {t['estado']}")
    await update.message.reply_text("\n".join(lines))

async def cmd_completar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Ejemplo: /completar 3")
        return
    try:
        tid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("El ID debe ser un numero.")
        return
    tareas = await db_obtener(f"&id=eq.{tid}")
    if not isinstance(tareas, list) or not tareas:
        await update.message.reply_text(f"No se encontro la tarea #{tid}.")
        return
    await db_actualizar(tid, {"estado": "Completada"})
    await update.message.reply_text(f"TAREA #{tid} COMPLETADA\n\n{tareas[0]['titulo']}")

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /estado [ID] [estado]\nEstados: Pendiente, En proceso, En revision, Completada\nEjemplo: /estado 2 En proceso")
        return
    try:
        tid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("El ID debe ser un numero.")
        return
    estados = ["Pendiente", "En proceso", "En revision", "Completada"]
    nuevo = " ".join(context.args[1:])
    if nuevo not in estados:
        await update.message.reply_text("Estado no valido.\nUse: " + ", ".join(estados))
        return
    tareas = await db_obtener(f"&id=eq.{tid}")
    if not isinstance(tareas, list) or not tareas:
        await update.message.reply_text(f"No se encontro la tarea #{tid}.")
        return
    anterior = tareas[0]["estado"]
    await db_actualizar(tid, {"estado": nuevo})
    await update.message.reply_text(f"TAREA #{tid} ACTUALIZADA\n\n{tareas[0]['titulo']}\n{anterior} -> {nuevo}")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /ayuda para ver los comandos.\nPara crear una tarea: /nueva [descripcion]")

async def main():
    print("=" * 50)
    print("  SGT Bot - Poder Judicial")
    print("  Conectando con Supabase...")
    print("=" * 50)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("nueva", cmd_nueva))
    app.add_handler(CommandHandler("urgente", cmd_urgente))
    app.add_handler(CommandHandler("mis_tareas", cmd_mis_tareas))
    app.add_handler(CommandHandler("todas", cmd_todas))
    app.add_handler(CommandHandler("completar", cmd_completar))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_desconocido))
    print("  Bot activo. Esperando mensajes...")
    print("  Presione Ctrl+C para detener.\n")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())