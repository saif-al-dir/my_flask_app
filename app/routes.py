import importlib
import requests  # type: ignore[import-not-found]
from urllib.request import urlopen
from flask import Blueprint, render_template, request, redirect, url_for  # type: ignore[import-not-found]
from app.models import Feed
from app import db

feedparser = importlib.import_module('feedparser')

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        url = request.form.get('url')
        category = request.form.get('category')
        if url:
            new_feed = Feed(url=url, category=category or "General")
            db.session.add(new_feed)
            db.session.commit()
        return redirect(url_for('main.home'))

    feeds = Feed.query.all()
    categorized_articles = {}

    for feed in feeds:
        try:
            response = requests.get(feed.url, timeout=10)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            
            if not parsed.bozo and parsed.entries:
                articles = []
                for entry in parsed.entries[:5]:
                    summary = entry.get('summary', '')
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': summary[:150] + '...' if len(summary) > 150 else summary
                    })
                
                if feed.category not in categorized_articles:
                    categorized_articles[feed.category] = []
                    
                categorized_articles[feed.category].append({
                    'feed_id': feed.id, # <--- ADDED THIS for the delete button
                    'feed_title': parsed.feed.get('title', 'Unknown Feed'),
                    'articles': articles
                })
        except Exception as e:
            print(f"Error fetching {feed.url}: {e}")
            continue

    return render_template('index.html', categorized_articles=categorized_articles)

# --- NEW DELETE ROUTE ---
@main.route('/delete/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    db.session.delete(feed)
    db.session.commit()
    return redirect(url_for('main.home'))