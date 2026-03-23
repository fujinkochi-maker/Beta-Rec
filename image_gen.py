from PIL import Image, ImageDraw, ImageFont
import io, os, math

BG=(12,12,14);BG2=(19,19,22);BG3=(26,26,31);BG4=(34,34,40)
BORDER=(44,44,53);RED=(232,0,30);GOLD=(245,196,0);GREEN=(0,230,118)
BLUE=(33,150,243);ORANGE=(255,140,0);MUTED=(136,136,160);DIM=(85,85,102)
WHITE=(245,245,247);SILVER=(192,192,192);BRONZE=(205,127,50)
BELT_COLORS={"WBC":(0,176,80),"WBO":(0,112,192),"IBF":(192,0,0),"WBA":(255,140,0)}

COUNTRY_FLAGS={
    "PH":"🇵🇭","US":"🇺🇸","UK":"🇬🇧","MX":"🇲🇽","PH":"🇵🇭",
    "JP":"🇯🇵","AU":"🇦🇺","CA":"🇨🇦","NG":"🇳🇬","UA":"🇺🇦",
    "KZ":"🇰🇿","AR":"🇦🇷","CU":"🇨🇺","TH":"🇹🇭","ID":"🇮🇩",
}

def load_font(size, bold=False):
    candidates = (["C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/calibrib.ttf"] if bold
                  else ["C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/calibri.ttf","C:/Windows/Fonts/segoeui.ttf"])
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def load_impact(size):
    for p in ["C:/Windows/Fonts/Impact.ttf","C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def rr(draw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def grad(img, x1, y1, x2, y2, c1, c2, vertical=False):
    draw = ImageDraw.Draw(img)
    span = y2-y1 if vertical else x2-x1
    for i in range(span):
        t = i/max(span-1,1)
        c = tuple(int(c1[j]+(c2[j]-c1[j])*t) for j in range(3))
        if vertical: draw.line([(x1,y1+i),(x2,y1+i)], fill=c)
        else: draw.line([(x1+i,y1),(x1+i,y2)], fill=c)

def to_bytes(img):
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0); return buf

def draw_win_bar(img, x, y, w, h, pct, color1=RED, color2=GOLD):
    draw=ImageDraw.Draw(img)
    draw.rounded_rectangle([x,y,x+w,y+h], radius=h//2, fill=BG4)
    fw=int(w*pct/100)
    if fw>h: grad(img, x, y, x+fw, y+h, color1, color2)

def fighter_display_name(f):
    nick = f.get("nickname","")
    name = f.get("fighter_name") or f.get("roblox_username","?")
    return f'"{nick}" {name}' if nick else name

def country_text(f):
    c = (f.get("country") or "").upper()
    return c if c else ""

# ═══════════════════════════════════════════
# PROFILE CARD
# ═══════════════════════════════════════════
def generate_profile_card(fighter, belts=None, matches=None, rank=None):
    W,H=900,720
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)
    belts=belts or []; matches=matches or []

    wins=fighter.get("wins",0); losses=fighter.get("losses",0)
    draws=fighter.get("draws",0); kos=fighter.get("kos",0)
    total=wins+losses
    win_pct=round((wins/total)*100) if total>0 else 0
    ko_pct=round((kos/wins)*100) if wins>0 else 0
    division=fighter.get("division","Heavyweight")
    dname=fighter_display_name(fighter)
    country=country_text(fighter)

    # Header
    grad(img,0,0,W,90,BG2,BG3)
    grad(img,0,0,W,4,RED,(180,0,20))
    draw.line([(0,90),(W,90)],fill=BORDER,width=1)
    grad(img,0,0,6,H,RED,(50,0,10))

    draw.text((24,14),"BOXING BETA",font=load_font(11,True),fill=RED)
    draw.text((24,30),"BOXREC",font=load_impact(32),fill=WHITE)

    # Country + Division tag top right
    info_parts=[]
    if country: info_parts.append(country)
    info_parts.append(division.upper())
    tag=" · ".join(info_parts)
    tw=int(draw.textlength(tag,font=load_font(12,True)))+20
    rr(draw,[W-tw-16,18,W-16,42],4,fill=BG4)
    draw.text((W-tw-8,22),tag,font=load_font(12,True),fill=MUTED)
    if rank: draw.text((W-60,52),f"#{rank}",font=load_impact(22),fill=GOLD)

    # Name
    nf=load_impact(52) if len(dname)<=16 else load_impact(36) if len(dname)<=24 else load_impact(26)
    draw.text((24,100),dname.upper(),font=nf,fill=WHITE)

    # Belts
    bx,by=24,162
    for b in belts:
        bc=BELT_COLORS.get(b.get("belt",""),GOLD)
        bn=b.get("belt","")
        bw=int(draw.textlength(bn,font=load_font(11,True)))+20
        rr(draw,[bx,by,bx+bw,by+22],4,fill=tuple(v//6 for v in bc),outline=bc,width=1)
        draw.text((bx+10,by+4),bn,font=load_font(11,True),fill=bc)
        bx+=bw+6

    # BIG RECORD
    ry=198
    fi90=load_impact(90); fi24=load_impact(24); fi60=load_impact(60)
    # W
    draw.text((24,ry),str(wins),font=fi90,fill=GREEN)
    ww=int(draw.textlength(str(wins),font=fi90))
    draw.text((24+ww+6,ry+62),"W",font=fi24,fill=GREEN)
    draw.text((24+ww+28,ry+18),"-",font=fi60,fill=DIM)
    sw=int(draw.textlength("-",font=fi60))
    # L
    lx=24+ww+28+sw+8
    draw.text((lx,ry),str(losses),font=fi90,fill=RED)
    lw=int(draw.textlength(str(losses),font=fi90))
    draw.text((lx+lw+6,ry+62),"L",font=fi24,fill=RED)
    draw.text((lx+lw+28,ry+18),"-",font=fi60,fill=DIM)
    # D
    dx=lx+lw+28+sw+8
    draw.text((dx,ry),str(draws),font=fi90,fill=MUTED)
    draw.text((dx+int(draw.textlength(str(draws),font=fi90))+6,ry+62),"D",font=fi24,fill=MUTED)

    # Stats panel
    px,py=480,100
    rr(draw,[px,py,W-20,H-20],10,fill=BG2,outline=BORDER,width=1)
    draw.text((px+16,py+14),"FIGHTER STATS",font=load_font(11,True),fill=MUTED)
    draw.line([(px+16,py+34),(W-36,py+34)],fill=BORDER,width=1)
    stats=[("KOs",str(kos),ORANGE),("WIN RATE",f"{win_pct}%",GREEN if win_pct>=50 else RED),
           ("KO RATE",f"{ko_pct}%",ORANGE),("TOTAL FIGHTS",str(total),BLUE)]
    sy=py+46
    for label,val,col in stats:
        draw.text((px+16,sy),label,font=load_font(11,True),fill=MUTED)
        draw.text((px+16,sy+16),val,font=load_impact(26),fill=col)
        sy+=56
    draw.text((px+16,sy+8),"WIN RATE",font=load_font(11,True),fill=MUTED)
    bw2=W-px-52
    draw_win_bar(img,px+16,sy+26,bw2,10,win_pct)
    draw.text((px+16,sy+42),f"{win_pct}%",font=load_font(12),fill=MUTED)

    # Recent fights
    fy=335
    draw.text((24,fy),"RECENT FIGHTS",font=load_font(11,True),fill=MUTED)
    draw.line([(24,fy+18),(440,fy+18)],fill=BORDER,width=1)
    fy+=26
    for m in matches[:5]:
        fname=fighter.get("fighter_name","")
        is_win=m.get("winner","").lower()==fname.lower()
        opp=m.get("loser","?") if is_win else m.get("winner","?")
        method=m.get("method","?"); rnd=f" R{m['round']}" if m.get("round") else ""
        rc=GREEN if is_win else RED; rt="WIN" if is_win else "LOSS"
        rw=int(draw.textlength(rt,font=load_font(11,True)))+14
        rr(draw,[24,fy,24+rw,fy+19],3,fill=tuple(v//5 for v in rc),outline=rc,width=1)
        draw.text((31,fy+3),rt,font=load_font(11,True),fill=rc)
        draw.text((24+rw+10,fy+2),f"vs {opp}",font=load_font(14,True),fill=WHITE)
        draw.text((24+rw+10,fy+17),f"{method}{rnd}  ·  {m.get('date','')}",font=load_font(12),fill=MUTED)
        fy+=40
    if not matches: draw.text((24,fy+4),"No fights recorded yet",font=load_font(12),fill=DIM)

    # Graph panel
    graph_y = H - 185
    draw.text((24, graph_y - 18), "PERFORMANCE TREND", font=load_font(11,True), fill=MUTED)
    draw.line([(24, graph_y-4),(440, graph_y-4)], fill=BORDER, width=1)
    if matches and len(matches) >= 2:
        fname = fighter.get("fighter_name","")
        pts = []
        w_c = 0; l_c = 0
        for m in list(reversed(matches[-8:])):
            if m.get("winner","").lower()==fname.lower(): w_c+=1
            else: l_c+=1
            t2 = w_c+l_c
            pts.append(round((w_c/t2)*100) if t2>0 else 50)
        cw2=410; ch2=120; ox2=24; oy2=graph_y+ch2
        for pct in [25,50,75]:
            gy2=oy2-int((pct/100)*ch2)
            draw.line([(ox2,gy2),(ox2+cw2,gy2)],fill=BORDER,width=1)
        coords2=[]
        for i,p in enumerate(pts):
            x2=ox2+int((i/max(len(pts)-1,1))*cw2)
            y2=oy2-int((p/100)*ch2)
            coords2.append((x2,y2))
        if len(coords2)>1:
            for i in range(len(coords2)-1):
                draw.line([coords2[i],coords2[i+1]],fill=RED,width=2)
            for x2,y2 in coords2:
                draw.ellipse([x2-4,y2-4,x2+4,y2+4],fill=RED)
        mid2=oy2-int(0.5*ch2)
        draw.line([(ox2,mid2),(ox2+cw2,mid2)],fill=(100,0,10),width=1)
    else:
        draw.text((24,graph_y+50),"Not enough fight data for graph",font=load_font(12),fill=DIM)

    # Footer
    draw.line([(0,H-30),(W,H-30)],fill=BORDER,width=1)
    draw.text((24,H-20),"BOXING BETA BOXREC  ·  Official Records",font=load_font(11,True),fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# H2H IMAGE
# ═══════════════════════════════════════════
def generate_h2h_image(f1, f2, b1=None, b2=None):
    W,H=900,480
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)
    b1=b1 or []; b2=b2 or []

    # Header
    grad(img,0,0,W,70,BG2,BG3)
    grad(img,0,0,W,4,RED,(180,0,20))
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((W//2-80,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    draw.text((W//2-90,30),"HEAD TO HEAD",font=load_impact(32),fill=WHITE)

    # VS divider
    draw.line([(W//2,70),(W//2,H-30)],fill=BORDER,width=1)
    vsbg=Image.new("RGB",(60,60),BG3)
    vsd=ImageDraw.Draw(vsbg); vsd.ellipse([0,0,59,59],fill=RED)
    vsd.text((12,10),"VS",font=load_impact(24),fill=WHITE)
    img.paste(vsbg,(W//2-30,H//2-60))

    def draw_fighter_side(f, belts, x_start, x_end, align_right=False):
        wins=f.get("wins",0); losses=f.get("losses",0)
        draws=f.get("draws",0); kos=f.get("kos",0)
        total=wins+losses
        win_pct=round((wins/total)*100) if total>0 else 0
        ko_pct=round((kos/wins)*100) if wins>0 else 0
        dname=fighter_display_name(f)
        country=country_text(f)

        cx=x_end-20 if align_right else x_start+20
        anchor="right" if align_right else "left"

        # Name
        nf=load_impact(32) if len(dname)<=14 else load_impact(24)
        nw=int(draw.textlength(dname.upper(),font=nf))
        nx=x_end-20-nw if align_right else x_start+20
        draw.text((nx,82),dname.upper(),font=nf,fill=WHITE)

        # Country + division
        meta=[]
        if country: meta.append(country)
        meta.append(f.get("division","HW"))
        draw.text((nx,122)," · ".join(meta),font=load_font(12,True),fill=MUTED)

        # Belt badges
        bx_pos=nx
        for b in belts[:2]:
            bc=BELT_COLORS.get(b.get("belt",""),GOLD)
            bn=b.get("belt","")
            bw=int(draw.textlength(bn,font=load_font(11,True)))+18
            rr(draw,[bx_pos,142,bx_pos+bw,162],4,fill=tuple(v//6 for v in bc),outline=bc,width=1)
            draw.text((bx_pos+9,145),bn,font=load_font(11,True),fill=bc)
            bx_pos+=bw+6

        # Big record
        rec=f"{wins}-{losses}-{draws}"
        rw2=int(draw.textlength(rec,font=load_impact(52)))
        rx=x_end-20-rw2 if align_right else x_start+20
        draw.text((rx,172),str(wins),font=load_impact(52),fill=GREEN)
        ww=int(draw.textlength(str(wins),font=load_impact(52)))
        draw.text((rx+ww+4,196),"W",font=load_font(14,True),fill=GREEN)
        draw.text((rx+ww+22,180),"-",font=load_impact(36),fill=DIM)
        sw=int(draw.textlength("-",font=load_impact(36)))
        draw.text((rx+ww+22+sw+6,172),str(losses),font=load_impact(52),fill=RED)
        lw2=int(draw.textlength(str(losses),font=load_impact(52)))
        draw.text((rx+ww+22+sw+6+lw2+4,196),"L",font=load_font(14,True),fill=RED)

        # Stats rows
        stats=[
            ("KOs", str(kos), ORANGE),
            ("Win Rate", f"{win_pct}%", GREEN if win_pct>=50 else RED),
            ("KO Rate", f"{ko_pct}%", ORANGE),
            ("Fights", str(total), BLUE),
        ]
        sy=248
        for label,val,col in stats:
            draw.text((x_start+20,sy),label,font=load_font(11,True),fill=MUTED)
            vw=int(draw.textlength(val,font=load_impact(22)))
            vx=x_end-20-vw if align_right else x_start+20
            draw.text((x_start+20,sy+16),val,font=load_impact(22),fill=col)
            sy+=46

        # Win bar
        bar_x=x_start+20; bar_w=x_end-x_start-40
        draw_win_bar(img,bar_x,H-80,bar_w,10,win_pct)
        draw.text((bar_x,H-62),f"{win_pct}% win rate",font=load_font(11,True),fill=MUTED)

    draw_fighter_side(f1, b1, 0, W//2-10)
    draw_fighter_side(f2, b2, W//2+10, W)

    draw.line([(0,H-30),(W,H-30)],fill=BORDER,width=1)
    draw.text((W//2-140,H-20),"BOXING BETA BOXREC  ·  Head to Head",font=load_font(11,True),fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# LEADERBOARD
# ═══════════════════════════════════════════
def generate_leaderboard_image(fighters, division=None, title="TOP FIGHTERS"):
    count=min(len(fighters),10)
    W=880; H=100+count*58+50
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)

    grad(img,0,0,W,70,BG2,BG3)
    grad(img,0,0,W,4,RED,GOLD)
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((20,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    t=f"{title}" + (f"  ·  {division.upper()}" if division else "  ·  ALL DIVISIONS")
    draw.text((20,30),t,font=load_impact(32),fill=WHITE)
    for hdr,hx in [("RANK",20),("FIGHTER",80),("DIV",360),("REC",480),("KOs",580),("WIN%",640)]:
        draw.text((hx,78),hdr,font=load_font(11,True),fill=DIM)
    draw.line([(20,94),(W-20,94)],fill=BORDER,width=1)

    y=102
    for i,f in enumerate(fighters[:10]):
        wins=f.get("wins",0); losses=f.get("losses",0); kos=f.get("kos",0)
        total=wins+losses; win_pct=round((wins/total)*100) if total>0 else 0
        dname=fighter_display_name(f); country=country_text(f)
        row_bg=BG3 if i%2==0 else BG2
        draw.rectangle([0,y,W,y+54],fill=row_bg)

        # Rank
        if i==0: rc,rt=GOLD,"1"
        elif i==1: rc,rt=SILVER,"2"
        elif i==2: rc,rt=BRONZE,"3"
        else: rc,rt=DIM,str(i+1)
        draw.text((30,y+14),rt,font=load_impact(26),fill=rc)

        # Name + country
        nf2=load_impact(20) if len(dname)<=16 else load_font(14,True)
        draw.text((80,y+8),dname,font=nf2,fill=WHITE)
        if country: draw.text((80,y+32),country,font=load_font(11,True),fill=MUTED)

        # Belt badges
        bx2=120 if not country else 140
        for b in f.get("belts",[])[:2]:
            bc=BELT_COLORS.get(b.get("belt",""),GOLD)
            bn=b.get("belt","")
            bww=int(draw.textlength(bn,font=load_font(10,True)))+10
            rr(draw,[bx2,y+30,bx2+bww,y+46],3,fill=tuple(v//6 for v in bc),outline=bc,width=1)
            draw.text((bx2+5,y+32),bn,font=load_font(10,True),fill=bc)
            bx2+=bww+4

        # Division
        div=f.get("division","")[:3].upper()
        draw.text((360,y+16),div,font=load_font(13,True),fill=MUTED)

        # Record
        draw.text((480,y+8),str(wins),font=load_impact(20),fill=GREEN)
        gww=int(draw.textlength(str(wins),font=load_impact(20)))
        draw.text((480+gww+3,y+8),"W",font=load_font(11),fill=GREEN)
        draw.text((480+gww+16,y+8),"-",font=load_font(11),fill=DIM)
        draw.text((480+gww+24,y+8),str(losses),font=load_impact(20),fill=RED)
        lww=int(draw.textlength(str(losses),font=load_impact(20)))
        draw.text((480+gww+24+lww+3,y+8),"L",font=load_font(11),fill=RED)

        # KOs
        draw.text((580,y+8),str(kos),font=load_impact(20),fill=ORANGE)

        # Win bar
        draw_win_bar(img,640,y+10,200,10,win_pct)
        draw.text((640,y+26),f"{win_pct}%",font=load_font(11),fill=MUTED)

        draw.line([(0,y+54),(W,y+54)],fill=BORDER,width=1)
        y+=58

    draw.rectangle([0,H-28,W,H],fill=BG2)
    draw.line([(0,H-28),(W,H-28)],fill=BORDER,width=1)
    draw.text((20,H-20),"BOXING BETA BOXREC  ·  Official Rankings",font=load_font(11,True),fill=DIM)
    return to_bytes(img)


def generate_rankings_image(fighters, division=None):
    return generate_leaderboard_image(fighters, division, title="RANKINGS BY WIN RATE")


# ═══════════════════════════════════════════
# MATCH HISTORY
# ═══════════════════════════════════════════
def generate_matchhistory_image(matches, filter_name=None, division=None):
    count=min(len(matches),10)
    W=880; H=100+count*54+40
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)

    grad(img,0,0,W,70,BG2,BG3)
    grad(img,0,0,W,4,RED,GOLD)
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((20,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    title=(f"FIGHT HISTORY  ·  {filter_name.upper()}" if filter_name else
           f"MATCH HISTORY  ·  {division.upper()}" if division else "RECENT MATCH HISTORY")
    draw.text((20,30),title,font=load_impact(28),fill=WHITE)
    for hdr,hx in [("#",20),("WINNER",50),("LOSER",320),("METHOD",580),("DATE",700)]:
        draw.text((hx,78),hdr,font=load_font(11,True),fill=DIM)
    draw.line([(20,94),(W-20,94)],fill=BORDER,width=1)

    y=102
    for i,m in enumerate(matches[:10]):
        row_bg=BG3 if i%2==0 else BG2
        draw.rectangle([0,y,W,y+50],fill=row_bg)
        draw.text((24,y+14),str(i+1),font=load_font(11),fill=DIM)
        draw.text((50,y+8),m.get("winner","?"),font=load_impact(20),fill=GREEN)
        draw.text((50,y+30),m.get("division",""),font=load_font(11),fill=MUTED)
        draw.text((294,y+14),"def.",font=load_font(11),fill=DIM)
        draw.text((320,y+8),m.get("loser","?"),font=load_impact(20),fill=RED)
        method=m.get("method","?"); rnd=f" R{m['round']}" if m.get("round") else ""
        mc=RED if method=="KO" else ORANGE if method=="TKO" else BLUE
        mw=int(draw.textlength(method+rnd,font=load_font(11,True)))+16
        rr(draw,[580,y+8,580+mw,y+26],3,fill=tuple(v//6 for v in mc),outline=mc,width=1)
        draw.text((588,y+10),method+rnd,font=load_font(11,True),fill=mc)
        draw.text((700,y+14),m.get("date",""),font=load_font(11),fill=MUTED)
        draw.line([(0,y+50),(W,y+50)],fill=BORDER,width=1)
        y+=54

    draw.rectangle([0,H-28,W,H],fill=BG2)
    draw.line([(0,H-28),(W,H-28)],fill=BORDER,width=1)
    draw.text((20,H-20),"BOXING BETA BOXREC  ·  Official Match Records",font=load_font(11,True),fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# CHAMPIONSHIPS
# ═══════════════════════════════════════════
def generate_championships_image(championships):
    by_div={}
    for c in championships:
        if c.get("champion"):
            by_div.setdefault(c["division"],{})[c["belt"]]=c
    if not by_div:
        W,H=880,160; img=Image.new("RGB",(W,H),BG)
        draw=ImageDraw.Draw(img)
        grad(img,0,0,W,4,RED,GOLD)
        draw.text((W//2-140,H//2-14),"NO CHAMPIONS ASSIGNED YET",font=load_impact(28),fill=DIM)
        return to_bytes(img)
    BORDER_BELTS=["WBC","WBO","IBF","WBA"]
    divs=list(by_div.keys()); cols=2
    rows=math.ceil(len(divs)/cols)
    cw,ch=420,130; pad=14
    W=cols*cw+(cols+1)*pad; H=90+rows*(ch+pad)+pad+28
    img=Image.new("RGB",(W,H),BG); draw=ImageDraw.Draw(img)
    grad(img,0,0,W,70,BG2,BG3)
    grad(img,0,0,W,4,RED,GOLD)
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((20,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    draw.text((20,28),"WORLD CHAMPIONSHIPS",font=load_impact(30),fill=WHITE)
    draw.text((W-200,38),"WBC · WBO · IBF · WBA",font=load_font(11,True),fill=MUTED)
    for idx,div in enumerate(divs):
        col=idx%cols; row=idx//cols
        cx=pad+col*(cw+pad); cy=80+row*(ch+pad)
        rr(draw,[cx,cy,cx+cw,cy+ch],8,fill=BG2,outline=BORDER,width=1)
        draw.text((cx+12,cy+10),div.upper(),font=load_impact(16),fill=WHITE)
        draw.line([(cx+12,cy+32),(cx+cw-12,cy+32)],fill=BORDER,width=1)
        for bi,belt in enumerate(BORDER_BELTS):
            bx=cx+12+(bi%2)*200; by2=cy+40+(bi//2)*36
            bc=BELT_COLORS[belt]
            draw.ellipse([bx,by2+5,bx+10,by2+15],fill=bc)
            draw.text((bx+15,by2+2),belt,font=load_font(10,True),fill=bc)
            cd=by_div[div].get(belt)
            draw.text((bx+15,by2+14),cd["champion"] if cd else "Vacant",
                font=load_font(11),fill=WHITE if cd else DIM)
    fy=H-28
    draw.rectangle([0,fy,W,H],fill=BG2)
    draw.line([(0,fy),(W,fy)],fill=BORDER,width=1)
    draw.text((20,fy+8),"BOXING BETA BOXREC  ·  World Title Records",font=load_font(11,True),fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# EMPTY STATE IMAGES
# ═══════════════════════════════════════════
def generate_empty_image(title, subtitle, icon_text="?"):
    W,H=880,300
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)
    grad(img,0,0,W,4,RED,GOLD)
    grad(img,0,0,W,70,BG2,BG3)
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((20,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    draw.text((20,30),title,font=load_impact(32),fill=WHITE)
    # Big icon circle
    cx,cy,r=W//2,165,55
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=BG3,outline=BORDER,width=2)
    iw=int(draw.textlength(icon_text,font=load_impact(48)))
    draw.text((cx-iw//2,cy-28),icon_text,font=load_impact(48),fill=DIM)
    # Subtitle
    sw=int(draw.textlength(subtitle,font=load_font(16,True)))
    draw.text((W//2-sw//2,cy+r+16),subtitle,font=load_font(16,True),fill=MUTED)
    draw.line([(0,H-28),(W,H-28)],fill=BORDER,width=1)
    draw.rectangle([0,H-28,W,H],fill=BG2)
    draw.text((20,H-20),"BOXING BETA BOXREC  ·  Official Records",font=load_font(11,True),fill=DIM)
    return to_bytes(img)

def generate_empty_leaderboard():
    return generate_empty_image("TOP FIGHTERS","No fighters on the leaderboard yet","0")

def generate_empty_rankings():
    return generate_empty_image("RANKINGS","No fighters ranked yet","?")

def generate_empty_championships():
    return generate_empty_image("WORLD CHAMPIONSHIPS","No champions have been crowned yet","0")

def generate_empty_matchhistory():
    return generate_empty_image("MATCH HISTORY","No matches recorded yet","0")

def generate_not_registered():
    return generate_empty_image("FIGHTER NOT FOUND","This fighter is not registered in the system","X")


# ═══════════════════════════════════════════
# PROFILE WITH GRAPH
# ═══════════════════════════════════════════
def generate_profile_graph(fighter, matches):
    """Generates a win/loss trend graph for the profile."""
    W,H=460,160
    img=Image.new("RGB",(W,H),BG2)
    draw=ImageDraw.Draw(img)
    rr(draw,[0,0,W,H],8,fill=BG2,outline=BORDER,width=1)
    draw.text((12,10),"PERFORMANCE TREND",font=load_font(10,True),fill=MUTED)

    if not matches or len(matches)<2:
        tw=int(draw.textlength("Not enough data",font=load_font(12)))
        draw.text((W//2-tw//2,H//2-8),"Not enough data",font=load_font(12),fill=DIM)
        return to_bytes(img)

    fname=fighter.get("fighter_name","")
    # Build running record from oldest to newest
    pts=[]
    w_count=0; l_count=0
    ordered=list(reversed(matches[-10:]))
    for m in ordered:
        if m.get("winner","").lower()==fname.lower(): w_count+=1
        else: l_count+=1
        total=w_count+l_count
        pts.append(round((w_count/total)*100) if total>0 else 50)

    # Draw grid lines
    for pct in [25,50,75,100]:
        gy=int(H-30-((pct/100)*(H-50)))
        draw.line([(30,gy),(W-10,gy)],fill=BORDER,width=1)
        draw.text((2,gy-6),str(pct),font=load_font(9),fill=DIM)

    # Draw line
    chart_w=W-40; chart_h=H-50; ox=30; oy=H-30
    coords=[]
    for i,p in enumerate(pts):
        x=ox+int((i/(max(len(pts)-1,1)))*chart_w)
        y=oy-int((p/100)*chart_h)
        coords.append((x,y))

    # Fill under line
    if len(coords)>1:
        poly=coords+[(coords[-1][0],oy),(coords[0][0],oy)]
        draw.polygon(poly,fill=(232,0,30,30))
        for i in range(len(coords)-1):
            draw.line([coords[i],coords[i+1]],fill=RED,width=2)
        for x,y in coords:
            draw.ellipse([x-3,y-3,x+3,y+3],fill=RED)

    # 50% line highlight
    mid_y=oy-int(0.5*chart_h)
    draw.line([(30,mid_y),(W-10,mid_y)],fill=(232,0,30,80),width=1)

    return to_bytes(img)


# ═══════════════════════════════════════════
# EMPTY STATE IMAGES
# ═══════════════════════════════════════════
def generate_empty_image(title, subtitle, icon_char="?"):
    W,H=860,280
    img=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(img)
    grad(img,0,0,W,70,BG2,BG3)
    grad(img,0,0,W,4,RED,GOLD)
    draw.line([(0,70),(W,70)],fill=BORDER,width=1)
    draw.text((20,14),"BOXING BETA BOXREC",font=load_font(11,True),fill=RED)
    draw.text((20,30),title,font=load_impact(30),fill=WHITE)
    # Circle icon
    cx,cy,r=W//2,155,50
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=BG3,outline=BORDER,width=2)
    iw=int(draw.textlength(icon_char,font=load_impact(40)))
    draw.text((cx-iw//2,cy-24),icon_char,font=load_impact(40),fill=DIM)
    # Subtitle
    sw=int(draw.textlength(subtitle,font=load_font(16,True)))
    draw.text((W//2-sw//2,210),subtitle,font=load_font(16,True),fill=MUTED)
    sw2=int(draw.textlength("Check back later or ask an admin to add data.",font=load_font(13)))
    draw.text((W//2-sw2//2,234),"Check back later or ask an admin to add data.",font=load_font(13),fill=DIM)
    draw.rectangle([0,H-28,W,H],fill=BG2)
    draw.line([(0,H-28),(W,H-28)],fill=BORDER,width=1)
    draw.text((20,H-20),"BOXING BETA BOXREC  ·  Official Records",font=load_font(11,True),fill=DIM)
    return to_bytes(img)

def generate_empty_leaderboard(): return generate_empty_image("TOP FIGHTERS","No fighters on the leaderboard yet.","0")
def generate_empty_rankings():    return generate_empty_image("RANKINGS","No fighters ranked yet.","#")
def generate_empty_championships(): return generate_empty_image("WORLD CHAMPIONSHIPS","No champions have been crowned yet.","?")
def generate_empty_matchhistory(): return generate_empty_image("MATCH HISTORY","No matches have been recorded yet.","X")
def generate_empty_profile():     return generate_empty_image("FIGHTER PROFILE","This fighter is not registered yet.","?")
def generate_not_registered():    return generate_empty_image("NOT REGISTERED","You are not registered as a fighter yet.","!")


# ═══════════════════════════════════════════
# PROFILE WITH GRAPH
# ═══════════════════════════════════════════
def generate_profile_graph(fighter, matches):
    """Generate a win/loss trend graph for the profile."""
    W,H=860,200
    img=Image.new("RGB",(W,H),BG2)
    draw=ImageDraw.Draw(img)
    draw.rectangle([0,0,W,H],fill=BG2)
    draw.text((20,12),"FIGHT HISTORY TREND",font=load_font(11,True),fill=MUTED)
    draw.line([(20,32),(W-20,32)],fill=BORDER,width=1)

    if not matches:
        draw.text((W//2-80,H//2-8),"No fight history yet",font=load_font(14),fill=DIM)
        return to_bytes(img)

    fname=(fighter.get("fighter_name") or "").lower()
    # Build cumulative W/L data
    results=[]
    for m in reversed(matches):
        results.append(1 if m.get("winner","").lower()==fname else 0)

    n=len(results); pad_l=40; pad_r=20; pad_t=44; pad_b=30
    gw=W-pad_l-pad_r; gh=H-pad_t-pad_b
    # Draw grid lines
    for i in range(3):
        gy=pad_t+int(gh*i/2)
        draw.line([(pad_l,gy),(W-pad_r,gy)],fill=BORDER,width=1)

    # Plot points
    if n==1:
        x=pad_l+gw//2
        y=pad_t+gh//2
        col=GREEN if results[0] else RED
        draw.ellipse([x-5,y-5,x+5,y+5],fill=col)
    else:
        pts=[]
        for i,r in enumerate(results):
            x=pad_l+int(i/(n-1)*gw)
            y=pad_t+gh-int(r*gh*0.7)-int(gh*0.15)
            pts.append((x,y,r))
        # Draw connecting lines
        for i in range(len(pts)-1):
            x1,y1,_=pts[i]; x2,y2,_=pts[i+1]
            mid_col=GREEN if pts[i+1][2] else RED
            draw.line([(x1,y1),(x2,y2)],fill=mid_col,width=2)
        # Draw dots
        for x,y,r in pts:
            col=GREEN if r else RED
            draw.ellipse([x-5,y-5,x+5,y+5],fill=col)
            draw.ellipse([x-3,y-3,x+3,y+3],fill=BG2)
            draw.ellipse([x-2,y-2,x+2,y+2],fill=col)

    # Legend
    draw.ellipse([W-120,14,W-110,24],fill=GREEN)
    draw.text((W-106,13),"Win",font=load_font(11,True),fill=GREEN)
    draw.ellipse([W-70,14,W-60,24],fill=RED)
    draw.text((W-56,13),"Loss",font=load_font(11,True),fill=RED)

    return to_bytes(img)


# ═══════════════════════════════════════════
# MATCH LOGGED IMAGE
# ═══════════════════════════════════════════
def generate_match_logged(winner_name, loser_name, method, round_num, division,
                           winner_record=None, loser_record=None, logged_by="Admin"):
    W, H = 860, 300
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    grad(img, 0, 0, W, H, BG2, BG3)
    grad(img, 0, 0, W, 4, RED, GOLD)
    draw.line([(0, H-32), (W, H-32)], fill=BORDER, width=1)

    # Header
    draw.text((20, 14), "BOXING BETA BOXREC", font=load_font(11, True), fill=RED)
    draw.text((20, 28), "MATCH RESULT", font=load_impact(34), fill=WHITE)
    draw.text((W-160, 22), division.upper(), font=load_font(12, True), fill=MUTED)

    # Divider line
    draw.line([(20, 72), (W-20, 72)], fill=BORDER, width=1)

    # Winner side
    wx = 60
    draw.text((wx, 90), "WINNER", font=load_font(11, True), fill=GREEN)
    nf = load_impact(46) if len(winner_name) <= 14 else load_impact(32)
    draw.text((wx, 108), winner_name.upper(), font=nf, fill=GREEN)
    if winner_record:
        wr = f"{winner_record['wins']}W-{winner_record['losses']}L"
        draw.text((wx, 162), wr, font=load_font(14, True), fill=MUTED)

    # VS badge center
    cx = W // 2
    draw.ellipse([cx-28, 110, cx+28, 166], fill=RED)
    draw.text((cx-14, 122), "def.", font=load_font(13, True), fill=WHITE)

    # Loser side
    lx = W - 60
    draw.text((lx - int(draw.textlength("LOSER", font=load_font(11, True))), 90),
              "LOSER", font=load_font(11, True), fill=RED)
    lf = load_impact(46) if len(loser_name) <= 14 else load_impact(32)
    lw2 = int(draw.textlength(loser_name.upper(), font=lf))
    draw.text((lx - lw2, 108), loser_name.upper(), font=lf, fill=RED)
    if loser_record:
        lr = f"{loser_record['wins']}W-{loser_record['losses']}L"
        lrw = int(draw.textlength(lr, font=load_font(14, True)))
        draw.text((lx - lrw, 162), lr, font=load_font(14, True), fill=MUTED)

    # Method badge
    method_str = method + (f"  R{round_num}" if round_num else "")
    mc = RED if method == "KO" else ORANGE if method == "TKO" else BLUE
    mw = int(draw.textlength(method_str, font=load_impact(28))) + 32
    mx = W // 2 - mw // 2
    rr(draw, [mx, 188, mx + mw, 226], 6,
       fill=tuple(v // 5 for v in mc), outline=mc, width=2)
    draw.text((mx + 16, 192), method_str, font=load_impact(28), fill=mc)

    # Footer
    draw.text((20, H-22), f"Logged by {logged_by}  ·  BOXING BETA BOXREC", font=load_font(11, True), fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# CHAMPION CROWNED IMAGE
# ═══════════════════════════════════════════
def generate_champion_crowned(belt, division, champion_name, won_date=""):
    BELT_COLORS_LOCAL = {"WBC": (0,176,80), "WBO": (0,112,192), "IBF": (192,0,0), "WBA": (255,140,0)}
    bc = BELT_COLORS_LOCAL.get(belt, GOLD)
    W, H = 860, 340
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # BG glow
    grad(img, 0, 0, W, H, BG2, BG)
    # Top accent
    grad(img, 0, 0, W, 5, bc, tuple(v // 2 for v in bc))
    draw.line([(0, H-32), (W, H-32)], fill=BORDER, width=1)

    # Gold star decoration
    for sx, sy in [(60, 60), (W-60, 60), (W//2, 40)]:
        draw.text((sx-8, sy-12), "★", font=load_impact(24), fill=bc)

    # Header
    draw.text((W//2 - int(draw.textlength("NEW WORLD CHAMPION", font=load_font(11, True)))//2,
               18), "NEW WORLD CHAMPION", font=load_font(11, True), fill=tuple(min(255, v+80) for v in bc))

    # Belt name big
    belt_txt = f"{belt} {division.upper()}"
    bw2 = int(draw.textlength(belt_txt, font=load_impact(36)))
    draw.text((W//2 - bw2//2, 36), belt_txt, font=load_impact(36), fill=bc)

    # Divider
    draw.line([(W//2-120, 88), (W//2+120, 88)], fill=bc, width=2)

    # Champion name BIG
    cf = load_impact(72) if len(champion_name) <= 12 else load_impact(52) if len(champion_name) <= 18 else load_impact(38)
    cw2 = int(draw.textlength(champion_name.upper(), font=cf))
    draw.text((W//2 - cw2//2, 96), champion_name.upper(), font=cf, fill=WHITE)

    # CHAMPION label
    cl_w = int(draw.textlength("CHAMPION", font=load_impact(28)))
    draw.text((W//2 - cl_w//2, 182), "CHAMPION", font=load_impact(28), fill=bc)

    # Date
    if won_date:
        dt_w = int(draw.textlength(f"Since {won_date}", font=load_font(14, True)))
        draw.text((W//2 - dt_w//2, 220), f"Since {won_date}", font=load_font(14, True), fill=MUTED)

    # Belt image path attempt
    belt_path = os.path.join(os.path.dirname(__file__), "static", "belts", f"{belt.lower()}.png")
    if not os.path.exists(belt_path):
        # Draw decorative belt bar instead
        grad(img, W//2-180, 248, W//2+180, 278, tuple(v//3 for v in bc), bc)
        draw.rounded_rectangle([W//2-180, 248, W//2+180, 278], radius=6,
            fill=tuple(v//4 for v in bc), outline=bc, width=2)
        btxt = f"🏆 {belt} CHAMPIONSHIP BELT"
        btw = int(draw.textlength(btxt, font=load_font(13, True)))
        draw.text((W//2 - btw//2, 256), btxt, font=load_font(13, True), fill=bc)

    draw.text((20, H-22), "BOXING BETA BOXREC  ·  World Championships", font=load_font(11, True), fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# REGISTRATION SUCCESS IMAGE
# ═══════════════════════════════════════════
def generate_registration_success(fighter_name, division, discord_name):
    W, H = 860, 280
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    grad(img, 0, 0, W, H, BG2, BG3)
    grad(img, 0, 0, W, 5, GREEN, (0, 100, 50))
    draw.line([(0, H-32), (W, H-32)], fill=BORDER, width=1)

    draw.text((20, 14), "BOXING BETA BOXREC", font=load_font(11, True), fill=GREEN)
    draw.text((20, 30), "FIGHTER REGISTERED", font=load_impact(34), fill=WHITE)
    draw.line([(20, 74), (W-20, 74)], fill=BORDER, width=1)

    # Check icon
    draw.ellipse([30, 90, 90, 150], fill=(0, 60, 30), outline=GREEN, width=2)
    draw.text((44, 96), "✓", font=load_impact(42), fill=GREEN)

    # Fighter name
    nf = load_impact(52) if len(fighter_name) <= 14 else load_impact(38)
    draw.text((110, 88), fighter_name.upper(), font=nf, fill=WHITE)
    draw.text((110, 150), f"{division}  ·  {discord_name}", font=load_font(14, True), fill=MUTED)

    # Tags
    tags = [("✅ Verified", GREEN), ("🥊 Fighter", (100, 100, 200))]
    tx = 110
    for tag, col in tags:
        tw2 = int(draw.textlength(tag, font=load_font(12, True))) + 20
        rr(draw, [tx, 176, tx+tw2, 200], 4,
           fill=tuple(v//6 for v in col), outline=col, width=1)
        draw.text((tx+10, 180), tag, font=load_font(12, True), fill=col)
        tx += tw2 + 8

    draw.text((20, H-22), "Welcome to Beta Rec  ·  Use /profile to view your record", font=load_font(11, True), fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# VERIFY / REGISTER IMAGE (bot command)
# ═══════════════════════════════════════════
def generate_verified_card(fighter_name, division, discord_name, registered_by="Admin"):
    return generate_registration_success(fighter_name, division, discord_name)


# ═══════════════════════════════════════════
# RESET RECORD IMAGE
# ═══════════════════════════════════════════
def generate_reset_record(fighter_name, reset_by="Admin"):
    W, H = 860, 200
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    grad(img, 0, 0, W, H, BG2, BG3)
    grad(img, 0, 0, W, 4, ORANGE, (150, 60, 0))
    draw.line([(0, H-30), (W, H-30)], fill=BORDER, width=1)
    draw.text((20, 14), "BOXING BETA BOXREC", font=load_font(11, True), fill=ORANGE)
    draw.text((20, 30), "RECORD RESET", font=load_impact(30), fill=WHITE)
    draw.line([(20, 68), (W-20, 68)], fill=BORDER, width=1)
    nf = load_impact(44) if len(fighter_name) <= 16 else load_impact(32)
    draw.text((40, 82), fighter_name.upper(), font=nf, fill=WHITE)
    draw.text((40, 138), "Record reset to  0W - 0L - 0D  (0 KOs)", font=load_font(14, True), fill=MUTED)
    draw.text((20, H-20), f"Reset by {reset_by}  ·  BOXING BETA BOXREC", font=load_font(11, True), fill=DIM)
    return to_bytes(img)


# ═══════════════════════════════════════════
# UPDATE RECORD IMAGE
# ═══════════════════════════════════════════
def generate_update_record(fighter, updated_by="Admin"):
    W, H = 860, 240
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    grad(img, 0, 0, W, H, BG2, BG3)
    grad(img, 0, 0, W, 4, BLUE, (0, 60, 150))
    draw.line([(0, H-30), (W, H-30)], fill=BORDER, width=1)
    draw.text((20, 14), "BOXING BETA BOXREC", font=load_font(11, True), fill=BLUE)
    draw.text((20, 30), "RECORD UPDATED", font=load_impact(30), fill=WHITE)
    draw.line([(20, 68), (W-20, 68)], fill=BORDER, width=1)
    name = fighter.get("fighter_name", "?")
    nf = load_impact(40) if len(name) <= 16 else load_impact(30)
    draw.text((40, 80), name.upper(), font=nf, fill=WHITE)
    # Stats row
    stats = [
        (str(fighter.get("wins", 0)), "WINS", GREEN),
        (str(fighter.get("losses", 0)), "LOSSES", RED),
        (str(fighter.get("draws", 0)), "DRAWS", MUTED),
        (str(fighter.get("kos", 0)), "KOs", ORANGE),
    ]
    sx = 40
    for val, label, col in stats:
        draw.text((sx, 134), val, font=load_impact(36), fill=col)
        vw = int(draw.textlength(val, font=load_impact(36)))
        draw.text((sx, 175), label, font=load_font(11, True), fill=MUTED)
        sx += vw + 50
    draw.text((20, H-20), f"Updated by {updated_by}  ·  BOXING BETA BOXREC", font=load_font(11, True), fill=DIM)
    return to_bytes(img)
