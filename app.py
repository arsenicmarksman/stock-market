from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests  # For API integration
import feedparser

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Database model for users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.String(200))
    profile_picture = db.Column(db.String(200))
    theme = db.Column(db.String(20), default='light')

# Home route - Displays stock data
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch stock data from Alpha Vantage (Replace with your own API key)
    api_key = 'YOUR_ALPHA_VANTAGE_API_KEY'
    symbol = 'AAPL'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={api_key}'

    response = requests.get(url)
    data = response.json()

    # Parse stock data
    stock_info = []
    if 'Time Series (5min)' in data:
        time_series = data['Time Series (5min)']
        for time, values in time_series.items():
            stock_info.append({
                'time': time,
                'open': values['1. open'],
                'high': values['2. high'],
                'low': values['3. low'],
                'close': values['4. close']
            })

    # Show stock data and user theme
    user = User.query.get(session['user_id'])
    return render_template('home.html', stock_info=stock_info[:10], theme=user.theme)

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')

        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.')

    return render_template('login.html')

@app.route('/stock-data')
def stock_data():
    # Fetch stock data (Replace API key)
    api_key = 'YOUR_ALPHA_VANTAGE_API_KEY'
    symbol = 'AAPL'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={api_key}'
    response = requests.get(url).json()

    # Parse data
    times = []
    prices = []
    if 'Time Series (5min)' in response:
        time_series = response['Time Series (5min)']
        for time, values in time_series.items():
            times.append(time)
            prices.append(float(values['4. close']))

    return {'times': times[::-1], 'prices': prices[::-1]}  # Reverse order for timeline


@app.route('/news-feed')
def news_feed():
    feeds = [
        'http://feeds.bbci.co.uk/news/rss.xml',
        'http://rss.cnn.com/rss/cnn_topstories.rss',
        'http://feeds.foxnews.com/foxnews/latest'
    ]

    news = []
    for feed in feeds:
        parsed_feed = feedparser.parse(feed)
        for entry in parsed_feed.entries[:5]:  # Get top 5 articles
            news.append({'title': entry.title, 'link': entry.link})

    return news

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.bio = request.form['bio']
        if 'profile_picture' in request.files:
            picture = request.files['profile_picture']
            if picture.filename != '':
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], picture.filename)
                picture.save(filepath)
                user.profile_picture = filepath
        db.session.commit()
        flash('Profile updated successfully!')

    return render_template('profile.html', user=user)

# Settings route
@app.route('/settings', methods=['POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    theme = request.form['theme']
    user = User.query.get(session['user_id'])
    user.theme = theme
    db.session.commit()
    flash('Settings updated!')
    return redirect(url_for('home'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!')
    return redirect(url_for('login'))

# Initialize database before the first request
@app.before_request
def create_tables():
    db.create_all()

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
