from apscheduler.schedulers.background import BackgroundScheduler

# Define a global instance so it can be accessed anywhere
scheduler = BackgroundScheduler()

def start_scheduler():
    # To prevent circular imports, import tasks here
    from app.services.trading_logic import monitor_open_positions, run_all_agents
    from datetime import datetime, timezone
    
    # 1. Job Canh gia Chot loi / Cat lo: Chay moi 1 phut
    scheduler.add_job(
        func=monitor_open_positions,
        trigger="interval",
        minutes=1,
        id="monitor_tp_sl_job",
        replace_existing=True
    )
    
    # 2. Job AI Phan tich tim co phieu: Chay moi 30 phut
    scheduler.add_job(
        func=run_all_agents,
        trigger="interval",
        minutes=30,
        id="automated_trading_job",
        next_run_time=datetime.now(timezone.utc),
        replace_existing=True
    )
    
    scheduler.start()
    print("[Core] Background Scheduler started.")
    return scheduler

def stop_scheduler():
    scheduler.shutdown(wait=False)
    print("[Core] Background Scheduler stopped.")
