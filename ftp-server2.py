import socket
import os
import threading
import logging
import json

# Директория по умолчанию для работы сервера
base_dir = os.path.join(os.getcwd(), 'users')
server_running = True  # Переменная для управления состоянием сервера
client_threads = []  # Список для хранения клиентских потоков
server_lock = threading.Lock()  # Лок для синхронизации состояния сервера

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_logger = logging.getLogger('file_logger')
file_handler = logging.FileHandler('file_operations.log')
file_logger.addHandler(file_handler)

auth_logger = logging.getLogger('auth_logger')
auth_handler = logging.FileHandler('auth.log')
auth_logger.addHandler(auth_handler)

conn_logger = logging.getLogger('conn_logger')
conn_handler = logging.FileHandler('connections.log')
conn_logger.addHandler(conn_handler)

# Загрузка информации о пользователях из файла
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    else:
        return {}

# Сохранение информации о пользователях в файл
def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f)

# Проверка авторизации пользователя
def authenticate_user(username, password):
    users = load_users()
    if username in users and users[username]['password'] == password:
        auth_logger.info(f"User {username} authenticated successfully")
        return True
    else:
        auth_logger.warning(f"Authentication failed for user {username}")
        return False

# Регистрация нового пользователя
def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    else:
        user_dir = os.path.join(base_dir, username)
        os.makedirs(user_dir)
        users[username] = {'password': password, 'quota': 1024 * 1024 * 10}  # 10 MB quota
        save_users(users)
        auth_logger.info(f"New user {username} registered")
        return True

# Функция для обработки запросов клиента
def process(req, username):
    req = req.split()
    command = req[0].lower()
    user_dir = os.path.join(base_dir, username)

    if command == 'pwd':
        return user_dir
    elif command == 'ls':
        return '; '.join(os.listdir(user_dir))
    elif command == 'mkdir':
        dirname = os.path.join(user_dir, req[1])
        if not os.path.exists(dirname):
            os.makedirs(dirname)
            file_logger.info(f"User {username} created directory: {dirname}")
            return "Directory created: " + dirname
        else:
            return "Directory already exists"
    elif command == 'rmdir':
        dirname = os.path.join(user_dir, req[1])
        if os.path.exists(dirname):
            os.rmdir(dirname)
            file_logger.info(f"User {username} removed directory: {dirname}")
            return "Directory removed: " + dirname
        else:
            return "Directory does not exist"
    elif command == 'rmfile':
        filename = os.path.join(user_dir, req[1])
        if os.path.exists(filename):
            os.remove(filename)
            file_logger.info(f"User {username} removed file: {filename}")
            return "File removed: " + filename
        else:
            return "File does not exist"
    elif command == 'rename':
        old_path = os.path.join(user_dir, req[1]) 
        new_path = os.path.join(user_dir, req[2])
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            file_logger.info(f"User {username} renamed {old_path} to {new_path}")
            return f"Renamed from {old_path} to {new_path}"
        else:
            return "File does not exist"
    elif command == 'upload':
        # Ожидается, что клиент отправит файл после этой команды
        return 'upload'
    elif command == 'download':
        filename = os.path.join(user_dir, req[1])
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                file_logger.info(f"User {username} downloaded file: {filename}")
                return f.read()
        else:
            return "File does not exist"
    elif command == 'exit':
        return "exit"
    elif command == 'stop':
        if username == 'admin':
            with server_lock:
                global server_running
                server_running = False
            return "Server stopping"
        else:
            return "Insufficient privileges"
    else:
        return 'bad request'
    return ''  # Добавьте эту строку

def handle_client(conn, addr):
    conn_logger.info(f"Connected by {addr}")
    username = None

    while True:
        request = conn.recv(1024).decode()
        conn_logger.info(f"Received request from {addr}: {request}")

        if not username:
            # Ожидаем авторизации или регистрации пользователя
            req_parts = request.split()
            if len(req_parts) == 3:
                action, username, password = req_parts
                if action == 'login':
                    if authenticate_user(username, password):
                        conn.send("Authenticated".encode())
                    else:
                        conn.send("Authentication failed".encode())
                elif action == 'register':
                    if register_user(username, password):
                        conn.send("Registered".encode())
                    else:
                        conn.send("Registration failed".encode())
            else:
                conn.send("Bad request".encode())
        else:
            if request:
                response = process(request, username)

                if response == 'upload':
                    # Получаем файл от клиента
                    filename = request.split()[1]
                    filepath = os.path.join(base_dir, username, filename)
                    
                    users = load_users()
                    user_quota = users[username]['quota']
                    file_size = int(conn.recv(1024).decode())
                    
                    if file_size > user_quota:
                        conn.send("Insufficient quota".encode())
                    else:
                        users[username]['quota'] -= file_size
                        save_users(users)

                        with open(filepath, 'wb') as f:
                            while True:
                                data = conn.recv(1024)
                                if not data:
                                    break
                                f.write(data)
                        file_logger.info(f"User {username} uploaded file: {filepath}")
                        conn.send(f"File {filename} uploaded".encode())

                elif isinstance(response, bytes):
                    # Отправляем файл клиенту
                    conn.sendall(response)
                else:
                    conn.send(response.encode())

                if response in ["exit", "Server stopping", "stop"]:
                    break
            else:
                conn.send("".encode())

    conn.close()
    conn_logger.info(f"Disconnected from {addr}")

# Основная функция для запуска сервера
def main():
    global server_running
    PORT = 6666

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))
    sock.listen()
    sock.settimeout(1.0)  # Устанавливаем таймаут для функции accept
    conn_logger.info(f"Listening on port {PORT}")

    while True:
        with server_lock:
            if not server_running:
                break
        try:
            conn, addr = sock.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
            client_threads.append(client_thread)
        except socket.timeout:
            continue
        except Exception as e:
            conn_logger.error(f"Error accepting connections: {e}")
            break

    # Ожидание завершения всех клиентских потоков
    for thread in client_threads:
        thread.join()

    sock.close()
    conn_logger.info("Server stopped")

if __name__ == "__main__":
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    main()
