from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__)

# --- HELPER FUNCTIONS FOR LIGHTWEIGHT MATH ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

# --- MAIN LOGIC ---
def get_kvant_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty: return None
        
        # 1. Trend Factors (Simple Moving Averages)
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # 2. Momentum Factors (RSI & MACD)
        df['RSI'] = calculate_rsi(df['Close'])
        df['MACD'], df['MACD_SIGNAL'] = calculate_macd(df['Close'])
        
        # 3. Volatility (ATR)
        df['ATR'] = calculate_atr(df)
        
        # Get latest data point
        curr = df.iloc[-1]
        
        # --- THE "ALPHA SCORE" ALGORITHM (0-100) ---
        score = 50
        
        # Trend (30 pts)
        if curr['Close'] > curr['SMA_50']: score += 15
        if curr['SMA_50'] > curr['SMA_200']: score += 15
        
        # Momentum (40 pts)
        if 40 < curr['RSI'] < 70: score += 10
        if curr['RSI'] < 30: score += 20
        if curr['MACD'] > 0: score += 10
        
        # Risk Penalty
        if (curr['ATR'] / curr['Close']) > 0.05: score -= 10

        score = max(0, min(100, score))
        
        if score >= 80: verdict = "STRONG BUY"
        elif score >= 60: verdict = "BUY"
        elif score <= 20: verdict = "STRONG SELL"
        elif score <= 40: verdict = "SELL"
        else: verdict = "HOLD"

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
    search_ticker = "SPY"
    if request.method == 'POST':
        search_ticker = request.form.get('ticker', 'SPY').upper()
    
    data = get_kvant_data(search_ticker)
    return render_template('index.html', data=data, ticker=search_ticker)

if __name__ == '__main__':
    app.run(debug=True)
