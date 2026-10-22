import os
import asyncio
import discord
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands

# Google Gemini SDK
from google import genai

# =====================================================================
# SETTINGS
# =====================================================================
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

EXCLUDED_ROLES = ["Staff", "Admin", "Trial Moderator", "Moderator", "Ticket King"]
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
EMPLOYEE_ROLE_NAME = "Employee"

# Eigene Kategorie-Listen für Befehle
PARTICIPATE_CATEGORY_IDS = [1537245698443968583, 1538637387138072627]
WORKER_CATEGORY_IDS = [1537242203397820446]
SPECIAL_CATEGORY_ID = 1536184549170741269

# Exklusive Kategorie ID für die KI-Antworten & Auto-Welcome
AI_ALLOWED_CATEGORY_ID = 1537228656055820401

# =====================================================================
# KI / GEMINI TRAINING & SYSTEM PROMPT (ENGLISH)
# =====================================================================
AI_SYSTEM_PROMPT = """
You are the official automated Event Support Bot on this Discord server. Your task is to assist players in support tickets warmly, politely, and naturally in English.

IMPORTANT CONVERSATION STYLE:
- Do NOT just copy and paste facts word-for-word like a robot!
- Speak dynamically and conversationally. Answer the user's specific question in a friendly tone while incorporating the facts below.

OFFICIAL EVENT INFORMATION & KNOWLEDGE BASE:

📜 Event Information:
- Start Date & Time: The exact date/time is announced in <#1533506634985504909>. Advise them to check there and turn on notifications!
- 💸 Entry Fee & Discounts: Standard entry fee is 35k. Discounts are available if they invite others to our event.
- 📍 Payment Location: Paid after joining the VIP server at Howling Peak.
- 🚪 Gate Opening: Once everyone has paid, the owner guides the group to the gate and unlocks it.
- ⚔️ Parkour & Reward: After passing through the gate, players get infinite attempts on the parkour until claiming the sword!
- 💰 Post-Event Cash: Players can stay in the server after getting rewards and invite others to earn cash.
- ✅ Legitimacy Check: If worried about safety, refer them to <#1534230669729861652> to read player feedback!

👥 Invite Rules & Rewards:
- Qualified Invites: Only invite people genuinely interested in joining the event.
- Invite Reward Rate: 3k per invited user initially. Dedicated, high-volume inviters will get a higher rate per person.

🚨 SPECIAL TRIGGERS & ACTIONS:

1. USER AGREES TO PARTICIPATE:
- If the user indicates they understood everything and agree to participate (e.g., "I agree", "I understand", "ok let's do it", "I want to join"):
  - Respond warmly confirming they are being signed up!
  - Include this exact trigger word at the VERY END of your response: [TRIGGER_PARTICIPATE]
  - Explicitly remind them: "Make sure to turn on notifications for the <#1533506634985504909> channel to not miss the next event! The next event will be announced in there soon."

2. UNANSWERABLE QUESTIONS / STAFF ESCALATION:
- If a user asks something not covered in these rules, asks for a human/staff, or pings staff:
  - Politely inform them that you cannot handle this specific request and that a staff member will assist them shortly.
  - ALWAYS include the staff tag <@&1536186291417518081> in your message!
"""

# Gemini Client initialisieren
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("WARNING: No GEMINI_API_KEY found. AI responses are disabled!")

# =====================================================================

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = EventBot()

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as: {bot.user.name}")
    print("-----------------------------------------------------")


# Helper function to completely remove existing prefixes
def clean_channel_name(name: str) -> str:
    prefixes = ["❗️-", "❗️", "⭐-", "⭐", "✅-", "✅"]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True
    return name


# Helper function to find first non-full category from a specific list
def get_available_category(guild, category_ids):
    for cat_id in category_ids:
        category = guild.get_channel(cat_id)
        if category and isinstance(category, discord.CategoryChannel):
            if len(category.channels) < 50:
                return category
    return None


# Helper function for executing participation logic (Role, Rename, Move)
async def execute_participate_logic(guild, channel):
    target_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    if not target_role:
        return False, f"Role **'@{PARTICIPANT_ROLE_NAME}'** not found!"

    assigned_count = 0
    for member in channel.members:
        if member.bot:
            continue

        has_excluded_role = any(role.name in EXCLUDED_ROLES or role.name == PARTICIPANT_ROLE_NAME for role in member.roles)
        if member.guild_permissions.administrator:
            has_excluded_role = True

        if not has_excluded_role:
            try:
                await member.add_roles(target_role)
                assigned_count += 1
            except discord.Forbidden:
                pass

    clean_name = clean_channel_name(channel.name)
    new_name = f"❗️{clean_name}"
    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
        except discord.Forbidden:
            pass

    target_category = get_available_category(guild, PARTICIPATE_CATEGORY_IDS)
    if target_category and channel.category_id != target_category.id:
        try:
            await channel.edit(category=target_category)
        except discord.Forbidden:
            pass

    return True, f"Assigned @{PARTICIPANT_ROLE_NAME} to {assigned_count} user(s)."


# -------------------------------------------------------------------
# 1. AUTOMATISCHE BEGRÜSSUNG BEI NEUEM TICKET
# -------------------------------------------------------------------
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if not isinstance(channel, discord.TextChannel):
        return

    # Nur in der Ticket-Kategorie ausführen
    if not channel.category or channel.category.id != AI_ALLOWED_CATEGORY_ID:
        return

    # 2 Sekunden warten, bis Ticket King seine Nachricht gesendet hat
    await asyncio.sleep(2)

    welcome_text = (
        "Hello! Please read this info above, that should be all details you need! "
        "Let me know if you understand all and then don't hesitate to ask any further questions."
    )

    # Versuchen, auf die Ticket-King-Nachricht zu antworten
    try:
        async for msg in channel.history(limit=5, oldest_first=True):
            if msg.author.bot:
                await msg.reply(welcome_text)
                return
        # Falls keine Bot-Nachricht gefunden wurde, normal senden
        await channel.send(welcome_text)
    except Exception as e:
        print(f"Error sending auto-welcome: {e}")


# -------------------------------------------------------------------
# 2. AUTOMATISCHE KI-ANTWORT AUF TICKETS (on_message)
# -------------------------------------------------------------------
@bot.event
async def on_message(message: discord.Message):
    # Bots generell ignorieren
    if message.author.bot:
        return

    # Team-Mitglieder ignorieren
    if isinstance(message.author, discord.Member):
        has_excluded_role = any(role.name in EXCLUDED_ROLES for role in message.author.roles)
        if has_excluded_role or message.author.guild_permissions.administrator:
            await bot.process_commands(message)
            return

    # Kategorie-Filter
    if not message.channel.category or message.channel.category.id != AI_ALLOWED_CATEGORY_ID:
        await bot.process_commands(message)
        return

    # KI-Antwort generieren
    if gemini_client:
        async with message.channel.typing():
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=message.content,
                    config={
                        "system_instruction": AI_SYSTEM_PROMPT,
                        "temperature": 0.6,
                    }
                )
                if response.text:
                    reply_text = response.text

                    # Prüfen, ob die KI die Teilnahme getriggert hat
                    trigger_found = False
                    if "[TRIGGER_PARTICIPATE]" in reply_text:
                        trigger_found = True
                        reply_text = reply_text.replace("[TRIGGER_PARTICIPATE]", "").strip()

                    # Nachricht absenden
                    await message.reply(
                        reply_text,
                        allowed_mentions=discord.AllowedMentions(roles=True, users=True)
                    )

                    # Falls getriggert: Automatsichen Participate-Prozess ausführen
                    if trigger_found:
                        await execute_participate_logic(message.guild, message.channel)

            except Exception as e:
                print(f"Fehler bei Gemini API Aufruf: {e}")
                await message.reply(f"⚠️ **KI-Fehler:** `{e}`")

    await bot.process_commands(message)


# -------------------------------------------------------------------
# SLASH COMMANDS (/participate, /worker, /paid, /sayall, etc.)
# -------------------------------------------------------------------
@bot.tree.command(name="participate", description="Assigns Participant role, adds ❗️ and moves ticket to participate category")
async def participate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success, msg = await execute_participate_logic(interaction.guild, interaction.channel)
    if success:
        await interaction.followup.send(f"✅ {msg}", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {msg}", ephemeral=True)


@bot.tree.command(name="worker", description="Assigns Employee role, adds ⭐ and moves ticket to worker category")
async def worker(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = interaction.channel

    target_role = discord.utils.get(guild.roles, name=EMPLOYEE_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Role **'@{EMPLOYEE_ROLE_NAME}'** was not found on this server!", ephemeral=True)
        return

    assigned_count = 0
    for member in channel.members:
        if member.bot:
            continue
        has_excluded_role = any(role.name in EXCLUDED_ROLES or role.name == EMPLOYEE_ROLE_NAME for role in member.roles)
        if member.guild_permissions.administrator:
            has_excluded_role = True

        if not has_excluded_role:
            try:
                await member.add_roles(target_role)
                assigned_count += 1
            except discord.Forbidden:
                pass

    clean_name = clean_channel_name(channel.name)
    new_name = f"⭐{clean_name}"
    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
        except discord.Forbidden:
            pass

    target_category = get_available_category(guild, WORKER_CATEGORY_IDS)
    if not target_category:
        await interaction.followup.send("❌ All Worker categories are full (50/50)!", ephemeral=True)
        return

    if channel.category_id != target_category.id:
        try:
            await channel.edit(category=target_category)
        except discord.Forbidden:
            pass

    await interaction.followup.send(f"✅ Role **@{target_role.name}** assigned to **{assigned_count}** new worker(s)!", ephemeral=True)


@bot.tree.command(name="paid", description="Marks ticket as paid and converts Participant to Former Participant")
async def paid(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = interaction.channel

    participant_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    former_role = discord.utils.get(guild.roles, name=FORMER_PARTICIPANT_ROLE_NAME)

    if not participant_role or not former_role:
        await interaction.followup.send("❌ Missing role(s) on server!", ephemeral=True)
        return

    swapped_count = 0
    for member in channel.members:
        if member.bot:
            continue
        if participant_role in member.roles:
            try:
                await member.remove_roles(participant_role)
                await member.add_roles(former_role)
                swapped_count += 1
            except discord.Forbidden:
                pass

    clean_name = clean_channel_name(channel.name)
    new_name = f"✅{clean_name}"
    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
        except discord.Forbidden:
            pass

    await interaction.followup.send(f"✅ Roles updated to `@{FORMER_PARTICIPANT_ROLE_NAME}` for **{swapped_count} user(s)**.", ephemeral=True)


@bot.tree.command(name="sayall", description="Sends a message to tickets or a specific category")
@app_commands.describe(message="The message to send", category_id="OPTIONAL: Category ID")
async def sayall(interaction: discord.Interaction, message: str, category_id: str = None):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    sent_count = 0

    target_category_id = None
    if category_id:
        try:
            target_category_id = int(category_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Invalid Category ID!", ephemeral=True)
            return

    for channel in guild.text_channels:
        is_target = False
        if target_category_id is not None:
            if channel.category and channel.category.id == target_category_id:
                is_target = True
        else:
            if channel.category is None:
                is_target = True

        if is_target:
            try:
                await channel.send(message)
                sent_count += 1
            except discord.Forbidden:
                pass

    await interaction.followup.send(f"📢 Message sent to **{sent_count} channel(s)**!", ephemeral=True)


@bot.tree.command(name="specialticket", description="Moves current ticket to Special Category")
async def specialticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = interaction.channel

    target_category = guild.get_channel(SPECIAL_CATEGORY_ID)
    if not target_category or not isinstance(target_category, discord.CategoryChannel):
        await interaction.followup.send("❌ Special category not found!", ephemeral=True)
        return

    try:
        await channel.edit(category=target_category)
        await interaction.followup.send(f"📁 Moved to **{target_category.name}**!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ No permissions to move channel.", ephemeral=True)


@bot.tree.command(name="movechannel", description="Moves current channel to specific category ID")
@app_commands.describe(category_id="The ID of target category")
async def movechannel(interaction: discord.Interaction, category_id: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = interaction.channel

    try:
        parsed_category_id = int(category_id.strip())
    except ValueError:
        await interaction.followup.send("❌ Invalid Category ID!", ephemeral=True)
        return

    target_category = guild.get_channel(parsed_category_id)
    if not target_category or not isinstance(target_category, discord.CategoryChannel):
        await interaction.followup.send("❌ Category not found!", ephemeral=True)
        return

    try:
        await channel.edit(category=target_category)
        await interaction.followup.send(f"📁 Moved to **{target_category.name}**!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ No permissions to move channel.", ephemeral=True)


# Start Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: No DISCORD_TOKEN found in environment variables!")
    else:
        bot.run(BOT_TOKEN)
