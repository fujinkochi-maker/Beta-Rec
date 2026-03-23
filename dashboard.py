from flask import Flask,session,redirect,request,jsonify,send_from_directory
import requests as req
import database as db
import os

app=Flask(__name__,static_folder="static")
app.secret_key=os.getenv("DASHBOARD_SECRET","boxing-beta-secret")
DISCORD_CLIENT_ID=os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET=os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI=os.getenv("DISCORD_REDIRECT_URI","http://localhost:5000/auth/callback")
ADMIN_IDS=[x.strip() for x in os.getenv("ADMIN_DISCORD_IDS","").split(",") if x.strip()]
MOD_IDS=[x.strip() for x in os.getenv("MOD_DISCORD_IDS","").split(",") if x.strip()]

def is_admin(): u=session.get("user"); return bool(u and u["id"] in ADMIN_IDS)
def is_mod():   u=session.get("user"); return bool(u and (u["id"] in ADMIN_IDS or u["id"] in MOD_IDS))

def ra(f):
    from functools import wraps
    @wraps(f)
    def w(*a,**k):
        if not session.get("user"): return jsonify({"error":"Unauthorized"}),401
        return f(*a,**k)
    return w

def rm(f):
    from functools import wraps
    @wraps(f)
    def w(*a,**k):
        if not is_mod(): return jsonify({"error":"Forbidden"}),403
        return f(*a,**k)
    return w

@app.route("/")
@app.route("/dashboard")
def index(): return send_from_directory("static","index.html")

@app.route("/auth/discord")
def auth_discord():
    p=f"client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(f"https://discord.com/api/oauth2/authorize?{p}")

@app.route("/auth/callback")
def auth_callback():
    code=request.args.get("code")
    if not code: return redirect("/?error=no_code")
    try:
        t=req.post("https://discord.com/api/oauth2/token",data={
            "client_id":DISCORD_CLIENT_ID,"client_secret":DISCORD_CLIENT_SECRET,
            "grant_type":"authorization_code","code":code,"redirect_uri":DISCORD_REDIRECT_URI})
        u=req.get("https://discord.com/api/users/@me",headers={"Authorization":f"Bearer {t.json()['access_token']}"})
        session["user"]=u.json()
        return redirect("/dashboard")
    except: return redirect("/?error=oauth_failed")

@app.route("/auth/logout")
def auth_logout(): session.clear(); return redirect("/")

# ── Public API ────────────────────────────────────────────
@app.route("/api/me")
def api_me():
    u=session.get("user")
    if not u: return jsonify({"user":None,"fighter":None,"isAdmin":False,"isMod":False})
    uid = str(u["id"])
    # Reload admin/mod lists fresh each request so .env changes take effect
    admin_ids = [x.strip() for x in os.getenv("ADMIN_DISCORD_IDS","").split(",") if x.strip()]
    mod_ids   = [x.strip() for x in os.getenv("ADMIN_DISCORD_IDS","").split(",") if x.strip()] +                 [x.strip() for x in os.getenv("MOD_DISCORD_IDS","").split(",")   if x.strip()]
    is_adm = uid in admin_ids
    is_md  = uid in mod_ids
    fighter = db.get_fighter_by_discord(uid)
    if fighter:
        fighter["belts"] = db.get_fighter_belts(fighter["fighter_name"])
        fighter["rank"]  = db.get_fighter_rank(uid, fighter.get("division"))
    print(f"[API/ME] uid={uid} isAdmin={is_adm} fighter={fighter['fighter_name'] if fighter else None} admin_ids={admin_ids}")
    return jsonify({"user":u,"fighter":fighter,"isAdmin":is_adm,"isMod":is_md})

@app.route("/api/search")
def api_search():
    q=request.args.get("q","").strip()
    if not q: return jsonify([])
    results=db.search_fighters(q)
    for f in results:
        f["belts"]=db.get_fighter_belts(f["fighter_name"])
    return jsonify(results)

@app.route("/api/fighter/<name>")
def api_fighter(name):
    f=db.get_fighter_by_name(name)
    if not f: return jsonify({"error":"Not found"}),404
    f["belts"]=db.get_fighter_belts(f["fighter_name"])
    f["rank"]=db.get_fighter_rank(str(f.get("discord_id","")),f.get("division"))
    f["matches"]=db.get_match_history(f["fighter_name"],20)
    return jsonify(f)

@app.route("/api/leaderboard")
def api_leaderboard():
    division=request.args.get("division")
    fighters=db.get_leaderboard(50,division)
    for f in fighters:
        f["belts"]=db.get_fighter_belts(f["fighter_name"])
        f["rank"]=db.get_fighter_rank(str(f.get("discord_id","")),f.get("division"))
    return jsonify(fighters)

@app.route("/api/rankings")
def api_rankings():
    return jsonify(db.get_rankings(request.args.get("division"),50))

@app.route("/api/matches")
def api_matches():
    return jsonify(db.get_match_history(request.args.get("filter"),50,request.args.get("division")))

@app.route("/api/championships")
def api_championships(): return jsonify(db.get_all_championships())

@app.route("/api/divisions")
def api_divisions(): return jsonify(db.DIVISIONS)

@app.route("/api/stats")
def api_stats():
    fighters=db.get_all_fighters(); matches=db.get_all_matches(9999)
    return jsonify({"total_fighters":len(fighters),"total_matches":len(matches),
        "total_kos":sum(m.get("is_ko",0) for m in matches),
        "verified":sum(1 for f in fighters if f.get("is_verified"))})

# ── Mod/Admin API ─────────────────────────────────────────
@app.route("/api/admin/register",methods=["POST"])
@rm
def admin_register():
    d=request.get_json()
    discord_id=d.get("discord_id","").strip()
    fighter_name=d.get("fighter_name","").strip()
    if not discord_id or not fighter_name: return jsonify({"error":"Missing fields"}),400
    db.register_fighter(fighter_name,discord_id,d.get("division","Heavyweight"),
        d.get("nickname",""),d.get("country",""))
    u = session.get("user",{})
    db.log_activity(u.get("username","admin"), "register", fighter_name)
    return jsonify({"success":True})

@app.route("/api/admin/fighters")
@rm
def admin_fighters(): return jsonify(db.get_all_fighters())

@app.route("/api/admin/matches")
@rm
def admin_matches(): return jsonify(db.get_all_matches(200))

@app.route("/api/admin/addmatch",methods=["POST"])
@rm
def admin_addmatch():
    d=request.get_json()
    w,l,m=d.get("winner","").strip(),d.get("loser","").strip(),d.get("method","").strip()
    if not w or not l or not m: return jsonify({"error":"Missing fields"}),400
    db.add_match(w,l,m,d.get("round"),m in("KO","TKO"),d.get("division","Heavyweight"))
    u = session.get("user",{})
    db.log_activity(u.get("username","admin"), "addmatch", f"{w} def. {l} by {m}")
    return jsonify({"success":True})

@app.route("/api/admin/match/<int:mid>",methods=["DELETE"])
@rm
def admin_delete_match(mid): db.delete_match(mid); return jsonify({"success":True})

@app.route("/api/admin/fighter/<name>",methods=["PATCH"])
@rm
def admin_update_fighter(name):
    d=request.get_json(); f=db.get_fighter_by_name(name)
    if not f: return jsonify({"error":"Not found"}),404
    if any(k in d for k in ["wins","losses","draws","kos"]):
        db.manual_update_record(name,d.get("wins",f["wins"]),d.get("losses",f["losses"]),
            d.get("draws",f["draws"]),d.get("kos",f["kos"]),d.get("division"))
    if "nickname" in d or "country" in d or "division" in d or "fighter_name" in d:
        db.update_fighter_info(f["discord_id"],d.get("fighter_name"),d.get("nickname"),
            d.get("country"),d.get("division"))
    return jsonify({"success":True})

@app.route("/api/admin/fighter/<name>",methods=["DELETE"])
@rm
def admin_delete_fighter(name): db.delete_fighter(name); return jsonify({"success":True})

@app.route("/api/admin/reset/<name>",methods=["POST"])
@rm
def admin_reset(name): db.reset_record(name); return jsonify({"success":True})

@app.route("/api/admin/champion",methods=["POST"])
@rm
def admin_set_champion():
    d=request.get_json(); db.set_champion(d["belt"],d["division"],d["fighter"]); return jsonify({"success":True})

@app.route("/api/admin/champion",methods=["DELETE"])
@rm
def admin_remove_champion():
    d=request.get_json(); db.remove_champion(d["belt"],d["division"]); return jsonify({"success":True})


@app.route("/api/fighters/export")
def export_fighters():
    fighters = db.get_all_fighters()
    for f in fighters:
        f["belts"] = db.get_fighter_belts(f.get("fighter_name",""))
        f["rank"] = db.get_fighter_rank(str(f.get("discord_id","")), f.get("division"))
    from flask import Response
    import json
    return Response(
        json.dumps({"fighters": fighters, "total": len(fighters)}, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=betarec_fighters.json"}
    )

@app.route("/api/fighters/all")
def all_fighters_list():
    fighters = db.get_all_fighters()
    return jsonify([{"id": f["id"], "fighter_name": f["fighter_name"],
                     "nickname": f.get("nickname",""), "division": f.get("division",""),
                     "wins": f["wins"], "losses": f["losses"], "draws": f["draws"],
                     "kos": f["kos"], "discord_id": f.get("discord_id",""),
                     "country": f.get("country","")} for f in fighters])


# ── Fight Cards ───────────────────────────────────────────
@app.route("/api/fightcards")
def api_fightcards():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM fight_cards ORDER BY fight_date ASC").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/fightcards", methods=["POST"])
@rm
def api_add_fightcard():
    d = request.get_json()
    with db.get_conn() as conn:
        conn.execute("INSERT INTO fight_cards (title, fighter1, fighter2, division, fight_date, event_name, status) VALUES (?,?,?,?,?,?,?)",
            (d.get("title",""), d.get("fighter1",""), d.get("fighter2",""), d.get("division","Heavyweight"),
             d.get("fight_date",""), d.get("event_name",""), "upcoming"))
    db.log_activity(session["user"]["username"], "add_fightcard", f"{d.get('fighter1')} vs {d.get('fighter2')}")
    return jsonify({"success": True})

@app.route("/api/fightcards/<int:card_id>", methods=["DELETE"])
@rm
def api_delete_fightcard(card_id):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM fight_cards WHERE id=?", (card_id,))
    db.log_activity(session["user"]["username"], "delete_fightcard", f"ID {card_id}")
    return jsonify({"success": True})

@app.route("/api/fightcards/<int:card_id>", methods=["PATCH"])
@rm
def api_update_fightcard(card_id):
    d = request.get_json()
    with db.get_conn() as conn:
        conn.execute("UPDATE fight_cards SET title=?,fighter1=?,fighter2=?,division=?,fight_date=?,event_name=?,status=? WHERE id=?",
            (d.get("title",""), d.get("fighter1",""), d.get("fighter2",""), d.get("division","Heavyweight"),
             d.get("fight_date",""), d.get("event_name",""), d.get("status","upcoming"), card_id))
    return jsonify({"success": True})

# ── Activity Log ──────────────────────────────────────────
@app.route("/api/admin/activity")
@rm
def api_activity():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 100").fetchall()
        return jsonify([dict(r) for r in rows])

# ── Bulk Import ───────────────────────────────────────────
@app.route("/api/admin/bulk_import", methods=["POST"])
@rm
def api_bulk_import():
    d = request.get_json()
    fighters = d.get("fighters", [])
    results = {"success": 0, "failed": 0, "errors": []}
    for f in fighters:
        try:
            name = f.get("fighter_name","").strip()
            discord_id = str(f.get("discord_id","")).strip()
            if not name: raise ValueError("Missing fighter_name")
            db.register_fighter(name, discord_id or None,
                f.get("division","Heavyweight"), f.get("nickname",""), f.get("country",""))
            if f.get("wins") or f.get("losses"):
                db.manual_update_record(discord_id or name,
                    int(f.get("wins",0)), int(f.get("losses",0)),
                    int(f.get("draws",0)), int(f.get("kos",0)), f.get("division"))
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{f.get('fighter_name','?')}: {str(e)}")
    db.log_activity(session["user"]["username"], "bulk_import", f"{results['success']} fighters imported")
    return jsonify(results)

def run_dashboard():
    port=int(os.getenv("PORT",5000))
    print(f"✅ Dashboard at http://localhost:{port}")
    app.run(host="0.0.0.0",port=port,debug=False,use_reloader=False)
