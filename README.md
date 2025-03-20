# CryptoBot Documentation

## Description
CryptoBot is a Python application that fetches cryptocurrency data from the CoinMarketCap API, stores it in an SQLite database, generates analysis reports, and sends structured updates to Telegram.

## Requirements
- Python 3.8 or higher
- CoinMarketCap account to obtain an API key
- Telegram bot to receive notifications
- Installed dependencies:
  ```bash
  pip install requests pandas logging python-dotenv sqlite3 matplotlib
  ```

## Configuration
The bot uses a `.env` file to store environment variables:
```
COINMARKETCAP_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
FETCH_INTERVAL=3600  # Interval in seconds (default: 1 hour)
TOP_N_COINS=100  # Number of cryptocurrencies to fetch
DATA_DIR=data  # Directory to store data
```

## Features
### 1. Database Initialization
```python
def initialize_database()
```
Creates the `crypto_data` and `analysis_results` tables in SQLite if they do not exist.

### 2. Data Retrieval
```python
def get_crypto_data()
```
Queries the CoinMarketCap API and returns the most important cryptocurrency data.

### 3. Data Storage
```python
def save_data_to_db(data)
```
Stores the retrieved data in the SQLite database.

```python
def save_raw_data(data)
```
Saves raw data in JSON format in the specified directory.

### 4. Data Analysis
```python
def analyze_market_data(df)
```
Performs calculations on:
- Top gainers and losers in 24h.
- Assets with the highest liquidity.
- Volatility.
- Market dominance.

The results are stored in the database.

### 5. Report Generation
```python
def generate_charts(df, analysis_results)
```
Creates visual charts of the market and saves them as images.

```python
def format_market_overview(df)
```
Generates a general market summary.

```python
def format_top_coins(df, top_n=5)
```
Lists the most important cryptocurrencies by market capitalization.

```python
def format_detailed_analysis(analysis_results)
```
Displays details of trends and significant movements.

### 6. Sending Data to Telegram
```python
def send_message_to_telegram(message, photo_path=None)
```
Sends structured messages and charts to Telegram.

### 7. Continuous Monitoring
```python
def process_crypto_data()
```
Executes the entire workflow:
1. Retrieves data.
2. Stores it in the database.
3. Performs analysis.
4. Generates reports.
5. Sends alerts to Telegram.

### 8. Running the Bot
```python
def main()
```
Runs the bot in an infinite loop with the configured interval.

## Usage
Run the script with:
```bash
python cryptoBot1.py
```
To stop it, use `CTRL + C`.

