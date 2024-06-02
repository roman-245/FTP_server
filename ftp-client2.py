import socket
import os

HOST = 'localhost'
PORT = 6666

def send_file(sock, filepath):
    file_size = os.path.getsize(filepath)
    sock.send(str(file_size).encode())
    response = sock.recv(1024).decode()
    if response == "Insufficient quota":
        print("Insufficient quota to upload the file")
        return
    
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

authenticated = False
while not authenticated:
    action = input("Enter 'login' to log in or 'register' to create a new account: ")
    if action == 'login' or action == 'register':
        username = input("Username: ")
        password = input("Password: ")
        request = f"{action} {username} {password}"
        sock.send(request.encode())
        response = sock.recv(1024).decode()
        print(response)
        if response == "Authenticated" or response == "Registered":
            authenticated = True

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
    