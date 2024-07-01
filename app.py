from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///notes.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

NEWS_API_KEY = os.getenv('NEWS_API_KEY', '1fd07a62200244a1b171dbcdc79ac99f')
NEWS_API_URL = 'https://newsapi.org/v2/everything'
HF_API_KEY = os.getenv('HF_API_KEY', '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')
HF_API_URL = 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn'

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)

class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    preferences = db.Column(db.String(200), nullable=False)

def fetch_ai_news(query='artificial intelligence'):
    params = {
        'q': query,
        'apiKey': NEWS_API_KEY,
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': 10
    }
    try:
        response = requests.get(NEWS_API_URL, params=params)
        response.raise_for_status()
        news_data = response.json()
        return news_data['articles']
    except requests.RequestException as e:
        flash(f"An error occurred while fetching news: {e}", 'danger')
        return []

def summarize_article(text):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": text[:1024], "parameters": {"max_length": 130, "min_length": 30, "do_sample": False}}
    
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    try:
        response.raise_for_status()
        summary = response.json()[0]['summary_text']
        return summary
    except requests.exceptions.HTTPError as e:
        flash(f"An error occurred while summarizing article: {e}", 'danger')
        return ""

@app.route('/', methods=['GET', 'POST'])
def home():
    user_id = 1  # Assuming a single user for simplicity

    if request.method == 'POST':
        preferences = request.form.getlist('preferences')
        preferences_str = ','.join(preferences)
        user_pref = UserPreference.query.filter_by(user_id=user_id).first()
        if user_pref:
            user_pref.preferences = preferences_str
        else:
            new_pref = UserPreference(user_id=user_id, preferences=preferences_str)
            db.session.add(new_pref)
        db.session.commit()

    user_pref = UserPreference.query.filter_by(user_id=user_id).first()
    if user_pref:
        preferences = user_pref.preferences.split(',')
        articles = []
        for pref in preferences:
            articles += fetch_ai_news(pref)
    else:
        articles = fetch_ai_news()
    summarized_articles = []
    for article in articles:
        description = article.get('description', '')
        if not description:
            continue
        summary = summarize_article(description)
        summarized_articles.append({
            'title': article['title'],
            'url': article['url'],
            'summary': summary,
            'publishedAt': article['publishedAt'],
            'urlToImage': article.get('urlToImage', '')
        })
    return render_template('home.html', articles=summarized_articles, user_pref=user_pref)

@app.route('/overview')
def overview():
    articles = fetch_ai_news()
    key_points = [summarize_article(article['description']) for article in articles if article.get('description', '')]
    return render_template('overview.html', key_points=key_points)

@app.route('/note', methods=['GET', 'POST'])
def note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_note = Note(title=title, content=content)
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('notes'))
    return render_template('note.html')

@app.route('/notes')
def notes():
    notes = Note.query.all()
    return render_template('notes.html', notes=notes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
