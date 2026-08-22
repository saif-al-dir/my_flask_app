import importlib
from urllib.request import urlopen
from flask import Blueprint, render_template, request, redirect, url_for  # type: ignore[import-not-found]
from app.models import Feed
from app import db

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
            # Parse the downloaded content
            with urlopen(feed.url, timeout=10) as response:
                parsed = importlib.import_module('feedparser').parse(response.read())
            
            # Check if the feed was parsed successfully
            if not parsed.bozo and parsed.entries:
                articles = []
                for entry in parsed.entries[:5]: # Get latest 5 articles
                    summary = entry.get('summary', '')
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': summary[:150] + '...' if len(summary) > 150 else summary
                    })
                
                if feed.category not in categorized_articles:
                    categorized_articles[feed.category] = []
                    
                categorized_articles[feed.category].append({
                    'feed_title': parsed.feed.get('title', 'Unknown Feed'),
                    'articles': articles
                })
        except Exception as e:
            # If a feed fails to load, print an error to the terminal but keep the site running
            print(f"Error fetching {feed.url}: {e}")
            continue

    return render_template('index.html', categorized_articles=categorized_articles)