import requests
import time
import pandas as pd
import logging
import os
from datetime import datetime
import json
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import sqlite3

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crypto_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env file
load_dotenv()

# Configuración desde variables de entorno
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FETCH_INTERVAL = 60  # Reducido a 60 segundos para pruebas
TOP_N_COINS = int(os.getenv("TOP_N_COINS", "5"))  # Reducido a Top 5 para pruebas
DATA_DIR = os.getenv("DATA_DIR", "data")

# Asegurar que el directorio de datos existe
os.makedirs(DATA_DIR, exist_ok=True)

# URLs de API
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
HEADERS = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def get_crypto_data():
    """Obtiene los datos de las principales criptomonedas con manejo de errores."""
    try:
        params = {"limit": TOP_N_COINS, "convert": "USD"}
        response = requests.get(CMC_URL, headers=HEADERS, params=params, timeout=30)
        print("Respuesta de CoinMarketCap:", response.status_code, response.text[:500])  # Ver los primeros 500 caracteres
        if response.status_code == 200:
            data = response.json()["data"]
            logger.info(f"Datos obtenidos correctamente: {len(data)} monedas")
            return data
        else:
            logger.error(f"Error en la API: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error de conexión: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return None

def send_message_to_telegram(message):
    """Envía el mensaje a Telegram y lo imprime en consola para prueba."""
    try:
        print("Mensaje a enviar a Telegram:\n", message)  # Mostrar en consola antes de enviarlo
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        print("Respuesta de Telegram:", response.status_code, response.text)  # Verificar respuesta de Telegram
        logger.info("Mensaje enviado a Telegram correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
        return False

def main():
    """Función principal para probar en local."""
    logger.info("Iniciando prueba de CryptoBot en local...")
    data = get_crypto_data()
    if data:
        message = "\n".join([f"{coin['name']} ({coin['symbol']}): ${coin['quote']['USD']['price']:.2f}" for coin in data])
        send_message_to_telegram(message)
    else:
        send_message_to_telegram("⚠️ No se pudieron obtener datos de CoinMarketCap.")

if __name__ == "__main__":
    main()
