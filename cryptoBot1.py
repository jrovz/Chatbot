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
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "3600"))  # 1 hora por defecto
TOP_N_COINS = int(os.getenv("TOP_N_COINS", "100"))  # Top 100 por defecto
DATA_DIR = os.getenv("DATA_DIR", "data")

# Asegurar que el directorio de datos existe
os.makedirs(DATA_DIR, exist_ok=True)

# URLs de API
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
HEADERS = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Conexión a la base de datos
DB_PATH = os.path.join(DATA_DIR, "crypto_data.db")

def initialize_database():
    """Inicializa la base de datos SQLite para almacenar históricos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Crear tabla para datos de criptomonedas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS crypto_data (
        id INTEGER,
        symbol TEXT,
        name TEXT,
        price REAL,
        market_cap REAL,
        volume_24h REAL,
        percent_change_1h REAL,
        percent_change_24h REAL,
        percent_change_7d REAL,
        timestamp TEXT,
        PRIMARY KEY (id, timestamp)
    )
    ''')
    
    # Crear tabla para análisis y alertas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_results (
        timestamp TEXT,
        analysis_type TEXT,
        coin_symbol TEXT,
        result TEXT,
        alert_sent INTEGER,
        PRIMARY KEY (timestamp, analysis_type, coin_symbol)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente")

def get_crypto_data():
    """Obtiene los datos de las principales criptomonedas con manejo de errores."""
    try:
        params = {"limit": TOP_N_COINS, "convert": "USD"}
        response = requests.get(CMC_URL, headers=HEADERS, params=params, timeout=30)
        
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

def save_data_to_db(data):
    """Guarda los datos en la base de datos SQLite."""
    if not data:
        return
    
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for coin in data:
        try:
            cursor.execute('''
            INSERT INTO crypto_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                coin["id"],
                coin["symbol"],
                coin["name"],
                coin["quote"]["USD"]["price"],
                coin["quote"]["USD"]["market_cap"],
                coin["quote"]["USD"]["volume_24h"],
                coin["quote"]["USD"]["percent_change_1h"],
                coin["quote"]["USD"]["percent_change_24h"],
                coin["quote"]["USD"]["percent_change_7d"],
                timestamp
            ))
        except Exception as e:
            logger.error(f"Error al guardar {coin['symbol']}: {str(e)}")
    
    conn.commit()
    conn.close()
    logger.info(f"Datos guardados en la base de datos: {len(data)} monedas")

def save_raw_data(data):
    """Guarda los datos crudos en formato JSON para respaldo."""
    if not data:
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"crypto_data_{timestamp}.json")
    
    with open(filepath, 'w') as f:
        json.dump(data, f)
    
    logger.info(f"Datos crudos guardados en {filepath}")

def convert_to_dataframe(data):
    """Convierte los datos a un DataFrame de pandas para análisis."""
    if not data:
        return None
        
    # Extraer datos relevantes
    processed_data = []
    for coin in data:
        coin_data = {
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'price': coin['quote']['USD']['price'],
            'market_cap': coin['quote']['USD']['market_cap'],
            'volume_24h': coin['quote']['USD']['volume_24h'],
            'percent_change_1h': coin['quote']['USD']['percent_change_1h'],
            'percent_change_24h': coin['quote']['USD']['percent_change_24h'],
            'percent_change_7d': coin['quote']['USD']['percent_change_7d'],
            'volume_to_market_cap': coin['quote']['USD']['volume_24h'] / coin['quote']['USD']['market_cap'] if coin['quote']['USD']['market_cap'] > 0 else 0
        }
        processed_data.append(coin_data)
        
    df = pd.DataFrame(processed_data)
    return df

def analyze_market_data(df):
    """Realiza análisis financieros sobre los datos."""
    if df is None or df.empty:
        return {}
    
    analysis_results = {}
    
    # Top gainers and losers (24h)
    top_gainers = df.nlargest(5, 'percent_change_24h')[['symbol', 'percent_change_24h']]
    top_losers = df.nsmallest(5, 'percent_change_24h')[['symbol', 'percent_change_24h']]
    
    # Liquidez (volumen/market cap)
    high_liquidity = df.nlargest(5, 'volume_to_market_cap')[['symbol', 'volume_to_market_cap']]
    
    # Volatilidad (diferencia entre cambio de 1h y 24h)
    df['volatility'] = abs(df['percent_change_1h'] - df['percent_change_24h'] / 24)
    high_volatility = df.nlargest(5, 'volatility')[['symbol', 'volatility']]
    
    # Trend strength (consistencia entre cambios de 1h, 24h y 7d)
    df['trend_consistency'] = df.apply(
        lambda x: 1 if (x['percent_change_1h'] > 0 and x['percent_change_24h'] > 0 and x['percent_change_7d'] > 0) or
                      (x['percent_change_1h'] < 0 and x['percent_change_24h'] < 0 and x['percent_change_7d'] < 0) else 0, 
        axis=1
    )
    strong_trends = df[df['trend_consistency'] == 1].nlargest(5, 'market_cap')[['symbol', 'percent_change_24h', 'percent_change_7d']]
    
    # Market dominance (% del market cap total)
    total_market_cap = df['market_cap'].sum()
    df['market_dominance'] = df['market_cap'] / total_market_cap * 100 if total_market_cap > 0 else 0
    market_dominance = df.nlargest(5, 'market_dominance')[['symbol', 'market_dominance']]
    
    analysis_results = {
        'top_gainers': top_gainers.to_dict('records'),
        'top_losers': top_losers.to_dict('records'),
        'high_liquidity': high_liquidity.to_dict('records'),
        'high_volatility': high_volatility.to_dict('records'),
        'strong_trends': strong_trends.to_dict('records'),
        'market_dominance': market_dominance.to_dict('records')
    }
    
    # Guardar resultados relevantes en la BD
    save_analysis_results(analysis_results)
    
    return analysis_results

def save_analysis_results(analysis_results):
    """Guarda los resultados de análisis en la base de datos."""
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        for analysis_type, results in analysis_results.items():
            if isinstance(results, list):
                for result in results:
                    if 'symbol' in result:
                        cursor.execute('''
                        INSERT INTO analysis_results VALUES (?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            analysis_type,
                            result['symbol'],
                            json.dumps(result),
                            0  # alert_sent = False
                        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error al guardar análisis: {str(e)}")
    finally:
        conn.close()

def generate_charts(df, analysis_results):
    """Genera gráficos para el informe."""
    if df is None or df.empty:
        return None
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = os.path.join(DATA_DIR, f"market_overview_{timestamp}.png")
    
    try:
        # Crear figura con subplots
        fig, axs = plt.subplots(2, 2, figsize=(12, 10))
        
        # Top 10 por capitalización
        top_market_cap = df.nlargest(10, 'market_cap')
        axs[0, 0].bar(top_market_cap['symbol'], top_market_cap['market_cap'] / 1e9)
        axs[0, 0].set_title('Top 10 por Capitalización (Miles de Millones USD)')
        axs[0, 0].tick_params(axis='x', rotation=45)
        
        # Top gainers y losers
        top_movers = pd.concat([
            df.nlargest(5, 'percent_change_24h'), 
            df.nsmallest(5, 'percent_change_24h')
        ])
        colors = ['green' if x > 0 else 'red' for x in top_movers['percent_change_24h']]
        axs[0, 1].bar(top_movers['symbol'], top_movers['percent_change_24h'], color=colors)
        axs[0, 1].set_title('Mejores y Peores Rendimientos (24h %)')
        axs[0, 1].tick_params(axis='x', rotation=45)
        
        # Volumen de trading
        top_volume = df.nlargest(10, 'volume_24h')
        axs[1, 0].bar(top_volume['symbol'], top_volume['volume_24h'] / 1e9)
        axs[1, 0].set_title('Top 10 por Volumen (Miles de Millones USD)')
        axs[1, 0].tick_params(axis='x', rotation=45)
        
        # Liquidez (Volumen/Market Cap)
        top_liquidity = df.nlargest(10, 'volume_to_market_cap')
        axs[1, 1].bar(top_liquidity['symbol'], top_liquidity['volume_to_market_cap'])
        axs[1, 1].set_title('Top 10 por Liquidez (Volumen/Market Cap)')
        axs[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()
        
        logger.info(f"Gráficos guardados en {chart_path}")
        return chart_path
    except Exception as e:
        logger.error(f"Error al generar gráficos: {str(e)}")
        return None

def format_market_overview(df, top_n=10):
    """Crea un resumen del mercado general."""
    if df is None or df.empty:
        return "No hay datos disponibles"
        
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    # Calcular capitalización total del mercado
    total_market_cap = df['market_cap'].sum() / 1e9  # Miles de millones
    
    # Calcular volumen total de 24h
    total_volume = df['volume_24h'].sum() / 1e9  # Miles de millones
    
    # Media de cambio de precio en 24h
    avg_change_24h = df['percent_change_24h'].mean()
    
    # Media de cambio de precio en 7d
    avg_change_7d = df['percent_change_7d'].mean()
    
    # Monedas en positivo vs negativo (24h)
    positive_coins = len(df[df['percent_change_24h'] > 0])
    negative_coins = len(df[df['percent_change_24h'] <= 0])
    
    message = (
        f"🌐 *RESUMEN DEL MERCADO CRYPTO* ({now})\n\n"
        f"💰 *Capitalización total:* ${total_market_cap:.2f}B\n"
        f"📊 *Volumen 24h:* ${total_volume:.2f}B\n"
        f"📈 *Cambio medio 24h:* {avg_change_24h:.2f}%\n"
        f"📈 *Cambio medio 7d:* {avg_change_7d:.2f}%\n"
        f"🟢 *Monedas en positivo:* {positive_coins}\n"
        f"🔴 *Monedas en negativo:* {negative_coins}\n\n"
    )
    
    return message

def format_detailed_analysis(analysis_results):
    """Formatea los resultados del análisis detallado."""
    if not analysis_results:
        return "No hay datos de análisis disponibles"
    
    message = "*ANÁLISIS DETALLADO*\n\n"
    
    # Top gainers
    message += "📈 *Top Ganadores (24h)*\n"
    for coin in analysis_results.get('top_gainers', []):
        message += f"   - {coin['symbol']}: {coin['percent_change_24h']:.2f}%\n"
    message += "\n"
    
    # Top losers
    message += "📉 *Top Perdedores (24h)*\n"
    for coin in analysis_results.get('top_losers', []):
        message += f"   - {coin['symbol']}: {coin['percent_change_24h']:.2f}%\n"
    message += "\n"
    
    # High liquidity
    message += "💧 *Mayor Liquidez (Volumen/Market Cap)*\n"
    for coin in analysis_results.get('high_liquidity', []):
        message += f"   - {coin['symbol']}: {coin['volume_to_market_cap']:.4f}\n"
    message += "\n"
    
    # High volatility
    message += "⚡ *Mayor Volatilidad*\n"
    for coin in analysis_results.get('high_volatility', []):
        message += f"   - {coin['symbol']}: {coin['volatility']:.4f}\n"
    message += "\n"
    
    # Strong trends
    message += "🧠 *Tendencias Consistentes*\n"
    for coin in analysis_results.get('strong_trends', []):
        direction = "↗️" if coin.get('percent_change_24h', 0) > 0 else "↘️"
        message += f"   - {coin['symbol']}: {direction} 24h: {coin.get('percent_change_24h', 0):.2f}%, 7d: {coin.get('percent_change_7d', 0):.2f}%\n"
    message += "\n"
    
    # Market dominance
    message += "👑 *Dominancia de Mercado*\n"
    for coin in analysis_results.get('market_dominance', []):
        message += f"   - {coin['symbol']}: {coin['market_dominance']:.2f}%\n"
    
    return message

def format_top_coins(df, top_n=5):
    """Formatea los datos de las principales criptomonedas."""
    if df is None or df.empty:
        return "No hay datos disponibles"
        
    top_coins = df.nlargest(top_n, 'market_cap')
    
    message = "💰 *TOP CRIPTOMONEDAS POR CAPITALIZACIÓN*\n\n"
    
    for _, coin in top_coins.iterrows():
        change_24h = coin['percent_change_24h']
        change_emoji = "🟢" if change_24h > 0 else "🔴"
        
        message += (
            f"{change_emoji} *{coin['name']} ({coin['symbol']})*\n"
            f"   - Precio: ${coin['price']:,.2f}\n"
            f"   - Cap. de Mercado: ${coin['market_cap']:,.0f}\n"
            f"   - Cambio 24h: {change_24h:.2f}%\n"
            f"   - Volumen 24h: ${coin['volume_24h']:,.0f}\n\n"
        )
    
    return message

def send_message_to_telegram(message, photo_path=None):
    """Envía el mensaje y opcionalmente una imagen a Telegram."""
    try:
        if photo_path and os.path.exists(photo_path):
            # Enviar imagen con texto
            files = {'photo': open(photo_path, 'rb')}
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": message[:1024],  # Limitar captura a 1024 caracteres
                "parse_mode": "Markdown"
            }
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data=payload,
                files=files
            )
            files['photo'].close()
            
            # Si el mensaje es más largo que 1024 caracteres, enviar el resto como texto
            if len(message) > 1024:
                send_message_to_telegram(message[1024:])
        else:
            # Enviar solo texto
            # Fragmentar mensajes largos (límite de Telegram: 4096 caracteres)
            if len(message) > 4000:
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    payload = {
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": chunk,
                        "parse_mode": "Markdown"
                    }
                    requests.post(TELEGRAM_URL, json=payload, timeout=10)
            else:
                payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                requests.post(TELEGRAM_URL, json=payload, timeout=10)
        
        logger.info("Mensaje enviado a Telegram correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
        return False

def check_for_alerts(df, previous_df=None):
    """Comprueba si hay condiciones que disparen alertas."""
    if df is None or df.empty:
        return []
    
    alerts = []
    
    # Alerta por movimiento brusco de precio (>10% en 1h)
    big_movers = df[abs(df['percent_change_1h']) > 10]
    for _, coin in big_movers.iterrows():
        direction = "subido" if coin['percent_change_1h'] > 0 else "bajado"
        alerts.append(
            f"⚠️ *ALERTA DE MOVIMIENTO*: {coin['name']} ({coin['symbol']}) ha {direction} un {abs(coin['percent_change_1h']):.2f}% en la última hora."
        )
    
    # Si tenemos datos previos, podemos detectar cambios
    if previous_df is not None and not previous_df.empty:
        # Implementar lógica de comparación
        pass
    
    return alerts

def process_crypto_data():
    """Procesa los datos de criptomonedas y envía informes."""
    # Obtener datos
    data = get_crypto_data()
    if not data:
        logger.error("No se pudieron obtener datos. Saltando este ciclo.")
        return
    
    # Guardar datos crudos
    save_raw_data(data)
    
    # Guardar en BD
    save_data_to_db(data)
    
    # Convertir a DataFrame para análisis
    df = convert_to_dataframe(data)
    
    # Realizar análisis
    analysis_results = analyze_market_data(df)
    
    # Generar gráficos
    chart_path = generate_charts(df, analysis_results)
    
    # Formatear mensajes
    market_overview = format_market_overview(df)
    top_coins_msg = format_top_coins(df, top_n=5)
    analysis_msg = format_detailed_analysis(analysis_results)
    
    # Comprobar alertas
    alerts = check_for_alerts(df)
    alerts_msg = "\n".join(alerts) if alerts else ""
    
    # Enviar mensajes a Telegram
    if alerts_msg:
        send_message_to_telegram(alerts_msg)
    
    # Combinar mensajes en un reporte completo
    full_report = f"{market_overview}\n\n{top_coins_msg}\n\n{analysis_msg}"
    
    # Enviar reporte con gráfico si está disponible
    send_message_to_telegram(full_report, chart_path)
    
    logger.info("Ciclo de procesamiento completado correctamente")

def main():
    """Función principal que ejecuta el bot."""
    logger.info("Iniciando CryptoBot...")
    
    # Inicializar base de datos
    initialize_database()
    
    # Primera ejecución inmediata
    process_crypto_data()
    
    # Bucle principal
    while True:
        try:
            logger.info(f"Esperando {FETCH_INTERVAL} segundos hasta la próxima actualización...")
            time.sleep(FETCH_INTERVAL)
            process_crypto_data()
        except KeyboardInterrupt:
            logger.info("Bot detenido por el usuario")
            break
        except Exception as e:
            logger.error(f"Error en el bucle principal: {str(e)}")
            # Esperar un tiempo antes de reintentar
            time.sleep(60)

if __name__ == "__main__":
    main()