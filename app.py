from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

app = Flask(__name__)

def get_kvant_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Fetch 1 year of data for calculations
        df = stock.history(period="1y")
        
        if df.empty: return None
        
        # --- QUANTITATIVE ENGINE ---
        
        # 1. Trend Factors
        df['SMA_50'] = df.ta.sma(length=50)
        df['SMA_200'] = df.ta.sma(length=200)
        
        # 2. Momentum Factors
        df['RSI'] = df.ta.rsi(length=14)
        df['MACD'] = df.ta.macd(fast=12, slow=26, signal=9)['MACD_12_26_9']
        
        # 3. Volatility Factors (Risk)
        df['ATR'] = df.ta.atr(length=14)
        
        # Get latest data point
        curr = df.iloc[-1]
        
        # --- THE "ALPHA SCORE" ALGORITHM (0-100) ---
        score = 50  # Start neutral
        
        # Trend Component (30 pts)
        if curr['Close'] > curr['SMA_50']: score += 15
        if curr['SMA_50'] > curr['SMA_200']: score += 15
        
        # Momentum Component (40 pts)
        if 40 < curr['RSI'] < 70: score += 10       # Healthy zone
        if curr['RSI'] < 30: score += 20            # Oversold bounce potential
        if curr['MACD'] > 0: score += 10            # Positive momentum
        
        # Risk Penalty
        # If volatility is extreme (ATR > 5% of price), reduce score
        if (curr['ATR'] / curr['Close']) > 0.05: score -= 10

        # Cap score 0-100
        score = max(0, min(100, score))
        
        # Determine Verdict
        if score >= 80: verdict = "STRONG BUY"
        elif score >= 60: verdict = "BUY"
        elif score <= 20: verdict = "STRONG SELL"
        elif score <= 40: verdict = "SELL"
        else: verdict = "HOLD"

        # --- FUNDAMENTALS ---
        info = stock.info
        
        return {
            'symbol': ticker.upper(),
            'price': round(curr['Close'], 2),
            'score': int(score),
            'verdict': verdict,
            'rsi': round(curr['RSI'], 2),
            'volatility': round((curr['ATR'] / curr['Close']) * 100, 2),
            'market_cap': info.get('marketCap', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            'sector': info.get('sector', 'Unknown'),
            'company_name': info.get('longName', ticker.upper())
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    data = None
    search_ticker = "SPY" # Default
    
    if request.method == 'POST':
        search_ticker = request.form.get('ticker', 'SPY').upper()
    
    data = get_kvant_data(search_ticker)
    
    return render_template('index.html', data=data, ticker=search_ticker)

if __name__ == '__main__':
    app.run(debug=True)