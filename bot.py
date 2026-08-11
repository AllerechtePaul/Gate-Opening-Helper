import os
import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================
# SETTINGS
# =====================================================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Roles ignored by /participate:
EXCLUDED_ROLES = [
    "Participant",
    "Former Participant",
    "Admin",
    "Trial Moderator",
    "Moderator",
    "Ticket King"
]

# Role names:
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
# =====================================================================

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = EventBot()

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as: {bot.user.name}")
    print("-----------------------------------------------------")


# -------------------------------------------------------------------
# 1. COMMAND: /participate
# Adds ❗️ to channel name & assigns @Participant role
# -------------------------------------------------------------------
@bot.tree.command(name="participate", description="Assigns the Participant role and adds ❗️ to the ticket name")
async def participate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    target_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Role **'@{PARTICIPANT_ROLE_NAME}'** was not found on this server!", ephemeral=True)
        return

    # 1. Assign role to eligible members
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
                print(f"Error: Could not assign role to {member.name}.")

    # 2. Add ❗️ prefix to channel name (if not already present)
    channel_renamed = False
    if not channel.name.startswith("❗️"):
        new_name = f"❗️-{channel.name}"
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    msg = f"✅ Role **@{target_role.name}** assigned to **{assigned_count}** new participant(s)!"
    if channel_renamed:
        msg += f"\n🏷️ Ticket renamed to **{new_name}**."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 2. COMMAND: /paid
# Changes @Participant to @Former Participant & adds ✅ to ticket name
# -------------------------------------------------------------------
@bot.tree.command(name="paid", description="Marks ticket as paid and converts Participant to Former Participant")
async def paid(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    participant_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    former_role = discord.utils.get(guild.roles, name=FORMER_PARTICIPANT_ROLE_NAME)

    if not participant_role or not former_role:
        await interaction.followup.send(
            f"❌ Missing role(s): Please ensure both **'@{PARTICIPANT_ROLE_NAME}'** "
            f"and **'@{FORMER_PARTICIPANT_ROLE_NAME}'** exist on this server!",
            ephemeral=True
        )
        return

    # 1. Swap roles for channel members
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
                print(f"Error: Could not update roles for {member.name}.")

    # 2. Rename channel with ✅ prefix
    channel_renamed = False
    
    current_name = channel.name
    if current_name.startswith("❗️-"):
        current_name = current_name[2:]
    elif current_name.startswith("❗️"):
        current_name = current_name[1:]

    if not current_name.startswith("✅"):
        new_name = f"✅-{current_name}"
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    msg = f"✅ Roles updated from `@{PARTICIPANT_ROLE_NAME}` to `@{FORMER_PARTICIPANT_ROLE_NAME}` for **{swapped_count} user(s)**."
    if channel_renamed:
        msg += f"\n🏷️ Ticket renamed to **{new_name}**."
    else:
        msg += "\n⚠️ Ticket already has the ✅ mark."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 3. COMMAND: /sayall
# Sends broadcast to uncategorized tickets or a specific category ID
# -------------------------------------------------------------------
@bot.tree.command(name="sayall", description="Sends a message to tickets or a specific category")
@app_commands.describe(
    message="The message to send",
    category_id="OPTIONAL: Category ID (leave empty for uncategorized tickets)"
)
async def sayall(
    interaction: discord.Interaction, 
    message: str, 
    category_id: str = None
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    sent_count = 0

    target_category_id = None
    if category_id:
        try:
            target_category_id = int(category_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Invalid Category ID! It must contain numbers only.", ephemeral=True)
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

    if target_category_id:
        await interaction.followup.send(f"📢 Message successfully sent to **{sent_count} channel(s)** in the specified category!", ephemeral=True)
    else:
        await interaction.followup.send(f"📢 Message successfully sent to **{sent_count} uncategorized ticket(s)**!", ephemeral=True)


# Start Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: No DISCORD_TOKEN found in environment variables!")
    else:
        bot.run(BOT_TOKEN)

    if not participant_role or not former_role:
        await interaction.followup.send(
            f"❌ Missing role(s): Please ensure both **'@{PARTICIPANT_ROLE_NAME}'** "
            f"and **'@{FORMER_PARTICIPANT_ROLE_NAME}'** exist on this server!",
            ephemeral=True
        )
        return

    # 1. Swap roles for channel members
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
                print(f"Error: Could not update roles for {member.name}.")

    # 2. Rename channel with ✅ prefix
    channel_renamed = False
    
    current_name = channel.name
    if current_name.startswith("❗️-"):
        current_name = current_name[2:]
    elif current_name.startswith("❗️"):
        current_name = current_name[1:]

    if not current_name.startswith("✅"):
        new_name = f"✅-{current_name}"
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    msg = f"✅ Roles updated from `@{PARTICIPANT_ROLE_NAME}` to `@{FORMER_PARTICIPANT_ROLE_NAME}` for **{swapped_count} user(s)**."
    if channel_renamed:
        msg += f"\n🏷️ Ticket renamed to **{new_name}**."
    else:
        msg += "\n⚠️ Ticket already has the ✅ mark."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 3. COMMAND: /sayall
# Sends broadcast to uncategorized tickets or a specific category ID
# -------------------------------------------------------------------
@bot.tree.command(name="sayall", description="Sends a message to tickets or a specific category")
@app_commands.describe(
    message="The message to send",
    category_id="OPTIONAL: Category ID (leave empty for uncategorized tickets)"
)
async def sayall(
    interaction: discord.Interaction, 
    message: str, 
    category_id: str = None
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    sent_count = 0

    target_category_id = None
    if category_id:
        try:
            target_category_id = int(category_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Invalid Category ID! It must contain numbers only.", ephemeral=True)
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

    if target_category_id:
        await interaction.followup.send(f"📢 Message successfully sent to **{sent_count} channel(s)** in the specified category!", ephemeral=True)
    else:
        await interaction.followup.send(f"📢 Message successfully sent to **{sent_count} uncategorized ticket(s)**!", ephemeral=True)


# Start Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: No DISCORD_TOKEN found in environment variables!")
    else:
        bot.run(BOT_TOKEN)
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
