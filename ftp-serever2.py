import socket
import os
import shutil
import threading

# Директория по умолчанию для работы сервера
dirname = os.path.join(os.getcwd(), 'docs')
server_running = True  # Переменная для управления состоянием сервера

# Функция для обработки запросов клиента
def process(req):
    req = req.split()
    command = req[0].lower()

    if command == 'pwd':
        return dirname
    elif command == 'ls':
        return '; '.join(os.listdir(dirname))
    elif command == 'mkdir':
        if not os.path.exists(os.path.join(dirname, req[1])):
            os.makedirs(os.path.join(dirname, req[1]))
            return "Directory created: " + os.path.join(dirname, req[1])
        else:
            return "Directory already exists"
    elif command == 'rmdir':
        path = os.path.join(dirname, req[1])
        if os.path.exists(path):
            os.rmdir(path)
            return "Directory removed: " + path
        else:
            return "Directory does not exist"
    elif command == 'rmfile':
        path = os.path.join(dirname, req[1])
        if os.path.exists(path):
            os.remove(path)
            return "File removed: " + path
        else:
            return "File does not exist"
    elif command == 'rename':
        old_path = os.path.join(dirname, req[1])
        new_path = os.path.join(dirname, req[2])
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            return "Renamed from {} to {}".format(old_path, new_path)
        else:
            return "File does not exist"
    elif command == 'upload':
        # Ожидается, что клиент отправит файл после этой команды
        return 'upload'
    elif command == 'download':
        path = os.path.join(dirname, req[1])
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return f.read()
        else:
            return "File does not exist"
    elif command == 'exit':
        return "exit"
    elif command == 'stop':
        global server_running
        server_running = False
        return "Server stopping"
    else:
        return 'bad request'

# Функция для обработки клиента в отдельном потоке
def handle_client(conn, addr):
    print(f"Connected by {addr}")

    while True:
        request = conn.recv(1024).decode()
        print(f"Received request: {request}")

        if request:
            response = process(request)

            if response == 'upload':
                # Получаем файл от клиента
                filename = request.split()[1]
                filepath = os.path.join(dirname, filename)
                with open(filepath, 'wb') as f:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        f.write(data)
                conn.send(f"File {filename} uploaded".encode())
            elif isinstance(response, bytes):
                # Отправляем файл клиенту
                conn.sendall(response)
            else:
                conn.send(response.encode())

            if response == "exit":
                break
            elif response == "Server stopping":
                conn.close()
                break

    conn.close()
    print(f"Disconnected from {addr}")

# Основная функция для запуска сервера
def main():
    global server_running
    PORT = 6666

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))
    sock.listen()
    print("Listening on port", PORT)

    while server_running:
        conn, addr = sock.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

    sock.close()
    print("Server stopped")

if __name__ == "__main__":
    main()
