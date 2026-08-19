import json
import re

def parse_trading_decision(full_text: str):
    decision = "HOLD"
    take_profit = None
    stop_loss = None
    
    # Try parsing JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            decision = data.get("decision", "HOLD").upper()
            if "MUA" in decision or "BUY" in decision:
                decision = "BUY"
            elif "BÁN" in decision or "SELL" in decision or "BAN" in decision:
                decision = "SELL"
            else:
                decision = "HOLD"
                
            tp_val = data.get("execution_take_profit", 0.0)
            sl_val = data.get("execution_stop_loss", 0.0)
            
            if float(tp_val) > 0:
                take_profit = float(tp_val)
            if float(sl_val) > 0:
                stop_loss = float(sl_val)
        except Exception as e:
            print(f"[Paper Trading] Parse JSON from AI failed: {e}")
            
    if not json_match:
        # Fallback regex if AI forgot JSON
        tail_text = full_text[-500:]
        if re.search(r'(FINAL DECISION|QUYẾT ĐỊNH).*?(BUY|MUA)', tail_text, re.DOTALL | re.IGNORECASE):
            decision = "BUY"
        elif re.search(r'(FINAL DECISION|QUYẾT ĐỊNH).*?(SELL|BÁN)', tail_text, re.DOTALL | re.IGNORECASE):
            decision = "SELL"
            
        tp_match = re.search(r'(?:Take Profit|Chốt lời|Chốt Lời).*?(?:[:\$]|\s)(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
        if tp_match:
            take_profit = float(tp_match.group(1))
            
        sl_match = re.search(r'(?:Stop Loss|Cắt lỗ|Cắt Lỗ).*?(?:[:\$]|\s)(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
        if sl_match:
            stop_loss = float(sl_match.group(1))

    return {
        "decision": decision,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "rationale": full_text
    }
