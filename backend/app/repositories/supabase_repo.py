from app.db import supabase

class SupabaseRepository:
    def __init__(self):
        self.db = supabase

    def get_portfolios(self):
        if not self.db: return []
        res = self.db.table("paper_portfolio").select("*").execute()
        return res.data if res.data else []

    def update_cash_balance(self, portfolio_id, new_balance):
        if not self.db: return None
        res = self.db.table("paper_portfolio").update({"cash_balance": new_balance}).eq("id", portfolio_id).execute()
        return res.data

    def get_position(self, portfolio_id, ticker):
        if not self.db: return None
        res = self.db.table("paper_positions").select("*").eq("portfolio_id", portfolio_id).eq("ticker", ticker).execute()
        return res.data[0] if res.data else None

    def get_all_positions(self):
        if not self.db: return []
        res = self.db.table("paper_positions").select("*").execute()
        return res.data if res.data else []

    def update_position(self, pos_id, data):
        if not self.db: return None
        res = self.db.table("paper_positions").update(data).eq("id", pos_id).execute()
        return res.data

    def insert_position(self, data):
        if not self.db: return None
        res = self.db.table("paper_positions").insert(data).execute()
        return res.data

    def delete_position(self, pos_id):
        if not self.db: return None
        res = self.db.table("paper_positions").delete().eq("id", pos_id).execute()
        return res.data

    def insert_trade(self, data):
        if not self.db: return None
        res = self.db.table("paper_trades").insert(data).execute()
        return res.data

    def insert_ai_decision(self, data):
        if not self.db: return None
        res = self.db.table("ai_decisions").insert(data).execute()
        return res.data

    def get_watchlist(self):
        if not self.db: return []
        res = self.db.table("ai_watchlist").select("ticker, fundamental_context, last_full_analysis").execute()
        return res.data if res.data else []

    def update_watchlist(self, ticker, data):
        if not self.db: return None
        res = self.db.table("ai_watchlist").update(data).eq("ticker", ticker).execute()
        return res.data

# Global instance
db_repo = SupabaseRepository()
