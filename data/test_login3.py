import httpx, sys
sys.path.insert(0, "D:/Sven/maths")
from backend.database import SessionLocal
from backend.models.user import User
from backend.services.auth_service import verify_password

db = SessionLocal()
user = db.query(User).filter(User.username == "admin").first()
print("User:", user.username if user else "NOT FOUND")
print("Hash:", user.password_hash[:20] if user and user.password_hash else "NONE")
print("Verify:", verify_password("admin123", user.password_hash) if user and user.password_hash else "N/A")
db.close()

r = httpx.post("http://localhost:8000/api/v1/auth/login", json={"username":"admin","password":"admin123"}, timeout=5)
print("API:", r.status_code)
