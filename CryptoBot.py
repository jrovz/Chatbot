import requests
import time

# Configuración
COINMARKETCAP_API_KEY = "TU_CMC_API_KEY"
TELEGRAM_BOT_TOKEN = "TU_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"
FETCH_INTERVAL = 3600  # 1 hora en segundos

# URL de CoinMarketCap
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
HEADERS = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}

# URL de Telegram
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def get_crypto_data():
    """Obtiene los datos de las 100 principales criptomonedas."""
    params = {"limit": 5, "convert": "USD"}  # Puedes cambiar el límite a 100
    response = requests.get(CMC_URL, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        return None

def format_crypto_message(data):
    """Formatea los datos en un mensaje estructurado."""
    message = "📊 *Top 5 Criptomonedas*\n\n"
    for coin in data:
        name = coin["name"]
        symbol = coin["symbol"]
        price = coin["quote"]["USD"]["price"]
        change_24h = coin["quote"]["USD"]["percent_change_24h"]
        volume = coin["quote"]["USD"]["volume_24h"]
        
        message += (f"💰 *{name} ({symbol})*\n"
                    f"   - Precio: ${price:,.2f}\n"
                    f"   - Cambio 24h: {change_24h:.2f}%\n"
                    f"   - Volumen: ${volume:,.2f}\n\n")
    return message

def send_message_to_telegram(message):
    """Envía el mensaje a Telegram."""
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(TELEGRAM_URL, json=payload)

def main():
    """Ejecuta el bot en un bucle cada hora."""
    while True:
        data = get_crypto_data()
        if data:
            message = format_crypto_message(data)
            send_message_to_telegram(message)
        else:
            send_message_to_telegram("⚠️ Error obteniendo datos de CoinMarketCap.")
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    main()
