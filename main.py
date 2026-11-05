import mimetypes
import pathlib
import urllib.parse
import socket
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from multiprocessing import Process
from pymongo import MongoClient

HTTP_PORT = 3000
SOCKET_PORT = 5000
SOCKET_HOST = '127.0.0.1'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017')

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/message.html')
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        try:
            with open(filename, 'rb') as fd:
                self.wfile.write(fd.read())
        except FileNotFoundError:
            self.wfile.write(b"File not found")

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

def run_http_server():
    server_address = ('0.0.0.0', HTTP_PORT)
    http = HTTPServer(server_address, HttpHandler)
    print(f"HTTP Server is running on port {HTTP_PORT}...")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

def run_socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", SOCKET_PORT))
    print(f"Socket Server is running on port {SOCKET_PORT}...")
    
    client = MongoClient(MONGO_URI)
    db = client.messages_db
    collection = db.messages

    try:
        while True:
            data, address = server_socket.recvfrom(1024)
            data_dict = dict(urllib.parse.parse_qsl(data.decode()))
            
            document = {
                "date": str(datetime.now()),
                "username": data_dict.get('username'),
                "message": data_dict.get('message')
            }
            collection.insert_one(document)
            print(f"Saved to MongoDB: {document}")
    except KeyboardInterrupt:
        server_socket.close()
    finally:
        client.close()

if __name__ == '__main__':
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()