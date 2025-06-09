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


async def scrape_mercadolibre(articulo: str, page) -> List[Dict]:
    await page.goto(f"https://listado.mercadolibre.com.mx/{articulo.replace(' ', '-')}")
    # Extracción de datos
    return [{
        "titulo": await title.inner_text(),
        "precio": (await price.inner_text()).replace("$", "").replace(",", ""),
        "enlace": await link.get_attribute("href"),
        "sitio": "MercadoLibre"
    } async for title, price, link in zip(
        page.locator("h2.ui-search-item__title").all(),
        page.locator("span.price-tag-amount").all(),
        page.locator("a.ui-search-item__group__element").all()
    )]

async def scrape_amazon(articulo: str, page) -> List[Dict]:
    await page.goto(f"https://www.amazon.com.mx/s?k={articulo.replace(' ', '+')}")
    # Extracción de datos (selectores de Amazon)
    return [{
        "titulo": await title.inner_text(),
        "precio": (await price.inner_text()).split("$")[-1].replace(",", ""),
        "enlace": f"https://www.amazon.com.mx{await link.get_attribute('href')}",
        "sitio": "Amazon"
    } async for title, price, link in zip(
        page.locator("span.a-text-normal").all(),
        page.locator("span.a-price-whole").all(),
        page.locator("a.a-link-normal.s-no-outline").all()
    )]

async def scrape_all_sites(articulo: str) -> pl.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Scraping paralelo
        tasks = []
        async with context.new_page() as page:
            tasks.append(scrape_mercadolibre(articulo, page))
            tasks.append(scrape_amazon(articulo, page))

        results = await asyncio.gather(*tasks)
        await browser.close()

        # Combina resultados y crea DataFrame
        flat_results = [item for sublist in results for item in sublist]
        df = pl.DataFrame(flat_results).with_columns(
            pl.col("precio").cast(pl.Float64),
            pl.lit(datetime.now()).alias("fecha_consulta")
        )

        return df

# Escucha el artículo del usuario
async def recibir_articulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articulo = update.message.text
    await update.message.reply_text(f"🔍 Buscando '{articulo}' en MercadoLibre y Amazon...")

    try:
        df = await scrape_all_sites(articulo)

        if df.is_empty():
            await update.message.reply_text("❌ No hay resultados en ningún sitio.")
            return ConversationHandler.END

        # Genera CSV comparativo
        csv_path = f"comparativo_{articulo[:15]}.csv"
        df.write_csv(csv_path)

        # Envía archivo con análisis rápido
        stats = df.group_by("sitio").agg([
            pl.col("precio").mean().alias("precio_promedio"),
            pl.count().alias("resultados")
        ])

        await update.message.reply_document(
            document=open(csv_path, "rb"),
            caption=f"📊 {len(df)} resultados totales\n{stats.to_pandas().to_markdown()}"
        )

        os.remove(csv_path)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

    return ConversationHandler.END



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