import requests
from bs4 import BeautifulSoup


def scrape_website(url: str, element: str, class_name: str = None):
	try:
		response = requests.get(url)
		response.raise_for_status()

		soup = BeautifulSoup(response.text, 'html.parser')
		if class_name:
			items = soup.find_all(element, class_=class_name)
		else:
			items = soup.find_all(element)
		
		return [item.get_text(strip=True)for item in items]

	except Exception as e:
		print(f"Error en scraping: {e}")
		return []