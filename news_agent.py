import os
import json
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Konfiguration
COUNTRIES = ["Germany", "Spain", "France", "Netherlands", "Denmark", "UK", "Poland", "Italy", "USA"]
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

def fetch_news():
    """Holt News der letzten 24h"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    all_news = []
    for country in COUNTRIES:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f'renewable energy OR wind power OR solar energy OR battery storage "{country}"',
            'from': yesterday,
            'sortBy': 'relevance',
            'language': 'en',
            'apiKey': NEWS_API_KEY
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            articles = response.json().get('articles', [])[:3]  # Top 3 pro Land
            for article in articles:
                all_news.append({
                    'country': country,
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url']
                })
    
    return all_news

def summarize_news(news_data):
    """Erstellt Zusammenfassung mit OpenAI"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    news_text = json.dumps(news_data, indent=2)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a renewable energy analyst. Create a concise summary in English."},
            {"role": "user", "content": f"Summarize these renewable energy news by country. Be brief and focus on key developments:\n\n{news_text}"}
        ],
        max_tokens=1500
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
