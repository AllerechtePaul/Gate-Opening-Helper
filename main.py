import os
import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================
# EINSTELLUNGEN (Exakte Rollennamen)
# =====================================================================
# Liest den Token sicher aus den Railway-Variablen ab:
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Rollen, die bei /participate IGNORIERT werden:
EXCLUDED_ROLES = [
    "Participant",
    "Former Participant",
    "Admin",
    "Trial Moderator",
    "Moderator",
    "Ticket King"  # Zur Sicherheit auch den Ticket-Bot ausschließen
]

# Die Rolle, die vergeben werden soll:
TARGET_ROLE_NAME = "Participant"

# Kategorie-Einstellung für /sayalltickets (None = nur unkategorisierte Kanäle):
TICKET_CATEGORY_NAME = None  
# =====================================================================

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Erfordert 'Server Members Intent' im Developer Portal!
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash-Commands wurden erfolgreich synchronisiert!")

bot = EventBot()

@bot.event
async def on_ready():
    print(f"Bot ist online! Eingeloggt als: {bot.user.name}")
    print("-----------------------------------------------------")


# -------------------------------------------------------------------
# 1. BEFEHL: /participate
# -------------------------------------------------------------------
@bot.tree.command(name="participate", description="Vergibt die Participant-Rolle an neue Teilnehmer im Ticket")
@app_commands.checks.has_permissions(administrator=True)
async def participate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    target_role = discord.utils.get(guild.roles, name=TARGET_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Die Rolle **'{TARGET_ROLE_NAME}'** wurde auf dem Server nicht gefunden!", ephemeral=True)
        return

    assigned_count = 0

    for member in channel.members:
        if member.bot:
            continue  # Bots überspringen

        # Prüfen, ob der User EINE der Ausschluss-Rollen hat
        has_excluded_role = any(role.name in EXCLUDED_ROLES for role in member.roles)
        
        # Zusätzlich Administrator-Rechte berücksichtigen
        if member.guild_permissions.administrator:
            has_excluded_role = True

        # Wenn der User KEINE der geblockten Rollen hat -> Rolle vergeben
        if not has_excluded_role:
            try:
                await member.add_roles(target_role)
                assigned_count += 1
            except discord.Forbidden:
                print(f"Fehler: Rolle konnte an {member.name} nicht vergeben werden.")

    await interaction.followup.send(f"✅ Rolle **{target_role.name}** an **{assigned_count}** neue Teilnehmer vergeben!", ephemeral=True)


# -------------------------------------------------------------------
# 2. BEFEHL: /paid
# -------------------------------------------------------------------
@bot.tree.command(name="paid", description="Markiert das Ticket als bezahlt und setzt ein ✅ im Kanalnamen")
@app_commands.checks.has_permissions(administrator=True)
async def paid(interaction: discord.Interaction):
    channel = interaction.channel

    if channel.name.startswith("✅"):
        await interaction.response.send_message("⚠️ Dieses Ticket ist bereits als bezahlt markiert!", ephemeral=True)
        return

    new_name = f"✅-{channel.name}"

    try:
        await channel.edit(name=new_name)
        await interaction.response.send_message(f"✅ Ticket wurde umbenannt in **{new_name}**!")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Der Bot hat keine Rechte, diesen Kanal umzubenennen.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)


# -------------------------------------------------------------------
# 3. BEFEHL: /sayalltickets
# -------------------------------------------------------------------
@bot.tree.command(name="sayalltickets", description="Sendet eine Durchsage an alle aktiven Tickets")
@app_commands.describe(nachricht="Die Nachricht für alle Tickets")
@app_commands.checks.has_permissions(administrator=True)
async def sayalltickets(interaction: discord.Interaction, nachricht: str):
    await interaction.response.defer(ephemeral=True)

    sent_count = 0
    guild = interaction.guild

    for channel in guild.text_channels:
        is_ticket = False
        if TICKET_CATEGORY_NAME is None and channel.category is None:
            is_ticket = True
        elif channel.category and channel.category.name == TICKET_CATEGORY_NAME:
            is_ticket = True

        if is_ticket:
            try:
                await channel.send(nachricht)
                sent_count += 1
            except discord.Forbidden:
                pass

    await interaction.followup.send(f"📢 Nachricht erfolgreich an **{sent_count} Tickets** gesendet!", ephemeral=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: Kein BOT_TOKEN in den Umgebungsvariablen gefunden!")
    else:
        bot.run(BOT_TOKEN)