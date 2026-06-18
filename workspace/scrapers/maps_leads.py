import time
import random

def scrape_maps(query="peluquerias madrid"):
    print(f"Scraping Google Maps for: {query}")
    time.sleep(2)
    # Simulated leads
    leads = [
        {"name": "Peluquería Estilo", "phone": "+34 912 345 678", "website": None},
        {"name": "Corte y Color", "phone": "+34 600 000 000", "website": None},
        {"name": "Barber Shop Elite", "phone": "+34 911 111 111", "website": "http://barber.com"}
    ]

    potential = [l for l in leads if not l['website']]
    print(f"Found {len(potential)} businesses without websites.")
    for p in potential:
        print(f"LEAD FOUND: {p['name']} - {p['phone']}")

if __name__ == "__main__":
    scrape_maps()
