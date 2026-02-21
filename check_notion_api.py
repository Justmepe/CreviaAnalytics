#!/usr/bin/env python3
from notion_client import Client
import os

api_key = os.getenv('NOTION_API_KEY', '')
client = Client(auth=api_key)

print("Client type:", type(client))
print("\nClient methods:")
methods = [m for m in dir(client) if not m.startswith('_')]
for m in methods:
    print(f"  - {m}")

print("\n\nDatabases endpoint type:", type(client.databases))
print("Databases endpoint methods:")
db_methods = [m for m in dir(client.databases) if not m.startswith('_')]
for m in db_methods:
    print(f"  - {m}")

# Try to use search instead
print("\n\nTrying search endpoint:")
search_methods = [m for m in dir(client.search) if not m.startswith('_')]
for m in search_methods:
    print(f"  - {m}")
