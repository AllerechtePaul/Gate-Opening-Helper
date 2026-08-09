import os
import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================
# EINSTELLUNGEN
# =====================================================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Rollen, die bei /participate IGNORIERT werden:
EXCLUDED_ROLES = [
    "Participant",
    "Former Participant",
    "Admin",
    "Trial Moderator",
    "Moderator",
    "Ticket King"
]

# Rollennamen für /participate und /paid:
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
# =====================================================================

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Benötigt für Rollen-Abfragen & -Änderungen
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

    target_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Die Rolle **'@{PARTICIPANT_ROLE_NAME}'** wurde auf dem Server nicht gefunden!", ephemeral=True)
        return

    assigned_count = 0

    for member in channel.members:
        if member.bot:
            continue

        has_excluded_role = any(role.name in EXCLUDED_ROLES for role in member.roles)
        if member.guild_permissions.administrator:
            has_excluded_role = True

        if not has_excluded_role:
            try:
                await member.add_roles(target_role)
                assigned_count += 1
            except discord.Forbidden:
                print(f"Fehler: Rolle konnte an {member.name} nicht vergeben werden.")

    await interaction.followup.send(f"✅ Rolle **{target_role.name}** an **{assigned_count}** neue Teilnehmer vergeben!", ephemeral=True)


# -------------------------------------------------------------------
# 2. BEFEHL: /paid
# Benennt den Kanal um & wechselt @Participant zu @Former Participant
# -------------------------------------------------------------------
@bot.tree.command(name="paid", description="Markiert das Ticket als bezahlt und wandelt Participant zu Former Participant um")
@app_commands.checks.has_permissions(administrator=True)
async def paid(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    # Rollen auf dem Server suchen
    participant_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    former_role = discord.utils.get(guild.roles, name=FORMER_PARTICIPANT_ROLE_NAME)

    if not participant_role or not former_role:
        await interaction.followup.send(
            f"❌ Fehlende Rolle(n): Bitte stelle sicher, dass **'@{PARTICIPANT_ROLE_NAME}'** "
            f"und **'@{FORMER_PARTICIPANT_ROLE_NAME}'** auf dem Server existieren!",
            ephemeral=True
        )
        return

    # 1. Rollen tauschen für alle Mitglieder in diesem Kanal
    swapped_count = 0
    for member in channel.members:
        if member.bot:
            continue

        # Wenn der User die Participant-Rolle besitzt
        if participant_role in member.roles:
            try:
                await member.remove_roles(participant_role)
                await member.add_roles(former_role)
                swapped_count += 1
            except discord.Forbidden:
                print(f"Fehler: Rollen bei {member.name} konnten nicht angepasst werden.")

    # 2. Kanal umbenennen (falls noch kein Haken vorhanden)
    channel_renamed = False
    if not channel.name.startswith("✅"):
        new_name = f"✅-{channel.name}"
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    # Status-Antwort zusammenbauen
    msg = f"✅ Rollen von **{swapped_count} Usern** von `@{PARTICIPANT_ROLE_NAME}` zu `@{FORMER_PARTICIPANT_ROLE_NAME}` geändert."
    if channel_renamed:
        msg += f"\n🏷️ Kanal wurde in **{new_name}** umbenannt."
    else:
        msg += "\n⚠️ Kanalname hatte bereits das ✅-Zeichen."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 3. BEFEHL: /sayall
# Sendet Durchsagen (optional gefiltert nach Kategorie-ID)
# -------------------------------------------------------------------
@bot.tree.command(name="sayall", description="Sendet eine Durchsage an Tickets oder eine bestimmte Kategorie")
@app_commands.describe(
    nachricht="Die Nachricht, die gesendet werden soll",
    kategorie_id="OPTIONAL: Die ID der Kategorie (leer lassen = nur unkategorisierte Tickets)"
)
@app_commands.checks.has_permissions(administrator=True)
async def sayall(
    interaction: discord.Interaction, 
    nachricht: str, 
    kategorie_id: str = None
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    sent_count = 0

    # Falls eine Kategorie-ID angegeben wurde, konvertieren wir sie in einen Integer
    target_category_id = None
    if kategorie_id:
        try:
            target_category_id = int(kategorie_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Ungültige Kategorie-ID! Die ID darf nur aus Zahlen bestehen.", ephemeral=True)
            return

    for channel in guild.text_channels:
        is_target = False

        if target_category_id is not None:
            # Falls eine Kategorie-ID eingegeben wurde: Prüfen, ob der Kanal in dieser Kategorie liegt
            if channel.category and channel.category.id == target_category_id:
                is_target = True
        else:
            # Falls keine ID angegeben wurde: Nur Kanäle OHNE Kategorie ansteuern
            if channel.category is None:
                is_target = True

        if is_target:
            try:
                await channel.send(nachricht)
                sent_count += 1
            except discord.Forbidden:
                pass  # Falls dem Bot Schreibrechte im Kanal fehlen

    if target_category_id:
        await interaction.followup.send(f"📢 Nachricht erfolgreich an **{sent_count} Kanäle** der angegebenen Kategorie gesendet!", ephemeral=True)
    else:
        await interaction.followup.send(f"📢 Nachricht erfolgreich an **{sent_count} unkategorisierte Tickets** gesendet!", ephemeral=True)


# Bot starten
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: Kein DISCORD_TOKEN in den Umgebungsvariablen gefunden!")
    else:
        bot.run(BOT_TOKEN)
