#!/usr/bin/env python3
import os
import sys
import time
import json
import requests
import random
import sqlite3
import logging
import schedule
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('userbot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('K-Connect-UserBot')

API_URL = 'https://k-connect.ru/api/'
TOKEN = 'asdfasdfasdfasdfasghashasdfhashASHSADFHDFH' # Замените на реальный TOKEN
USERNAME = 'qsqsqs@gmail.com'  # Замените на реальный username
PASSWORD = '12312312.'  # Замените на реальный пароль
# Укажите имя канала или ID аккаунта для публикации (оставьте пустым для основного аккаунта)
CHANNEL_NAME = 'memeKconnect'  # Имя канала для публикации
ACCOUNT_ID = None  # ID аккаунта (используется, если CHANNEL_NAME пустой)

MEMES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memes')
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'posted_files.db')

os.makedirs(MEMES_FOLDER, exist_ok=True)

session = requests.Session()

def get_user_channels():

    try:
        channels_url = urljoin(API_URL, 'users/my-channels')
        response = session.get(channels_url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info(f"Успешно получен список каналов и аккаунтов")
                return data
            else:
                logger.error(f"Ошибка получения списка каналов: {data.get('error')}")
        else:
            logger.error(f"Ошибка запроса списка каналов. Код: {response.status_code}")
    except Exception as e:
        logger.error(f"Исключение при получении списка каналов: {str(e)}")
    
    return None

def switch_account(account_id):

    try:
        switch_url = urljoin(API_URL, 'users/switch-account')
        data = {"account_id": account_id}
        
        response = session.post(switch_url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"Успешное переключение на аккаунт {account_id}")
                return True
            else:
                logger.error(f"Ошибка переключения аккаунта: {result.get('error')}")
        else:
            logger.error(f"Ошибка запроса переключения аккаунта. Код: {response.status_code}")
    except Exception as e:
        logger.error(f"Исключение при переключении аккаунта: {str(e)}")
    
    return False

def find_account_by_name(channels_data, name):

    if not channels_data:
        return None
        
    channels = channels_data.get('channels', [])
    for channel in channels:
        if channel.get('name').lower() == name.lower() or channel.get('username').lower() == name.lower():
            return channel.get('id')
    
    main_account = channels_data.get('main_account')
    if main_account and (main_account.get('name').lower() == name.lower() or 
                          main_account.get('username').lower() == name.lower()):
        return main_account.get('id')
    
    current_account = channels_data.get('current_account')
    if current_account and (current_account.get('name').lower() == name.lower() or 
                             current_account.get('username').lower() == name.lower()):
        return current_account.get('id')
    
    return None

def authenticate():

    logger.info("Выполняется авторизация...")
    
    session.cookies.set("konnect_session", TOKEN, domain="k-connect.ru")
    
    try:
        auth_check_url = urljoin(API_URL, 'auth/check')
        auth_response = session.get(auth_check_url)
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            if auth_data.get('isAuthenticated'):
                logger.info("Авторизация с помощью cookie успешна")
                
                return handle_account_switching()
            else:
                logger.warning("Сессия недействительна, требуется логин")
        else:
            logger.error(f"Ошибка проверки сессии. Код: {auth_response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при проверке авторизации: {str(e)}")
    
    try:
        login_url = urljoin(API_URL, 'auth/login')
        login_data = {
            "usernameOrEmail": USERNAME,
            "password": PASSWORD
        }
        
        login_response = session.post(login_url, json=login_data)
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data.get('success'):
                logger.info("Авторизация через логин/пароль успешна")
                
                return handle_account_switching()
            else:
                logger.error(f"Ошибка авторизации: {login_data.get('error')}")
        else:
            logger.error(f"Ошибка при авторизации. Код: {login_response.status_code}")
    except Exception as e:
        logger.error(f"Исключение при авторизации: {str(e)}")
    
    return False

def handle_account_switching():

    if not CHANNEL_NAME and not ACCOUNT_ID:
        logger.info("Используется текущий аккаунт (не указан канал или ID для переключения)")
        return True
    
    channels_data = get_user_channels()
    if not channels_data:
        logger.error("Не удалось получить список каналов")
        return False
    
    current_account = channels_data.get('current_account', {})
    logger.info(f"Текущий аккаунт: {current_account.get('name')} ({current_account.get('id')})")
    
    if ACCOUNT_ID:
        if str(current_account.get('id')) == str(ACCOUNT_ID):
            logger.info(f"Уже в нужном аккаунте с ID {ACCOUNT_ID}")
            return True
            
        logger.info(f"Переключение на аккаунт с ID {ACCOUNT_ID}")
        return switch_account(ACCOUNT_ID)
    
    if CHANNEL_NAME:
        account_id = find_account_by_name(channels_data, CHANNEL_NAME)
        
        if not account_id:
            logger.error(f"Канал с именем '{CHANNEL_NAME}' не найден")
            return False
            
        if str(current_account.get('id')) == str(account_id):
            logger.info(f"Уже в нужном аккаунте: {CHANNEL_NAME} ({account_id})")
            return True
            
        logger.info(f"Переключение на аккаунт {CHANNEL_NAME} ({account_id})")
        return switch_account(account_id)
    
    return True

def init_database():

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posted_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        post_id INTEGER,
        post_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def is_file_posted(filename):

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM posted_files WHERE filename = ?", (filename,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_file_as_posted(filename, post_id):

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posted_files (filename, post_id, post_date) VALUES (?, ?, ?)",
        (filename, post_id, datetime.now())
    )
    conn.commit()
    conn.close()
    logger.info(f"Файл {filename} отмечен как опубликованный с post_id {post_id}")

def get_files_to_post():

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    files_to_post = []
    
    for file in os.listdir(MEMES_FOLDER):
        file_path = os.path.join(MEMES_FOLDER, file)
        if os.path.isfile(file_path):
            ext = file.rsplit('.', 1)[1].lower() if '.' in file else ''
            if ext in allowed_extensions and not is_file_posted(file):
                files_to_post.append(file)
    
    return files_to_post

def post_image(filename):

    file_path = os.path.join(MEMES_FOLDER, filename)
    
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не найден")
        return None
    
    files = {
        'images[]': (filename, open(file_path, 'rb'), f'image/{filename.split(".")[-1]}')
    }
    
    data = {
        'content': f'Автоматический пост 🤖'
    }
    
    try:
        if not authenticate():
            logger.error("Невозможно опубликовать пост - ошибка авторизации")
            return None
        
        response = session.post(
            urljoin(API_URL, 'posts/create'),
            data=data,
            files=files
        )
        
        files['images[]'][1].close()
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                post_id = response_data.get('post', {}).get('id')
                logger.info(f"Успешно опубликован пост с ID {post_id}, файл: {filename}")
                return post_id
            else:
                logger.error(f"Ошибка публикации поста: {response_data.get('error')}")
        else:
            logger.error(f"Ошибка публикации поста. Код: {response.status_code}, Ответ: {response.text}")
    
    except Exception as e:
        logger.error(f"Исключение при публикации поста: {str(e)}")
    
    return None

def publish_post():

    files_to_post = get_files_to_post()
    
    if not files_to_post:
        logger.info("Нет новых файлов для публикации")
        return
    
    selected_file = random.choice(files_to_post)
    logger.info(f"Выбран файл для публикации: {selected_file}")
    
    post_id = post_image(selected_file)
    
    if post_id:
        mark_file_as_posted(selected_file, post_id)
        logger.info(f"Файл {selected_file} успешно опубликован и отмечен в БД")
    else:
        logger.error(f"Не удалось опубликовать файл {selected_file}")

def main():

    logger.info("Запуск UserBot для публикации постов")
    
    init_database()
    
    if not authenticate():
        logger.error("Не удалось авторизоваться. Проверьте TOKEN или логин/пароль.")
        sys.exit(1)
    
    files_count = len(get_files_to_post())
    logger.info(f"Доступно файлов для публикации: {files_count}")
    
    schedule.every(1).hours.do(publish_post)
    logger.info("Расписание настроено: публикация каждый час")
    
    logger.info("Публикация первого поста при запуске...")
    publish_post()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        sys.exit(1)
