import threading, os
from dotenv import load_dotenv
load_dotenv()

import database as db
db.init_db()
print("✅ Database initialized.")

from dashboard import run_dashboard
from bot import run_bot

t = threading.Thread(target=run_dashboard, daemon=True)
t.start()
run_bot()
