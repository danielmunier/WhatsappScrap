from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import json
import time
import re
import logging

SHEETDB_URL = ''
SHEETDB_TOKEN = ''  

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicia o navegador
browser = webdriver.Chrome()

def start_whatsapp_web():
    # Acessa o WhatsApp Web
    browser.get("https://web.whatsapp.com")
    # Espera o usuário escanear o QR code se necessário 
    input('Pressione "Enter" após escanear o QR code e o WhatsApp Web estar carregado completamente')


def send_data_to_sheetdb(data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SHEETDB_TOKEN}'
    }
    response = requests.post(SHEETDB_URL, data=json.dumps(data), headers=headers)
    logging.info(response.json())


def contains_trigger(message):
    score_regex = re.compile(r'consulta(r)?[\s_-]?score', re.IGNORECASE)
    documentation_regex = re.compile(r'documenta(c|ç)(a|ã)o', re.IGNORECASE)
    link_request_regex = re.compile(r'pedido[\s_-]?de[\s_-]?link', re.IGNORECASE)
    return (
        score_regex.search(message) is not None or 
        documentation_regex.search(message) is not None or 
        link_request_regex.search(message) is not None
    )

def to_title_case(name):
    return ' '.join(word.capitalize() for word in name.split())

def format_cpf(cpf):
    cleaned = re.sub(r'\D', '', cpf)
    formatted = f'{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}'
    return formatted

def extract_data(message):
    lines = message.split('\n')
    data = {"Nome": "", "Nascimento": "", "CPF": "", "Cidade": "", "Consultora": "", "Bairro": ""}  
    
    for line in lines:
        line = line.strip()
        if re.match(r'^nome:', line, re.IGNORECASE):
            data['Nome'] = line.split(':', 1)[1].strip()
        elif re.match(r'^cpf:', line, re.IGNORECASE):
            data['CPF'] = format_cpf(line.replace('cpf:', '').strip())
        elif re.match(r'^nascimento:', line, re.IGNORECASE):
            data['Nascimento'] = line.split(':', 1)[1].strip()  # Captura o valor após os dois pontos
        elif re.match(r'^(endereço|bairro|cidade):', line, re.IGNORECASE):
            if 'Cidade' not in data:
                data['Cidade'] = ""
            data['Bairro'] += " " + to_title_case(line.split(':', 1)[1].strip())
            data['Cidade'] += " " + to_title_case(line.split(':', 1)[1].strip())
        elif re.match(r'^(consultora|consultor):', line, re.IGNORECASE):
            data['Consultor'] = line.split(':', 1)[1].strip()
            data['Consultora'] = line.split(':', 1)[1].strip()
    
    return data


def get_latest_messages():
    messages = browser.find_elements(By.CSS_SELECTOR, "div.message-in, div.message-out")
    latest_messages = []
    for message in messages[-10:]:
        text_elements = message.find_elements(By.CSS_SELECTOR, "span.selectable-text")
        for element in text_elements:
            latest_messages.append(element.text)
    return latest_messages

def monitor_conversation():
    logging.info("Monitorando mensagens...")
    last_messages = get_latest_messages()
    while True:
        try:
            current_messages = get_latest_messages()
            if current_messages != last_messages:
                new_messages = [msg for msg in current_messages if msg not in last_messages]
                for msg in new_messages:
                    logging.info(f"Nova mensagem: {msg}")
                    if contains_trigger(msg):
                        data = extract_data(msg)
                        logging.info(f"Dados extraídos: {data}")
                        send_data_to_sheetdb(data)
                last_messages = current_messages
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erro: {e}")
            break

try:
    start_whatsapp_web()
    monitor_conversation()
except KeyboardInterrupt:
    logging.info("Bot interrompido pelo usuário.")
finally:
    browser.quit()
