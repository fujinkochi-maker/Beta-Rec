import discord
from discord import app_commands
from discord.ext import commands
import database as db
import image_gen as ig
import os, re

DIVISIONS = db.DIVISIONS
BELTS = db.BELTS

division_choices = [app_commands.Choice(name=d, value=d) for d in DIVISIONS]
method_choices   = [app_commands.Choice(name=m, value=m) for m in ["KO","TKO","Decision","Split Decision"]]
belt_choices     = [app_commands.Choice(name=b, value=b) for b in BELTS]

VERIFIED_ROLE_NAME = os.getenv("VERIFIED_ROLE_NAME", "Verified Fighter")
MOD_ROLE_NAME      = os.getenv("MOD_ROLE_NAME", "Mod")

# ── Helpers ───────────────────────────────────────────────
def fmt_nickname(fighter):
    """Format Discord nickname: Name (W-L-D) KOs KO"""
    w = fighter.get("wins",0)
    l = fighter.get("losses",0)
    d = fighter.get("draws",0)
    k = fighter.get("kos",0)
    name = fighter.get("fighter_name","?")
    nick = fighter.get("nickname","")
    display = f'"{nick}" {name}' if nick else name
    return f"{display} ({w}-{l}-{d}) {k} KO"

async def update_discord_nickname(guild, discord_id, fighter):
    try:
        member = guild.get_member(int(discord_id))
        if not member: member = await guild.fetch_member(int(discord_id))
        if member:
            await member.edit(nick=fmt_nickname(fighter))
    except Exception as e:
        print(f"Could not update nickname for {discord_id}: {e}")

async def assign_verified_role(guild, discord_id):
    try:
        member = guild.get_member(int(discord_id))
        if not member: member = await guild.fetch_member(int(discord_id))
        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
        if not role:
            role = await guild.create_role(name=VERIFIED_ROLE_NAME, color=discord.Color.from_rgb(232,0,30), reason="BoxRec verified fighter")
        if role not in member.roles:
            await member.add_roles(role)
    except Exception as e:
        print(f"Could not assign role to {discord_id}: {e}")

async def remove_verified_role(guild, discord_id):
    try:
        member = guild.get_member(int(discord_id))
        if not member: member = await guild.fetch_member(int(discord_id))
        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
        if role and role in member.roles:
            await member.remove_roles(role)
        await member.edit(nick=None)
    except Exception as e:
        print(f"Could not remove role from {discord_id}: {e}")

def is_mod(interaction):
    return (interaction.user.guild_permissions.manage_guild or
            interaction.user.id == interaction.guild.owner_id or
            str(interaction.user.id) in [x.strip() for x in os.getenv('ADMIN_DISCORD_IDS','').split(',') if x.strip()])

class BoxingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"✅ Commands synced to guild {guild_id}")
        else:
            await self.tree.sync()
            print("✅ Commands synced globally")

    async def on_ready(self):
        print(f"✅ Bot online as {self.user}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name="Boxing Beta"))

    async def on_message(self, message):
        if message.author.bot:
            return
        reg_channel = os.getenv("REGISTRATION_CHANNEL", "registration")
        reg_channel_id = os.getenv("REGISTRATION_CHANNEL_ID", "")
        ch_name = getattr(message.channel, "name", "").lower()
        ch_id = str(message.channel.id)
        print(f"[MSG] #{ch_name} (id:{ch_id}) | from: {message.author} | content: {message.content[:60]}")
        if ch_name == reg_channel.lower() or (reg_channel_id and ch_id == reg_channel_id):
            print(f"[REG] Registration channel matched! Processing...")
            await handle_registration_message(message)
        await self.process_commands(message)

bot = BoxingBot()


# ══════════════════════════════════════════════════════════
# /profile
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="profile", description="View a fighter's BoxRec profile card")
@app_commands.describe(member="Discord member (optional)", name="Fighter name (optional)")
async def profile(interaction: discord.Interaction, member: discord.Member = None, name: str = None):
    await interaction.response.defer()
    fighter = None
    if member:  fighter = db.get_fighter_by_discord(str(member.id))
    elif name:  fighter = db.get_fighter_by_name(name)
    else:       fighter = db.get_fighter_by_discord(str(interaction.user.id))
    if not fighter:
        buf = ig.generate_not_registered()
        return await interaction.followup.send(file=discord.File(fp=buf, filename="not_found.png"))
    belts   = db.get_fighter_belts(fighter["fighter_name"])
    matches = db.get_match_history(fighter["fighter_name"], 5)
    rank    = db.get_fighter_rank(str(fighter["discord_id"]), fighter.get("division"))
    buf = ig.generate_profile_card(fighter, belts, matches, rank)
    await interaction.followup.send(file=discord.File(fp=buf, filename="profile.png"))


# ══════════════════════════════════════════════════════════
# /h2h  — Head to head comparison image
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="h2h", description="Head-to-head comparison of two fighters")
@app_commands.describe(fighter1="First fighter name or @mention", fighter2="Second fighter name or @mention",
                       member1="First fighter Discord member", member2="Second fighter Discord member")
async def h2h(interaction: discord.Interaction,
              member1: discord.Member = None, member2: discord.Member = None,
              fighter1: str = None, fighter2: str = None):
    await interaction.response.defer()
    f1 = db.get_fighter_by_discord(str(member1.id)) if member1 else db.get_fighter_by_name(fighter1) if fighter1 else None
    f2 = db.get_fighter_by_discord(str(member2.id)) if member2 else db.get_fighter_by_name(fighter2) if fighter2 else None
    if not f1 or not f2:
        return await interaction.followup.send("❌ Could not find both fighters. Make sure they are registered.", ephemeral=True)
    b1 = db.get_fighter_belts(f1["fighter_name"])
    b2 = db.get_fighter_belts(f2["fighter_name"])
    buf = ig.generate_h2h_image(f1, f2, b1, b2)
    await interaction.followup.send(file=discord.File(fp=buf, filename="h2h.png"))


# ══════════════════════════════════════════════════════════
# /leaderboard
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="leaderboard", description="Top fighters leaderboard image")
@app_commands.choices(division=division_choices)
async def leaderboard(interaction: discord.Interaction, division: str = None):
    await interaction.response.defer()
    fighters = db.get_leaderboard(10, division)
    if not fighters:
        buf = ig.generate_empty_leaderboard()
        return await interaction.followup.send(file=discord.File(fp=buf, filename="leaderboard.png"))
    for f in fighters: f["belts"] = db.get_fighter_belts(f["fighter_name"])
    buf = ig.generate_leaderboard_image(fighters, division)
    await interaction.followup.send(file=discord.File(fp=buf, filename="leaderboard.png"))


# ══════════════════════════════════════════════════════════
# /rankings
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="rankings", description="Fighter rankings by win rate image")
@app_commands.choices(division=division_choices)
async def rankings(interaction: discord.Interaction, division: str = None):
    await interaction.response.defer()
    fighters = db.get_rankings(division, 10)
    if not fighters:
        buf = ig.generate_empty_rankings()
        return await interaction.followup.send(file=discord.File(fp=buf, filename="rankings.png"))
    for f in fighters: f["belts"] = db.get_fighter_belts(f["fighter_name"])
    buf = ig.generate_rankings_image(fighters, division)
    await interaction.followup.send(file=discord.File(fp=buf, filename="rankings.png"))


# ══════════════════════════════════════════════════════════
# /matchhistory
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="matchhistory", description="Recent match history image")
@app_commands.choices(division=division_choices)
async def matchhistory(interaction: discord.Interaction, name: str = None, division: str = None):
    await interaction.response.defer()
    matches = db.get_match_history(name, 10, division)
    if not matches:
        buf = ig.generate_empty_matchhistory()
        return await interaction.followup.send(file=discord.File(fp=buf, filename="matchhistory.png"))
    buf = ig.generate_matchhistory_image(matches, name, division)
    await interaction.followup.send(file=discord.File(fp=buf, filename="matchhistory.png"))


# ══════════════════════════════════════════════════════════
# /divisions
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="divisions", description="View all world championship belts image")
async def divisions(interaction: discord.Interaction):
    await interaction.response.defer()
    champs = db.get_all_championships()
    active = [c for c in champs if c.get("champion")]
    if not active:
        buf = ig.generate_empty_championships()
        return await interaction.followup.send(file=discord.File(fp=buf, filename="championships.png"))
    buf = ig.generate_championships_image(champs)
    await interaction.followup.send(file=discord.File(fp=buf, filename="championships.png"))


# ══════════════════════════════════════════════════════════
# /addmatch  — Admin/Mod
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="addmatch", description="Log a match result")
@app_commands.describe(winner="Winner fighter name", loser="Loser fighter name",
                       method="Win method", division="Division", round_num="Round ended (optional)")
@app_commands.choices(method=method_choices, division=division_choices)
async def addmatch(interaction: discord.Interaction, winner: str, loser: str, method: str,
                   division: str = "Heavyweight", round_num: int = None):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Only admins or mods can log matches.", ephemeral=True)
    await interaction.response.defer()
    is_ko = method in ("KO","TKO")
    db.add_match(winner, loser, method, round_num, is_ko, division)
    w = db.get_fighter_by_name(winner)
    l = db.get_fighter_by_name(loser)
    # Update nicknames
    if w and w.get("discord_id"):
        await update_discord_nickname(interaction.guild, w["discord_id"], w)
    if l and l.get("discord_id"):
        await update_discord_nickname(interaction.guild, l["discord_id"], l)
    embed = discord.Embed(title="Match Logged", color=0x00ff88)
    embed.add_field(name="Winner", value=f"**{winner}** ({w['wins'] if w else '?'}W-{w['losses'] if w else '?'}L)", inline=True)
    embed.add_field(name="Loser",  value=f"**{loser}** ({l['wins'] if l else '?'}W-{l['losses'] if l else '?'}L)", inline=True)
    embed.add_field(name="Result", value=f"{method}{f' R{round_num}' if round_num else ''} · {division}", inline=False)
    embed.set_footer(text=f"Logged by {interaction.user.display_name} · Nicknames updated")
    await interaction.followup.send(embed=embed)


# ══════════════════════════════════════════════════════════
# /update_record  — Admin/Mod
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="update_record", description="Manually update a fighter's record")
@app_commands.describe(member="Fighter's Discord member", wins="Wins", losses="Losses", draws="Draws", kos="KOs", division="Division")
@app_commands.choices(division=division_choices)
async def update_record(interaction: discord.Interaction, member: discord.Member,
                        wins: int = None, losses: int = None, draws: int = None,
                        kos: int = None, division: str = None):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Only admins or mods can update records.", ephemeral=True)
    await interaction.response.defer()
    fighter = db.get_fighter_by_discord(str(member.id))
    if not fighter:
        return await interaction.followup.send(f"❌ {member.mention} is not registered.", ephemeral=True)
    updated = db.manual_update_record(
        str(member.id),
        wins   if wins   is not None else fighter["wins"],
        losses if losses is not None else fighter["losses"],
        draws  if draws  is not None else fighter["draws"],
        kos    if kos    is not None else fighter["kos"],
        division
    )
    if updated:
        await update_discord_nickname(interaction.guild, str(member.id), updated)
    buf = ig.generate_update_record(updated, interaction.user.display_name)
    await interaction.followup.send(file=discord.File(fp=buf, filename="record_updated.png"))


# ══════════════════════════════════════════════════════════
# /editfighter  — Admin/Mod
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="editfighter", description="Edit a fighter's name, nickname, country or division")
@app_commands.describe(member="Fighter's Discord member", fighter_name="New fighter name",
                       nickname="New nickname", country="Country code (e.g. PH, US)", division="Division")
@app_commands.choices(division=division_choices)
async def editfighter(interaction: discord.Interaction, member: discord.Member,
                      fighter_name: str = None, nickname: str = None,
                      country: str = None, division: str = None):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Only admins or mods can do this.", ephemeral=True)
    await interaction.response.defer()
    fighter = db.get_fighter_by_discord(str(member.id))
    if not fighter:
        return await interaction.followup.send(f"❌ {member.mention} is not registered.", ephemeral=True)
    db.update_fighter_info(str(member.id), fighter_name, nickname, country, division)
    updated = db.get_fighter_by_discord(str(member.id))
    await update_discord_nickname(interaction.guild, str(member.id), updated)
    await interaction.followup.send(f"✅ Fighter **{updated['fighter_name']}** updated. Nickname refreshed.")


# ══════════════════════════════════════════════════════════
# /resetrecord  — Admin/Mod
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="resetrecord", description="Reset a fighter's record to 0-0-0")
async def resetrecord(interaction: discord.Interaction, member: discord.Member):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Only admins or mods can do this.", ephemeral=True)
    await interaction.response.defer()
    fighter = db.get_fighter_by_discord(str(member.id))
    if not fighter:
        return await interaction.followup.send(f"❌ {member.mention} is not registered.", ephemeral=True)
    db.reset_record(str(member.id))
    updated = db.get_fighter_by_discord(str(member.id))
    await update_discord_nickname(interaction.guild, str(member.id), updated)
    buf = ig.generate_reset_record(fighter["fighter_name"], interaction.user.display_name)
    await interaction.followup.send(file=discord.File(fp=buf, filename="record_reset.png"))


# ══════════════════════════════════════════════════════════
# /setchampion /removechampion  — Admin/Mod
# ══════════════════════════════════════════════════════════
async def fighter_name_autocomplete(interaction: discord.Interaction, current: str):
    fighters = db.get_all_fighters()
    return [
        app_commands.Choice(name=f["fighter_name"], value=f["fighter_name"])
        for f in fighters
        if current.lower() in f["fighter_name"].lower()
    ][:25]

@bot.tree.command(name="setchampion", description="Assign a world title belt to a fighter")
@app_commands.describe(belt="Belt organization", division="Weight division", name="Fighter name")
@app_commands.choices(belt=belt_choices, division=division_choices)
@app_commands.autocomplete(name=fighter_name_autocomplete)
async def setchampion(interaction: discord.Interaction, belt: str, division: str, name: str):
    if not is_mod(interaction): return await interaction.response.send_message("❌ Mods/Admins only.", ephemeral=True)
    fighter = db.get_fighter_by_name(name)
    if not fighter:
        return await interaction.response.send_message(f"❌ Fighter **{name}** not found. They must be registered first.", ephemeral=True)
    await interaction.response.defer()
    db.set_champion(belt, division, name)
    from datetime import date
    buf = ig.generate_champion_crowned(belt, division, name, date.today().isoformat())
    await interaction.followup.send(file=discord.File(fp=buf, filename="champion.png"))

@bot.tree.command(name="removechampion", description="Vacate a world title belt")
@app_commands.choices(belt=belt_choices, division=division_choices)
async def removechampion(interaction: discord.Interaction, belt: str, division: str):
    if not is_mod(interaction): return await interaction.response.send_message("❌ Mods/Admins only.", ephemeral=True)
    await interaction.response.defer()
    db.remove_champion(belt, division)
    buf = ig.generate_empty_championships()
    await interaction.followup.send(
        content=f"✅ **{belt} {division}** title is now **vacant**.",
        file=discord.File(fp=buf, filename="vacant.png")
    )



# ══════════════════════════════════════════════════════════
# AUTO REGISTRATION — watches #registration channel
# ══════════════════════════════════════════════════════════
import re, difflib

# Explicit word filter (add more as needed)
BANNED_WORDS = [
    "nigga","nigger","fuck","shit","bitch","ass","cunt","dick","pussy",
    "faggot","retard","whore","slut","bastard","damn","hell","piss",
    "cock","penis","vagina","sex","porn","rape","kill","nazi","hitler"
]

# Field aliases — handles typos and alternate names
FIELD_ALIASES = {
    "fighter_name": [
        "fighter name","fightername","fighter","name","fighter_name",
        "char name","character name","char","player name","playername",
        "fighter name:", "name:"
    ],
    "weight_class": [
        "weight class","weightclass","weight","division","weight class:",
        "class","weight division","wc","w class"
    ],
}

# Weight class fuzzy match list
WEIGHT_CLASSES = [
    "Heavyweight","Cruiserweight","Light Heavyweight","Super Middleweight",
    "Middleweight","Super Welterweight","Welterweight","Super Lightweight",
    "Lightweight","Super Featherweight","Featherweight","Super Bantamweight",
    "Bantamweight","Super Flyweight","Flyweight","Minimumweight"
]

def fuzzy_match_weight(raw):
    """Match a weight class string even with typos."""
    if not raw: return "Heavyweight"
    raw_clean = raw.strip().title()
    # Exact match first
    for wc in WEIGHT_CLASSES:
        if wc.lower() == raw_clean.lower():
            return wc
    # Fuzzy match
    matches = difflib.get_close_matches(raw_clean, WEIGHT_CLASSES, n=1, cutoff=0.5)
    if matches:
        return matches[0]
    # Keyword match
    raw_lower = raw.lower()
    for wc in WEIGHT_CLASSES:
        if any(part.lower() in raw_lower for part in wc.split()):
            return wc
    return "Heavyweight"

def parse_field_name(line_key):
    """Fuzzy match a field label to a known field."""
    line_key_clean = line_key.lower().strip().rstrip(":").strip()
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if line_key_clean == alias.lower().rstrip(":").strip():
                return field
    # Fuzzy fallback
    all_aliases = [(alias, field) for field, aliases in FIELD_ALIASES.items() for alias in aliases]
    alias_strs = [a[0].lower() for a in all_aliases]
    matches = difflib.get_close_matches(line_key_clean, alias_strs, n=1, cutoff=0.6)
    if matches:
        idx = alias_strs.index(matches[0])
        return all_aliases[idx][1]
    return None

def parse_registration(text):
    """
    Parse registration message into fields.
    Works with multiline AND single line input.
    Examples:
      Fighter Name: Nick Ball\nWeight class: Featherweight
      Fighter Name: Nick Ball Weight Class: Featherweight
    """
    result = {"fighter_name": None, "weight_class": None}

    # Build a regex pattern from all known field aliases
    # Matches "Field Label: value" anywhere in the text
    all_aliases = []
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            all_aliases.append((re.escape(alias.rstrip(":")), field))

    # Sort by length descending so longer matches win
    all_aliases.sort(key=lambda x: len(x[0]), reverse=True)

    # Try to find each field using regex on the full text (handles single line)
    text_norm = text.replace("\n", " \n ")  # normalize newlines
    for alias_pattern, field in all_aliases:
        if result[field]:
            continue  # already found
        # Match "alias: value" — value goes until next known field label or end
        pattern = rf"(?i){alias_pattern}\s*:?\s*(.+?)(?=(?:{'|'.join(re.escape(a) for a, _ in all_aliases)})\s*:?\s*|$)"
        m = re.search(pattern, text_norm, re.IGNORECASE)
        if m:
            val = m.group(1).strip().rstrip("\n").strip()
            if val:
                result[field] = val

    # Fallback: also try line by line
    if not result["fighter_name"] or not result["weight_class"]:
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip(); value = value.strip()
            field = parse_field_name(key)
            if field and value and not result[field]:
                result[field] = value

    return result

def contains_explicit(text):
    """Check if text contains banned/explicit words."""
    text_lower = text.lower()
    # Remove spaces to catch spaced-out slurs
    text_nospace = text_lower.replace(" ","").replace("_","").replace("-","")
    for word in BANNED_WORDS:
        if word in text_lower or word in text_nospace:
            return word
    return None

async def handle_registration_message(message):
    """Process a message in the registration channel."""
    content = message.content.strip()

    # Must have at least one colon (looks like a form)
    if ":" not in content:
        return

    # Parse the form
    parsed = parse_registration(content)
    fighter_name = parsed.get("fighter_name")
    weight_class_raw = parsed.get("weight_class")

    # Must have at least fighter name
    if not fighter_name:
        await message.reply(
            "❌ **Could not find your Fighter Name.**\n"
            "Make sure you include a line like:\n`Fighter Name: Your Name Here`",
            mention_author=True
        )
        await message.add_reaction("❌")
        return

    # Clean fighter name
    fighter_name = fighter_name.strip()

    # Check explicit content
    explicit = contains_explicit(fighter_name)
    if explicit:
        await message.reply(
            f"❌ **Fighter name rejected** — contains inappropriate content.\n"
            f"Please choose a different name.",
            mention_author=True
        )
        await message.add_reaction("🚫")
        return

    # Check already registered (this Discord user)
    existing_user = db.get_fighter_by_discord(str(message.author.id))
    if existing_user:
        await message.reply(
            f"❌ **You are already registered** as **{existing_user['fighter_name']}**.\n"
            f"Contact an admin if you need to change your name.",
            mention_author=True
        )
        await message.add_reaction("⚠️")
        return

    # Check name taken
    existing_name = db.get_fighter_by_name(fighter_name)
    if existing_name and existing_name.get("discord_id") != str(message.author.id):
        await message.reply(
            f"❌ **Fighter name '{fighter_name}' is already taken.**\n"
            f"Please choose a different name.",
            mention_author=True
        )
        await message.add_reaction("❌")
        return

    # Fuzzy match weight class
    division = fuzzy_match_weight(weight_class_raw) if weight_class_raw else "Heavyweight"

    # Register the fighter
    db.register_fighter(fighter_name, str(message.author.id), division, "", "")

    # Update Discord nickname
    fighter = db.get_fighter_by_discord(str(message.author.id))
    guild = message.guild
    await update_discord_nickname(guild, str(message.author.id), fighter)
    await assign_verified_role(guild, str(message.author.id))

    # Send image
    buf = ig.generate_registration_success(fighter_name, division, message.author.display_name)
    await message.reply(
        content=f"{message.author.mention} Welcome to **Beta Rec**! Use `/profile` to see your card.",
        file=discord.File(fp=buf, filename="registered.png"),
        mention_author=True
    )
    await message.add_reaction("✅")

    print(f"✅ Auto-registered: {fighter_name} ({division}) — {message.author}")


# ══════════════════════════════════════════════════════════
# /deletefighter  — replaces /unregister
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="deletefighter", description="(Admin) Remove a fighter from the system")
@app_commands.describe(member="Discord member to remove")
@app_commands.default_permissions(manage_guild=True)
async def deletefighter(interaction: discord.Interaction, member: discord.Member):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
    await interaction.response.defer()
    fighter = db.get_fighter_by_discord(str(member.id))
    if not fighter:
        return await interaction.followup.send(f"❌ {member.mention} is not registered.", ephemeral=True)
    db.delete_fighter(str(member.id))
    await remove_verified_role(interaction.guild, str(member.id))
    await interaction.followup.send(
        f"✅ **{fighter['fighter_name']}** has been removed from the system and their Verified Fighter role stripped."
    )


# ══════════════════════════════════════════════════════════
# /linkfighter  — manually link a Discord user to existing fighter
# ══════════════════════════════════════════════════════════
@bot.tree.command(name="linkfighter", description="(Admin) Link a Discord member to an existing fighter record")
@app_commands.describe(member="Discord member", name="Fighter name in the system")
@app_commands.autocomplete(name=fighter_name_autocomplete)
@app_commands.default_permissions(manage_guild=True)
async def linkfighter(interaction: discord.Interaction, member: discord.Member, name: str):
    if not is_mod(interaction):
        return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
    await interaction.response.defer()
    fighter = db.get_fighter_by_name(name)
    if not fighter:
        return await interaction.followup.send(f"❌ Fighter **{name}** not found.", ephemeral=True)
    db.verify_fighter(str(member.id), name)
    updated = db.get_fighter_by_discord(str(member.id))
    await update_discord_nickname(interaction.guild, str(member.id), updated)
    await assign_verified_role(interaction.guild, str(member.id))
    await interaction.followup.send(
        f"✅ **{name}** linked to {member.mention} — nickname updated and Verified Fighter role assigned."
    )


def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Missing DISCORD_TOKEN in .env")
        return
    bot.run(token)
