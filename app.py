from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

NEWS_API_KEY = '1fd07a62200244a1b171dbcdc79ac99f'
NEWS_API_URL = 'https://newsapi.org/v2/everything'
HF_API_KEY = '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'
HF_API_URL = 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn'

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)

def fetch_ai_news():
    params = {
        'q': 'artificial intelligence',
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
    
    # Debugging information
    print(f"Sending request to Hugging Face API with payload: {payload}")
    
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    try:
        response.raise_for_status()
        summary = response.json()[0]['summary_text']
        return summary
    except requests.exceptions.HTTPError as e:
        print(f"HTTPError: {e}")
        print(f"Response content: {response.content}")
        raise

@app.route('/')
def home():
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
            'publishedAt': article['publishedAt']
        })
    return render_template('home.html', articles=summarized_articles)

@app.route('/news')
def news():
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
            'publishedAt': article['publishedAt']
        })
    return render_template('news.html', articles=summarized_articles)

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
    with app.app_context():
        db.create_all()
    app.run(debug=True)
