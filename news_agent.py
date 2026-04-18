import os
import json
import feedparser
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Konfiguration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
# RSS-Feeds von Fachmedien
RSS_FEEDS = {
    "Recharge News": "[rechargenews.com](https://www.rechargenews.com/rss)",
    "PV Magazine Global": "[pv-magazine.com](https://www.pv-magazine.com/feed/)",
    "PV Magazine Germany": "[pv-magazine.de](https://www.pv-magazine.de/feed/)",
    "Windpower Monthly": "[windpowermonthly.com](https://www.windpowermonthly.com/rss)",
    "Energy Storage News": "[energy-storage.news](https://www.energy-storage.news/feed/)",
    "Renews.biz": "[renews.biz](https://renews.biz/feed/)",
    "Electrek": "[electrek.co](https://electrek.co/feed/)",
    "CleanTechnica": "[cleantechnica.com](https://cleantechnica.com/feed/)",
}
# Google News RSS für länderspezifische Suche
GOOGLE_NEWS_COUNTRIES = {
    "Germany": "Deutschland erneuerbare Energien Windpark Solarpark",
    "Spain": "Spain renewable energy wind solar",
    "Netherlands": "Netherlands offshore wind solar energy",
    "Denmark": "Denmark wind energy Vestas Orsted",
    "Poland": "Poland renewable energy wind solar",
    "France": "France renewable energy offshore wind",
    "Italy": "Italy solar wind energy project",
    "UK": "UK offshore wind renewable energy",
    "USA": "USA renewable energy wind solar project",
}
def fetch_rss_news():
    """Holt News von Fachmedien RSS-Feeds"""
    yesterday = datetime.now() - timedelta(days=1)
    all_news = []
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                # Datum prüfen wenn vorhanden
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if pub_date < yesterday:
                        continue
                
                all_news.append({
                    'source': source,
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', '')[:500],
                    'url': entry.get('link', ''),
                    'date': pub_date.strftime('%Y-%m-%d') if pub_date else 'recent'
                })
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    
    return all_news
def fetch_google_news():
    """Holt länderspezifische News via Google News RSS"""
    all_news = []
    
    for country, query in GOOGLE_NEWS_COUNTRIES.items():
        try:
            # Google News RSS URL
            url = f"[news.google.com](https://news.google.com/rss/search?q={query.replace()' ', '+')}+when:1d&hl=en"
            
            if country == "Germany":
                url = f"[news.google.com](https://news.google.com/rss/search?q={query.replace()' ', '+')}+when:1d&hl=de&gl=DE"
            
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:3]:
                all_news.append({
                    'source': f"Google News ({country})",
                    'country': country,
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', '')[:300],
                    'url': entry.get('link', ''),
                })
        except Exception as e:
            print(f"Error fetching Google News for {country}: {e}")
    
    return all_news
def summarize_news(rss_news, country_news):
    """Erstellt strukturierte Zusammenfassung mit OpenAI"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    combined_news = {
        "trade_publications": rss_news,
        "country_specific": country_news
    }
    
    news_text = json.dumps(combined_news, indent=2, ensure_ascii=False)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Du bist ein Analyst für erneuerbare Energien und erstellst einen täglichen Briefing für einen COO.
Struktur:
1. **Top Stories** - Die 3-5 wichtigsten Meldungen des Tages
2. **Deutschland** - Alle relevanten deutschen News (ausführlich)
3. **Europa** - Wichtige Entwicklungen in anderen europäischen Ländern
4. **International** - USA und globale News
Fokus auf:
- Projektankündigungen (mit MW/GW Angaben)
- Turbinen-Bestellungen (Vestas, Siemens Gamesa, Nordex, etc.)
- Ausschreibungsergebnisse
- Politische Entscheidungen
- Große PPAs und Netzanschlüsse
Stil: Kurz, präzise, Bullet Points. Keine Floskeln."""},
            {"role": "user", "content": f"Erstelle das heutige Briefing basierend auf diesen News:\n\n{news_text}"}
        ],
        max_tokens=2500
    )
    
    return response.choices[0].message.content
def send_email(summary):
    """Sendet E-Mail mit Zusammenfassung"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Renewable Energy Briefing - {datetime.now().strftime('%d.%m.%Y')}"
    
    body = f"""Guten Morgen Malte,
{summary}
---
Quellen: Recharge News, PV Magazine, Windpower Monthly, Energy Storage News, Renews.biz, Google News
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("Email sent successfully!")
def main():
    print("Fetching trade publication news...")
    rss_news = fetch_rss_news()
    print(f"Found {len(rss_news)} articles from trade publications")
    
    print("Fetching country-specific news...")
    country_news = fetch_google_news()
    print(f"Found {len(country_news)} country-specific articles")
    
    print("Creating summary...")
    summary = summarize_news(rss_news, country_news)
    
    print("Sending email...")
    send_email(summary)
    
    print("Done!")
if __name__ == "__main__":
    main()