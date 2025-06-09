from sqlite3 import Row
from playwright.sync_api import sync_playwright
import polars as pl


def scrape_website():
	
	playwright = sync_playwright().start()
	browser = playwright.chromium.launch(headless=False)
	page = browser.new_page()
	query="tarja de acero 80_45_22"
	url = f"https://listado.mercadolibre.com.mx/{query.replace(' ' , '-')}"	

	page.goto(url)

	try:
		page.wait_for_selector('text="Agregar ubicación"', timeout=360)
		page.click('text="Más tarde"')
		
	except:
		pass
	page.wait_for_selector("#shipping_highlighted_fulfillment")
	page.click("#shipping_highlighted_fulfillment")

	page.wait_for_selector("li.ui-search-layout__item")
	items = page.query_selector_all("li.ui-search-layout__item")

	products = []
	for item in items:
		title = item.query_selector('h3')
		price = item.query_selector('span.andes-money-amount')

		link = item.query_selector('a.poly-component__title')

		title_val = title.inner_text()
		
		price_val = price.inner_text().replace("\n","").strip()
		link_val = link.get_attribute('href')

		products.append((title_val, price_val, link_val))
		
	browser.close()
	playwright.stop()

	df  = pl.DataFrame(products, schema=["Titulo", "Precio", "Link"],orient="row")
	df.write_csv("./output/products.csv")
	