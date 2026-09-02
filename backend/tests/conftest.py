import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:5432/test"
os.environ["DATABASE_SSL"] = "false"
os.environ["DATABASE_INIT_ON_STARTUP"] = "false"
os.environ["FRONTEND_URL"] = "http://localhost:3000,http://127.0.0.1:3000"
