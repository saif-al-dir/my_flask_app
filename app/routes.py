import importlib
import xml.etree.ElementTree as ET
import requests  # type: ignore[import-not-found]
from urllib.parse import urlparse
from bs4 import BeautifulSoup  # type: ignore[import-not-found]
from flask import Blueprint, Response, flash, render_template, request, redirect, url_for  # type: ignore[import-not-found]
from app.models import Article, Feed
from datetime import datetime, timedelta, timezone
from app import db

feedparser = importlib.import_module('feedparser')

main = Blueprint('main', __name__)

def fetch_and_store_articles():
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    Article.query.filter(Article.published_at < two_days_ago).delete()
    db.session.commit()

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    feeds = Feed.query.filter(Feed.last_fetched < one_hour_ago).all()

    for feed in feeds:
        try:
            response = requests.get(feed.url, timeout=10)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            
            if not parsed.bozo and parsed.entries:
                feed.title = parsed.feed.get('title', 'Unknown Feed')
                
                for entry in parsed.entries[:10]:
                    existing = Article.query.filter_by(link=entry.link).first()
                    if not existing:
                        summary = entry.get('summary', '')
                        pub_date = datetime.now(timezone.utc)
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            try:
                                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                            except:
                                pass

                        # --- NEW: Extract Image ---
                        img_url = None
                        # 1. Check media_content
                        if hasattr(entry, 'media_content') and entry.media_content:
                            img_url = entry.media_content[0].get('url')
                        # 2. Check media_thumbnail
                        elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                            img_url = entry.media_thumbnail[0].get('url')
                        # 3. Check enclosures
                        elif hasattr(entry, 'enclosures') and entry.enclosures:
                            for enc in entry.enclosures:
                                if enc.get('type', '').startswith('image'):
                                    img_url = enc.get('href')
                                    break
                        # 4. Parse HTML summary for an img tag
                        if not img_url and summary:
                            soup = BeautifulSoup(summary, 'html.parser')
                            img_tag = soup.find('img')
                            if img_tag and 'src' in img_tag.attrs:
                                img_url = img_tag['src']
                                if img_url.startswith('/'):
                                    parsed_uri = urlparse(feed.url)
                                    img_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}{img_url}"

                        new_article = Article(
                            feed_id=feed.id,
                            title=entry.title,
                            link=entry.link,
                            summary=summary[:250],
                            image_url=img_url, # Save image URL
                            published_at=pub_date
                        )
                        db.session.add(new_article)
                
                feed.last_fetched = datetime.now(timezone.utc)
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
            fetch_and_store_articles()
        return redirect(url_for('main.home'))

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

@main.route('/refresh')
def refresh_feeds():
    fetch_and_store_articles()
    return redirect(url_for('main.home'))

@main.route('/delete/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    Article.query.filter_by(feed_id=feed_id).delete()
    db.session.delete(feed)
    db.session.commit()
    return redirect(url_for('main.home'))

@main.route('/read')
def read_article():
    article_url = request.args.get('url')
    if not article_url:
        return redirect(url_for('main.home'))

    # --- NEW: Mark as Read in Database ---
    article = Article.query.filter_by(link=article_url).first()
    if article:
        article.is_read = True
        db.session.commit()

    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('title').text if soup.find('title') else "No Title"
        
        image_url = None
        img_tag = soup.find('img')
        if img_tag and 'src' in img_tag.attrs:
            img_src = img_tag['src']
            if img_src.startswith('/'):
                parsed_uri = urlparse(article_url)
                img_src = f"{parsed_uri.scheme}://{parsed_uri.netloc}{img_src}"
            image_url = img_src

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
            for outline in root.findall('.//outline'):
                xml_url = outline.get('xmlUrl')
                if xml_url:
                    title = outline.get('text', 'Imported Feed')
                    category = outline.get('text', 'Imported') 
                    parent = outline.getparent() if hasattr(outline, 'getparent') else None
                    if parent is not None and parent.get('text'):
                        category = parent.get('text')
                    
                    exists = Feed.query.filter_by(url=xml_url).first()
                    if not exists:
                        new_feed = Feed(url=xml_url, category=category, title=title)
                        db.session.add(new_feed)
            db.session.commit()
            fetch_and_store_articles()
        except Exception as e:
            flash(f"Error importing OPML: {e}")
    return redirect(url_for('main.home'))

@main.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now(timezone.utc).year
    }