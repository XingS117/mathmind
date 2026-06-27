import httpx
r = httpx.post("http://localhost:8000/api/v1/auth/login", json={"username":"admin","password":"admin123"}, timeout=5)
print("Status:", r.status_code)
print("Body:", r.text)
