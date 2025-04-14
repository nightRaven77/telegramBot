from scraper import scrape_website
from notifier import sync_send_telegram_notificaction

import schedule
import time

def job():
    url = r"""https://articulo.mercadolibre.com.mx/MLM-2051886252-base-soporte-para-laptop-tableta-portatil-ajustable-plegable-_JM?searchVariation=177696748063"""
    elementos = scrape_website(url, "span", "andes-money-amount__fraction")

    if elementos:
        msj = "El precio es: " + elementos[0]
        sync_send_telegram_notificaction(msj)
    else:
        print("No se encontraron elementos")

schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)