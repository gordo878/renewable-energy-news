import os
import json
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Konfiguration
# die 10 wichtigsten Länder
COUNTRIES = ["Germany", "Spain", "France", "Netherlands", "Hungary", "Greece", "Poland", "Italy", "Chile", "Dominican Republic"]
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

def fetch_news():
    """Holt News der letzten 24h mit Fokus auf Projekte & Markt"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    all_news = []
    
    for country in COUNTRIES:
        # Spezielle Suchbegriffe je nach Land
        if country == "Germany":
            # Deutsche & englische Quellen für Deutschland
            queries = [
                '(Deutschland OR Germany) AND (Ausschreibung OR tender OR "wind farm" OR "solar park" OR Windpark OR Solarpark OR BNetzA OR "Bundesnetzagentur")',
                '(Vestas OR Siemens Gamesa OR Nordex OR Enercon OR GE OR Envision) AND (Germany OR Deutschland) AND (order OR Auftrag OR MW)',
                '(Germany) AND (BESS OR "power purchase agreement" OR PPA OR "grid connection" OR Netzanschluss OR Batteriespeicher)'
            ]
            articles_collected = []
            
            for query in queries:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': query,
                    'from': yesterday,
                    'sortBy': 'relevance',
                    'language': 'de',
                    'pageSize': 3,
                    'apiKey': NEWS_API_KEY
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    articles_collected.extend(response.json().get('articles', []))
            
            # Auch englische Quellen checken
            params['language'] = 'en'
            params['q'] = '(Germany) AND ("wind turbine order" OR "solar project" OR "renewable tender" OR "FiT" OR "auction results")'
            response = requests.get(url, params=params)
            if response.status_code == 200:
                articles_collected.extend(response.json().get('articles', []))
            
            # Beste 5 auswählen
            articles = articles_collected[:5]
            
        else:
            # Andere Länder - Fokus auf große Projekte & Deals
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'("{country}") AND ("wind farm" OR "solar park" OR "GW" OR "MW" OR "turbine order" OR "Vestas" OR "Siemens Gamesa" OR "tender" OR "auction" OR "power purchase" OR "renewable project" OR "battery storage project") NOT (stock OR share)',
                'from': yesterday,
                'sortBy': 'relevance',
                'language': 'en',
                'pageSize': 5,
                'apiKey': NEWS_API_KEY
            }
            response = requests.get(url, params=params)
            articles = response.json().get('articles', [])[:5] if response.status_code == 200 else []
        
        # Artikel verarbeiten
        for article in articles:
            if article['title'] and article['url']:  # Nur vollständige Artikel
                all_news.append({
                    'country': country,
                    'title': article['title'],
                    'description': article.get('description', ''),
                    'url': article['url'],
                    'source': article.get('source', {}).get('name', '')
                })
    
    return all_news

def summarize_news(news_data):
    """Erstellt strukturierte Zusammenfassung mit OpenAI"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    news_text = json.dumps(news_data, indent=2)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are a renewable energy market analyst for a COO. 
            Focus on: 1) New project announcements with MW/GW sizes
            2) Turbine/equipment orders and suppliers
            3) Tender results and upcoming auctions  
            4) Policy changes affecting renewable markets
            5) Major grid connections or PPAs
            
            Structure: Start with Germany (detailed), then other countries (brief).
            Use bullet points. Include MW/GW numbers when mentioned.
            Be concise but include key commercial details."""},
            {"role": "user", "content": f"Summarize these news, Germany first and detailed:\n\n{news_text}"}
        ],
        max_tokens=2000
    )
    
    return response.choices[0].message.content

def send_email(summary):
    """Sendet E-Mail mit Zusammenfassung"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Renewable Energy News - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"""
Good morning Malte,

Here's your daily renewable energy briefing:

{summary}

Best regards,
Your News Agent
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Gmail SMTP
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("Email sent successfully!")

def main():
    print("Fetching news...")
    news = fetch_news()
    
    print("Creating summary...")
    summary = summarize_news(news)
    
    print("Sending email...")
    send_email(summary)
    
    print("Done!")

if __name__ == "__main__":
    main()
