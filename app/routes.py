import importlib
import requests  # type: ignore[import-not-found]
from urllib.request import urlopen
from bs4 import BeautifulSoup  # type: ignore[import-not-found]
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
                    'feed_id': feed.id,
                    'feed_title': parsed.feed.get('title', 'Unknown Feed'),
                    'articles': articles
                })
        except Exception as e:
            print(f"Error fetching {feed.url}: {e}")
            continue

    return render_template('index.html', categorized_articles=categorized_articles)

@main.route('/delete/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    db.session.delete(feed)
    db.session.commit()
    return redirect(url_for('main.home'))

# --- NEW ROUTE TO READ ARTICLES ---
@main.route('/read')
def read_article():
    # Get the URL from the link (?url=...)
    article_url = request.args.get('url')
    if not article_url:
        return redirect(url_for('main.home'))

    try:
        # Fetch the article webpage
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML to extract the text
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find the main title
        title = soup.find('title').text if soup.find('title') else "No Title"
        
        # Try to find the main text (extracting all <p> tags usually works best for articles)
        paragraphs = soup.find_all('p')
        content = '\n\n'.join([p.get_text() for p in paragraphs if len(p.get_text()) > 50]) # Ignore tiny paragraphs
        
        if not content:
            content = "Could not extract readable text from this article. Please visit the original site."

        return render_template('article.html', title=title, content=content, original_url=article_url)
        
    except Exception as e:
        return f"Error reading article: {e}", 500