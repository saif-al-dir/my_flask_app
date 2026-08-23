import importlib
import xml.etree.ElementTree as ET
import requests  # type: ignore[import-not-found]
from urllib.request import urlopen
from urllib.parse import urlparse
from bs4 import BeautifulSoup  # type: ignore[import-not-found]
from flask import Blueprint, Response, flash, render_template, request, redirect, url_for  # type: ignore[import-not-found]
from app.models import Article, Feed
from datetime import datetime, timedelta
from app import db

feedparser = importlib.import_module('feedparser')

main = Blueprint('main', __name__)

def fetch_and_store_articles():
    """Fetches new articles from feeds and deletes articles older than 2 days."""
    # 1. Delete articles older than 2 days
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    Article.query.filter(Article.published_at < two_days_ago).delete()
    db.session.commit()

    # 2. Fetch new articles if not fetched in the last 1 hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    feeds = Feed.query.filter(Feed.last_fetched < one_hour_ago).all()

    for feed in feeds:
        try:
            response = requests.get(feed.url, timeout=10)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            
            if not parsed.bozo and parsed.entries:
                feed.title = parsed.feed.get('title', 'Unknown Feed')
                
                for entry in parsed.entries[:10]: # Store latest 10 per feed
                    # Check if article already exists
                    existing = Article.query.filter_by(link=entry.link).first()
                    if not existing:
                        summary = entry.get('summary', '')
                        # Try to parse publish date, fallback to now
                        pub_date = datetime.utcnow()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            try:
                                pub_date = datetime(*entry.published_parsed[:6])
                            except:
                                pass

                        new_article = Article(
                            feed_id=feed.id,
                            title=entry.title,
                            link=entry.link,
                            summary=summary[:250],
                            published_at=pub_date
                        )
                        db.session.add(new_article)
                
                feed.last_fetched = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            print(f"Error fetching {feed.url}: {e}")
            continue

@main.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        url = request.form.get('url')
        category = request.form.get('category')
        if url:
            new_feed = Feed(url=url, category=category or "General")
            db.session.add(new_feed)
            db.session.commit()
            # Fetch immediately for this new feed
            fetch_and_store_articles()
        return redirect(url_for('main.home'))

    # Update feeds and purge old articles
    fetch_and_store_articles()

    # Get articles grouped by category
    feeds = Feed.query.all()
    categorized_articles = {}

    for feed in feeds:
        articles = Article.query.filter_by(feed_id=feed.id).order_by(Article.published_at.desc()).all()
        if articles:
            if feed.category not in categorized_articles:
                categorized_articles[feed.category] = []
                
            categorized_articles[feed.category].append({
                'feed_id': feed.id,
                'feed_title': feed.title,
                'articles': articles
            })

    return render_template('index.html', categorized_articles=categorized_articles)

@main.route('/delete/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    # Delete articles belonging to this feed first
    Article.query.filter_by(feed_id=feed_id).delete()
    db.session.delete(feed)
    db.session.commit()
    return redirect(url_for('main.home'))

@main.route('/read')
def read_article():
    article_url = request.args.get('url')
    if not article_url:
        return redirect(url_for('main.home'))

    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('title').text if soup.find('title') else "No Title"
        
        # Extract first available image
        image_url = None
        img_tag = soup.find('img')
        if img_tag and 'src' in img_tag.attrs:
            img_src = img_tag['src']
            # Handle relative URLs
            if img_src.startswith('/'):
                parsed_uri = urlparse(article_url)
                img_src = f"{parsed_uri.scheme}://{parsed_uri.netloc}{img_src}"
            image_url = img_src

        # Extract text
        paragraphs = soup.find_all('p')
        content = '\n\n'.join([p.get_text() for p in paragraphs if len(p.get_text()) > 50])

        return render_template('article.html', title=title, content=content, image_url=image_url, original_url=article_url)
        
    except Exception as e:
        return f"Error reading article: {e}", 500

# --- OPML IMPORT / EXPORT ---
@main.route('/export_opml')
def export_opml():
    feeds = Feed.query.all()
    root = ET.Element('opml', version='1.0')
    head = ET.SubElement(root, 'head')
    ET.SubElement(head, 'title').text = 'My RSS Feeds'
    body = ET.SubElement(root, 'body')
    
    # Group by categories
    categories = {}
    for feed in feeds:
        if feed.category not in categories:
            categories[feed.category] = []
        categories[feed.category].append(feed)
        
    for cat_name, cat_feeds in categories.items():
        cat_outline = ET.SubElement(body, 'outline', text=cat_name, title=cat_name)
        for feed in cat_feeds:
            ET.SubElement(cat_outline, 'outline', text=feed.title, title=feed.title, type='rss', xmlUrl=feed.url)
            
    xml_str = ET.tostring(root, encoding='unicode')
    return Response(xml_str, mimetype='text/xml', headers={'Content-Disposition': 'attachment; filename=rss_feeds.opml'})

@main.route('/import_opml', methods=['POST'])
def import_opml():
    file = request.files.get('opml_file')
    if file:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            # Find all outline elements that have an xmlUrl attribute
            for outline in root.findall('.//outline'):
                xml_url = outline.get('xmlUrl')
                if xml_url:
                    title = outline.get('text', 'Imported Feed')
                    category = outline.get('text', 'Imported') # Parent outline is usually category
                    # If it's a child, get parent category
                    parent = outline.getparent() if hasattr(outline, 'getparent') else None
                    if parent is not None and parent.get('text'):
                        category = parent.get('text')
                    
                    # Add to DB if not exists
                    exists = Feed.query.filter_by(url=xml_url).first()
                    if not exists:
                        new_feed = Feed(url=xml_url, category=category, title=title)
                        db.session.add(new_feed)
            db.session.commit()
            fetch_and_store_articles()
        except Exception as e:
            flash(f"Error importing OPML: {e}")
    return redirect(url_for('main.home'))