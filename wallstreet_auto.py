import requests, time, json, os, random
from datetime import datetime
import matplotlib.pyplot as plt

# ========= إعداداتك =========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FILE_TRADES = "trades.json"
FILE_OPEN = "open_trade.json"
LOT_SIZE = 0.02  # 0.02 lot = 2 ounce
# ===========================

HEADERS = {"User-Agent": "Mozilla/5.0"}

def load_json(f, default):
    if os.path.exists(f):
        with open(f,'r') as j: return json.load(j)
    return default

def save_json(f, data):
    with open(f,'w') as j: json.dump(j,f)

def get_stats():
    trades = load_json(FILE_TRADES, [])
    if not trades:
        return {"total":0,"win":0,"loss":0,"pnl":0,"best":0,"worst":0,"last":0}
    pnl = sum(t['pnl'] for t in trades)
    win = len([t for t in trades if t['pnl']>0])
    return {
        "total": len(trades),
        "win": win,
        "loss": len(trades)-win,
        "pnl": round(pnl,2),
        "best": round(max(t['pnl'] for t in trades),2),
        "worst": round(min(t['pnl'] for t in trades),2),
        "last": round(trades[-1]['pnl'],2)
    }

def send_photo(caption, path):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(path,"rb") as ph:
            requests.post(url, data={"chat_id":CHAT_ID,"caption":caption,"parse_mode":"Markdown"}, files={"photo":ph}, timeout=20)
    except Exception as e: print(e)

def send_msg(txt):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id":CHAT_ID,"text":txt,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def create_chart(gold, sl, tp, action, stats, open_trade=None):
    prices = [gold + random.uniform(-4,4) for _ in range(60)]
    fig = plt.figure(figsize=(10,6), facecolor='black')
    ax = plt.gca()
    ax.set_facecolor('black')
    ax.plot(prices, color='#FFD700', linewidth=2, label='XAUUSD')

    # رسم الصفقة المفتوحة
    if open_trade:
        ax.axhline(open_trade['entry'], color='cyan', linestyle='--', label=f"ENTRY {open_trade['entry']:.2f}")
        ax.axhline(open_trade['sl'], color='#ff4444', linestyle='--', label=f"SL {open_trade['sl']:.2f}")
        ax.axhline(open_trade['tp'], color='#00ff00', linestyle='--', label=f"TP {open_trade['tp']:.2f}")
        # PnL حي
        live_pnl = (gold - open_trade['entry'])* (LOT_SIZE*100) if "BUY" in open_trade['action'] else (open_trade['entry']-gold)*(LOT_SIZE*100)
        pnl_color = '#00ff00' if live_pnl>=0 else '#ff4444'
    else:
        ax.axhline(gold, color='cyan', linestyle='--')
        live_pnl = 0
        pnl_color = 'white'

    # بوكس AURA STYLE
    hold_text = f"${live_pnl:.2f}" if open_trade else "NO TRADE"
    box = f"""1 SESSION P&L (USD)
${stats['pnl']}  LAST {stats['last']:+.2f}
BEST +{stats['best']}  WORST {stats['worst']}

1 POSITION
{open_trade['action'] if open_trade else action} {LOT_SIZE} lots @ {open_trade['entry'] if open_trade else gold:.2f}
HOLD {hold_text}  MARGIN $16.66 1:500

1 RADAR
• {'IN TRADE' if open_trade else 'WAITING'}
Trades {stats['total']} | W:{stats['win']} L:{stats['loss']}
SPEED 5.2 t/s  ATR 183"""

    props = dict(boxstyle='round', facecolor='#111', edgecolor='#FFD700', alpha=0.95)
    ax.text(0.02, 0.97, box, transform=ax.transAxes, fontsize=8, color='#FFD700', bbox=props, family='monospace', va='top')
    ax.tick_params(colors='white')
    plt.title(f"XAUUSD | {action} | LIVE {gold:.2f} | {datetime.now().strftime('%H:%M:%S')}", color='white', fontsize=10)
    plt.tight_layout()
    plt.savefig("chart.png", dpi=150, facecolor='black')
    plt.close()
    return "chart.png"

# --- جلب السعر ---
def get_gold_price():
    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=10, headers=HEADERS).json()
        p = float(r.get('price',0))
        if p>1000: return p
    except: pass
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=1m", timeout=10, headers=HEADERS).json()
        return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
    except: return 4164.0

def get_yahoo(sym):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1m"
        r=requests.get(url, timeout=10, headers=HEADERS).json()
        meta=r['chart']['result'][0]['meta']
        return float(meta['regularMarketPrice']), float(meta['regularMarketPrice'])-float(meta.get('chartPreviousClose', meta['regularMarketPrice']))
    except: return 0,0

def analyze():
    gold = get_gold_price()
    dxy, dxy_chg = get_yahoo("DX-Y.NYB")
    us10y, us10y_chg = get_yahoo("%5ETNX")
    vix, _ = get_yahoo("%5EVIX")
    score=0
    if dxy_chg<-0.20: score+=4
    elif dxy_chg>0.20: score-=4
    if us10y_chg<-0.05: score+=3
    elif us10y_chg>0.05: score-=3
    if vix>18: score+=2
    if score>=5:
        action="🟢 BUY"; sl=gold-7.5; tp=gold+12
    elif score<=-5:
        action="🔴 SELL"; sl=gold+7.5; tp=gold-12
    else:
        action="⏸️ WAIT"; sl=tp=gold
    return gold, dxy, vix, score, action, sl, tp

def main():
    print("🏦 AUTO BOT V4 خدام...")
    send_msg("🏦 *V4 AUTO بدا* - كيدخل ويخرج بوحدو ✅")
    while True:
        gold, dxy, vix, score, action, sl, tp = analyze()
        stats = get_stats()
        open_trade = load_json(FILE_OPEN, None)

        # 1. إلا كاينة صفقة مفتوحة - قلب واش ضربات SL/TP
        if open_trade:
            entry = open_trade['entry']
            # حساب P&L حي
            if "BUY" in open_trade['action']:
                if gold <= open_trade['sl']: # ضرب SL
                    pnl = (gold - entry) * (LOT_SIZE*100)
                    close_reason = "🔴 SL"
                elif gold >= open_trade['tp']: # ضرب TP
                    pnl = (gold - entry) * (LOT_SIZE*100)
                    close_reason = "🟢 TP"
                else:
                    close_reason = None
            else: # SELL
                if gold >= open_trade['sl']:
                    pnl = (entry - gold) * (LOT_SIZE*100)
                    close_reason = "🔴 SL"
                elif gold <= open_trade['tp']:
                    pnl = (entry - gold) * (LOT_SIZE*100)
                    close_reason = "🟢 TP"
                else:
                    close_reason = None
            
            if close_reason: # تسد الصفقة
                trades = load_json(FILE_TRADES, [])
                trades.append({"entry":entry,"exit":gold,"action":open_trade['action'],"pnl":round(pnl,2),"reason":close_reason,"time":str(datetime.now())})
                save_json(FILE_TRADES, trades)
                os.remove(FILE_OPEN) if os.path.exists(FILE_OPEN) else None
                chart = create_chart(gold, sl, tp, f"{close_reason} CLOSE", get_stats(), None)
                send_photo(f"""
*🔒 صفقة تسدات {close_reason}*

{open_trade['action']} {entry:.2f} → {gold:.2f}
*P&L:* {pnl:+.2f}$ 
*المجموع اليوم:* ${get_stats()['pnl']:.2f}
*الصفقات:* {get_stats()['total']} (W{get_stats()['win']}/L{get_stats()['loss']})
""", chart)
                print(f"تسكرات: {pnl}$")
            else:
                # تحديث الشارت كل 5 دقائق والصفقة مفتوحة
                if int(time.time()) % 300 < 35:
                    chart = create_chart(gold, sl, tp, action, stats, open_trade)
                    live = (gold-entry)*(LOT_SIZE*100) if "BUY" in open_trade['action'] else (entry-gold)*(LOT_SIZE*100)
                    send_photo(f"📈 *صفقة مفتوحة* | P&L الحي: {live:+.2f}$ | GOLD {gold:.2f}", chart)

        # 2. إلا ماكايناش صفقة مفتوحة وكاينة إشارة قوية → حل صفقة جديدة
        else:
            if abs(score)>=5:
                new_trade = {"entry":gold,"sl":sl,"tp":tp,"action":action,"time":str(datetime.now())}
                save_json(FILE_OPEN, new_trade)
                chart = create_chart(gold, sl, tp, action, stats, new_trade)
                send_photo(f"""
🚀 *دخول جديد AUTO*

🎯 {action}
📍 دخول: {gold:.2f}
🛑 SL: {sl:.2f}
✅ TP: {tp:.2f}
Lots: {LOT_SIZE}

*STATS:* ${stats['pnl']} | {stats['total']} صفقة
""", chart)
                print(f"تحلات صفقة: {action} @ {gold}")

        print(f"{datetime.now().strftime('%H:%M:%S')} GOLD {gold:.2f} | Score {score} | Stats {stats['pnl']}$ | Open: {bool(open_trade)}")
        time.sleep(35) # كيشوف كل 35 ثانية

if __name__=="__main__":
    main()
