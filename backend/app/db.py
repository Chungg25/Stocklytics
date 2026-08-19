import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    supabase: Client = create_client(url, key)
else:
    supabase = None
    print("Warning: SUPABASE_URL or SUPABASE_KEY is missing. Database features will be disabled.")
