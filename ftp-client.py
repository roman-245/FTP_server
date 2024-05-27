import socket
import os

HOST = 'localhost'
PORT = 6666

def send_file(sock, filepath):
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            sock.sendall(data)

def receive_file(sock, filepath):
    with open(filepath, 'wb') as f:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            f.write(data)

sock = socket.socket()
sock.connect((HOST, PORT))

while True:
    request = input('> ')
    if request == "":
        request = "pwd"

    sock.send(request.encode())
    response = sock.recv(1024).decode()
    
    if response == 'upload':
        filename = request.split()[1]
        if os.path.exists(filename):
            send_file(sock, filename)
            response = sock.recv(1024).decode()
        else:
            print("File does not exist.")
            continue
    elif response.startswith('download'):
        filename = request.split()[1]
        receive_file(sock, os.path.join(os.getcwd(), filename))
        response = f"File {filename} downloaded"
    
    print(response)
    
    if response == 'exit' or response == 'Server stopping':
        break

sock.close()
