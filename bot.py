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

STAFF_ROLE_ID = 1536186291417518081
EXCLUDED_ROLES = ["Staff", "Admin", "Trial Moderator", "Moderator", "Ticket King"]
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
EMPLOYEE_ROLE_NAME = "Employee"

PARTICIPATE_CATEGORY_IDS = [1537245698443968583, 1538637387138072627]
WORKER_CATEGORY_IDS = [1537242203397820446]
SPECIAL_CATEGORY_ID = 1536184549170741269

# KI-Kategorie ID (Wo die KI arbeiten darf)
AI_ALLOWED_CATEGORY_ID = 1537228656055820401

# NEU: Staff-Pause Kategorie ID (Wohin das Ticket verschoben wird, wenn Staff schreibt)
STAFF_PAUSE_CATEGORY_ID = 1562656450562621571

# =====================================================================
# KI / GEMINI TRAINING & SYSTEM PROMPT (ENGLISH)
# =====================================================================
AI_SYSTEM_PROMPT = """
You are the official automated Event Support Bot on this Discord server. Your task is to assist players in support tickets directly, concisely, and naturally in English.

STRICT FORMATTING & CONVERSATION RULES:
1. BE CONCISE & DIRECT:
   - Keep answers SHORT (1-2 sentences max).
   - Do NOT add unnecessary empty lines or multi-paragraph fluff.
   - Do NOT repeat the full welcome intro if you or the bot already greeted them earlier!

2. ALWAYS ASK IF THEY HAVE MORE QUESTIONS:
   - After answering a user's question, ALWAYS briefly ask if they have any further questions (e.g., "Do you have any other questions?").

3. NOTIFICATION REMINDER (STRICTLY ONCE):
   - Mention the notification reminder ONLY ONCE during the entire conversation when relevant:
     "Make sure to turn on notifications for <#1533506634985504909> so you don't miss event announcements!"
   - Do NOT repeat or attach this reminder to every single message!

4. USER DENIES / HAS NO MORE QUESTIONS (PARTICIPATE TRIGGER):
   - Trigger the participation process ONLY when the user indicates they have no more questions or denies having further questions (e.g., "no", "no questions", "nope", "I'm good", "that's all", "understood all").
   - Action to take:
     - Respond ONLY with a single short line: "Awesome! You're all set and signed up for the event! 🎉"
     - Include this exact trigger word at the VERY END: [TRIGGER_PARTICIPATE]

5. UNANSWERABLE QUESTIONS / STAFF ESCALATION:
   - If a user asks something not covered in the rules, asks for staff, or pings staff:
     - Politely inform them that staff will assist them shortly and tag <@&1536186291417518081>.

OFFICIAL EVENT INFORMATION & KNOWLEDGE BASE:
📜 Event Details:
- Start Date & Time: Announced in <#1533506634985504909>. Advise them to check there and turn on notifications!
- 💸 Entry Fee & Discounts: The standard entry fee is 35k, but you can reduce the price by 3k per invite.
- 💰 Earning Cash: After participating in the event, players can earn extra cash by inviting other interested players.
- 📍 Payment Location: Paid after joining the VIP server at Howling Peak.
- 🚪 Gate Opening: Once everyone pays, the owner guides the group to the gate and unlocks it.
- ⚔️ Parkour & Reward: Infinite attempts on the parkour after passing the gate until claiming the sword!
- ✅ Legitimacy Check: Refer to <#1534230669729861652> for player feedback.

👥 Invite Rules:
- Qualified Invites: Only invite people who are genuinely interested in participating.
"""

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

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

def get_available_category(guild, category_ids):
    for cat_id in category_ids:
        category = guild.get_channel(cat_id)
        if category and isinstance(category, discord.CategoryChannel):
            if len(category.channels) < 50:
                return category
    return None

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

async def keep_typing(channel):
    while True:
        await channel.typing()
        await asyncio.sleep(8)

# 1. AUTO WELCOME
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if not isinstance(channel, discord.TextChannel):
        return

    if not channel.category or channel.category.id != AI_ALLOWED_CATEGORY_ID:
        return

    await asyncio.sleep(4)

    welcome_text = (
        "Yes, we are glad that you would like to participate in our event!\n"
        "Please read the info above. It should be all the details you need.\n"
        "Let me know if you understand all and don't hesitate to ask any further questions."
    )

    try:
        async for msg in channel.history(limit=5, oldest_first=True):
            if msg.author.bot:
                await msg.reply(welcome_text)
                return
        await channel.send(welcome_text)
    except Exception as e:
        print(f"Error sending auto-welcome: {e}")

# 2. ON MESSAGE (KATEGORIE-STEUERUNG)
@bot.event
async def on_message(message: discord.Message):
    # Bots generell ignorieren
    if message.author.bot:
        return

    # STRENGER KATEGORIE-FILTER: Nur verarbeiten, wenn sich das Ticket in der AI_ALLOWED_CATEGORY befindet!
    if not message.channel.category or message.channel.category.id != AI_ALLOWED_CATEGORY_ID:
        await bot.process_commands(message)
        return

    # Prüfen, ob die Nachricht von einem Staff-Mitglied stammt
    is_staff = False
    if isinstance(message.author, discord.Member):
        has_staff_role = any(role.id == STAFF_ROLE_ID or role.name in EXCLUDED_ROLES for role in message.author.roles)
        if has_staff_role or message.author.guild_permissions.administrator:
            is_staff = True

    # WENN EIN STAFF SCHREIBT: Ticket in die Pause-Kategorie verschieben!
    if is_staff:
        pause_category = message.guild.get_channel(STAFF_PAUSE_CATEGORY_ID)
        if pause_category and isinstance(pause_category, discord.CategoryChannel):
            try:
                await message.channel.edit(category=pause_category)
            except discord.Forbidden:
                print("Fehler: Bot hat keine Berechtigung, die Kategorie zu ändern.")
        await bot.process_commands(message)
        return

    # KI ANTWORT GENERIEREN (Gilt nur für Nachrichten von normalen Spielern in der KI-Kategorie)
    if gemini_client:
        typing_task = asyncio.create_task(keep_typing(message.channel))
        
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                response = await gemini_client.aio.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=message.content,
                    config={
                        "system_instruction": AI_SYSTEM_PROMPT,
                        "temperature": 0.5,
                    }
                )
                break
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                
                typing_task.cancel()
                print(f"Fehler bei Gemini API Aufruf: {e}")
                await message.reply("⚠️ *The AI service is currently busy. Please send your message once more!*")
                await bot.process_commands(message)
                return

        typing_task.cancel()

        if response and response.text:
            reply_text = response.text.strip()

            trigger_found = False
            if "[TRIGGER_PARTICIPATE]" in reply_text:
                trigger_found = True
                reply_text = reply_text.replace("[TRIGGER_PARTICIPATE]", "").strip()

            await message.reply(
                reply_text,
                allowed_mentions=discord.AllowedMentions(roles=True, users=True)
            )

            if trigger_found:
                await execute_participate_logic(message.guild, message.channel)

    await bot.process_commands(message)

# =====================================================================
# SLASH COMMANDS
# =====================================================================

@bot.tree.command(name="botresume", description="Moves channel back to AI allowed category to re-enable AI support")
async def botresume(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    channel = interaction.channel

    ai_category = guild.get_channel(AI_ALLOWED_CATEGORY_ID)
    if not ai_category or not isinstance(ai_category, discord.CategoryChannel):
        await interaction.followup.send("❌ Target AI category was not found!", ephemeral=True)
        return

    try:
        await channel.edit(category=ai_category)
        await interaction.followup.send("🤖 **AI Support re-enabled! Channel moved back to AI category.**", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Bot misses permissions to move channel back.", ephemeral=True)


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


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: No DISCORD_TOKEN found!")
    else:
        bot.run(BOT_TOKEN)
