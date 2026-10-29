import json
import os
import socket
import urllib.parse


HOST = "127.0.0.1"
PORT = 8080


def parse_http_request(data):
    if "\r\n\r\n" in data:
        parts = data.split("\r\n\r\n", 1)
    else:
        parts = data.split("\n\n", 1)

    header_part = parts[0]
    body = ""
    if len(parts) > 1:
        body = parts[1]

    lines = header_part.split("\r\n")
    if not lines or not lines[0]:
        return None

    request_line = lines[0].split(" ")
    if len(request_line) < 3:
        return None

    method = request_line[0].upper().strip()
    full_path = request_line[1]

    parsed_url = urllib.parse.urlparse(full_path)
    path = parsed_url.path
    query_params = urllib.parse.parse_qs(parsed_url.query)

    headers = {}

    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value
    return {
        "method": method,
        "path": path,
        "query_params": query_params,
        "headers": headers,
        "body": body,
    }


def build_response(status_code, status_text, content_type, body, extra_headers=None):
    body_bytes = body.encode("utf-8")
    response_lines = [
        f"HTTP/1.1 {status_code} {status_text}",
        f"Content-Type: {content_type}; charset=utf-8",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close"
    ]

    if extra_headers:
        for k, v in extra_headers.items():
            response_lines.append(f"{k}: {v}")

    response_header = "\r\n".join(response_lines) + "\r\n\r\n"
    return response_header.encode("utf-8") + body_bytes


def handle_request(request):
    if not request:
        return build_response(400, "Bad Request", "text/plain", "Invalid HTTP Request")
    method = request["method"]
    path = request["path"]

    if method == "GET":
        if path == "/" or path == "/index.html":
            if os.path.exists("index.html"):
                with open("index.html", "r") as f:
                    content = f.read()
                return build_response(200, "OK", "text/html", content)
            else:
                return build_response(200, "OK", "text/html", "<h1>Welcome!</h1>")

        elif path == "/page":
            user_id = request["query_params"].get("id", ["Not specified"])[0]
            html = f"<html><body><h1>Page</h1><p>Requested ID: {user_id}</p></body></html>"
            return build_response(200, "OK", "text/html", html)
        else:
            return build_response(400, "Not Found", "text/html", "<h1>404 Not Found</h1>")
    elif method == "POST":
        content_type = request["headers"].get("content-type", "")
        if "application/json" in content_type:
            try:
                json_data = json.loads(request["body"])
                response_body = json.dumps({"status": "success", "received_data": json_data})
                return build_response(200, "OK", "application/json", response_body)
            except json.JSONDecodeError:
                return build_response(400, "Bad Request", "application/json", '{"error": "Invalid JSON"}')
        else:
            return build_response(415, "Unsupported Media Type", "text/plain", "Expected application/json")
    
    return build_response(405, "Method Not Allowed", "text/plain", "Method not supported")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"\nServer is started on http://{HOST}:{PORT}/\n")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            data = client_socket.recv(4096).decode("utf-8", errors="ignore")
            
            if data:
                parsed_req = parse_http_request(data)

                if parsed_req and parsed_req["method"] == "POST":
                    content_length = int(parsed_req["headers"].get("content-length", 0))
                    already_read_body = len(parsed_req["body"].encode("utf-8"))

                    while already_read_body < content_length:
                        chunk = client_socket.recv(4096).decode("utf-8", errors="ignore")

                        if not chunk:
                            break
                        parsed_req["body"] += chunk
                        already_read_body += len(chunk.encode("utf-8"))

                response = handle_request(parsed_req)
                client_socket.sendall(response)

            client_socket.close()
    except KeyboardInterrupt:
        print("\nServer is closing.\n")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()