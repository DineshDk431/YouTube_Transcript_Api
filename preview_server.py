from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir("c:/Youtube_transcript")

class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.js': 'application/javascript',
        '.css': 'text/css',
    }

print("=" * 50)
print("  UI Preview Server Running!")
print("=" * 50)
print()
print("  Login Page:     http://localhost:8080/static/login.html")
print("  Dashboard Page: http://localhost:8080/static/dashboard.html")
print()
print("  Press Ctrl+C to stop")
print("=" * 50)

HTTPServer(("", 8080), Handler).serve_forever()
