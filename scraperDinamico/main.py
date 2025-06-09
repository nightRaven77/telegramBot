import asyncio
import os
import polars as pl

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from typing import Dict, List
from datetime import datetime

load_dotenv()

# Estados de la conversación
WAITING_ARTICLE = 1


# Inicia el bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot de búsqueda. Usa /buscar para iniciar."
    )

# Comando /buscar
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 ¿Qué artículo deseas buscar?")
    return WAITING_ARTICLE  # Pasa al siguiente estado

# Escucha el artículo del usuario
async def recibir_articulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articulo = update.message.text

    await update.message.reply_text(f"Buscando '{articulo}'... ⏳")

    df = await scrape_with_playwright(articulo)

    if df.is_empty():
        await update.message.reply_text("❌ No encontré resultados.")
        return ConversationHandler.END

    if not df.is_empty():
        stats = df.select([
            pl.col("Precio").cast(pl.Float64).mean().alias("precio_promedio"),
            pl.col("Precio").cast(pl.Float64).max().alias("precio_max")
        ])
        await update.message.reply_text(
            f"📌 Estadísticas:\n{stats.to_pandas().to_markdown()}"
        )

    # Guarda el CSV temporalmente
    csv_path = f"resultados_{articulo[:20]}.csv"
    df.write_csv(csv_path)

    # Envía el CSV al usuario
    await update.message.reply_document(
        document=open(csv_path, "rb"),
        caption=f"📊 {len(df)} resultados para '{articulo}'"
    )


    # Opcional: Borra el archivo después de enviarlo
    import os
    os.remove(csv_path)

    return ConversationHandler.END

# Scraping con Playwright
async def scrape_with_playwright(articulo: str) -> pl.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(f"https://listado.mercadolibre.com.mx/{articulo.replace(' ', '-')}")

        await page.wait_for_selector("#shipping_highlighted_fulfillment", timeout=2000)
        await page.click("#shipping_highlighted_fulfillment")
        await page.wait_for_selector("li.ui-search-layout__item", timeout=5000)
        items = await page.query_selector_all("li.ui-search-layout__item")

        results = []

        for item in items:
            title = await item.query_selector("h3")
            price = await item.query_selector("span.andes-money-amount__fraction")
            link = await item.query_selector("a")

            title_val = await title.inner_text() if title else ""
            price_val = await price.inner_text() if price else ""
            link_val = await link.get_attribute("href") if link else ""
            fecha_consulta = datetime.now()

            results.append((title_val.strip(), float(price_val.replace(',', '').strip()), link_val, fecha_consulta.__str__()))

        await browser.close()

        # Crea DataFrame con Polars
        df = pl.DataFrame(results, schema=["Titulo", "Precio", "Link", "fecha_consulta"], orient="row")

        return df

# Manejo de errores
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Búsqueda cancelada.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("buscar", buscar)],
        states={
            WAITING_ARTICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_articulo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    # Inicia el bot
    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())