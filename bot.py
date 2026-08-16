import os
import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================
# SETTINGS
# =====================================================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

EXCLUDED_ROLES = ["Staff", "Admin", "Trial Moderator", "Moderator", "Ticket King"]
PARTICIPANT_ROLE_NAME = "Participant"
FORMER_PARTICIPANT_ROLE_NAME = "Former Participant"
EMPLOYEE_ROLE_NAME = "Employee"

# Eigene Kategorie-Listen für jeden Befehl!
PARTICIPATE_CATEGORY_IDS = [1537245698443968583, 1538637387138072627]
WORKER_CATEGORY_IDS = [1537242203397820446]  # Falls voll, erstelle Worker 2 und trage hier die ID ein!
SPECIAL_CATEGORY_ID = 1536184549170741269
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


# -------------------------------------------------------------------
# 1. COMMAND: /participate
# -------------------------------------------------------------------
@bot.tree.command(name="participate", description="Assigns Participant role, adds ❗️ and moves ticket to participate category")
async def participate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    target_role = discord.utils.get(guild.roles, name=PARTICIPANT_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Role **'@{PARTICIPANT_ROLE_NAME}'** was not found on this server!", ephemeral=True)
        return

    # Assign role
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
                print(f"Error: Could not assign role to {member.name}.")

    # Rename channel without duplicating emojis
    clean_name = clean_channel_name(channel.name)
    new_name = f"❗️{clean_name}"
    channel_renamed = False

    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    # Find available Participate Category
    target_category = get_available_category(guild, PARTICIPATE_CATEGORY_IDS)
    channel_moved = False

    if not target_category:
        await interaction.followup.send("❌ All Participant categories are full (50/50)! Please create a new Participant category.", ephemeral=True)
        return

    if channel.category_id != target_category.id:
        try:
            await channel.edit(category=target_category)
            channel_moved = True
        except discord.Forbidden:
            print(f"Error: Could not move channel {channel.name} to category.")

    # Response
    msg = f"✅ Role **@{target_role.name}** assigned to **{assigned_count}** new participant(s)!"
    if channel_renamed:
        msg += f"\n🏷️ Ticket renamed to **{new_name}**."
    if channel_moved:
        msg += f"\n📁 Moved to category **{target_category.name}**."
    else:
        msg += f"\nℹ️ Ticket is already in **{target_category.name}**."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 2. COMMAND: /worker
# -------------------------------------------------------------------
@bot.tree.command(name="worker", description="Assigns Employee role, adds ⭐ and moves ticket to worker category")
async def worker(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    target_role = discord.utils.get(guild.roles, name=EMPLOYEE_ROLE_NAME)
    if not target_role:
        await interaction.followup.send(f"❌ Role **'@{EMPLOYEE_ROLE_NAME}'** was not found on this server!", ephemeral=True)
        return

    # Assign role
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
                print(f"Error: Could not assign role to {member.name}.")

    # Rename channel without duplicating emojis
    clean_name = clean_channel_name(channel.name)
    new_name = f"⭐{clean_name}"
    channel_renamed = False

    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
            channel_renamed = True
        except discord.Forbidden:
            pass

    # Find available Worker Category
    target_category = get_available_category(guild, WORKER_CATEGORY_IDS)
    channel_moved = False

    if not target_category:
        await interaction.followup.send("❌ All Worker categories are full (50/50)! Please create a new Worker category.", ephemeral=True)
        return

    if channel.category_id != target_category.id:
        try:
            await channel.edit(category=target_category)
            channel_moved = True
        except discord.Forbidden:
            print(f"Error: Could not move channel {channel.name} to category.")

    # Response
    msg = f"✅ Role **@{target_role.name}** assigned to **{assigned_count}** new worker(s)!"
    if channel_renamed:
        msg += f"\n🏷️ Ticket renamed to **{new_name}**."
    if channel_moved:
        msg += f"\n📁 Moved to category **{target_category.name}**."
    else:
        msg += f"\nℹ️ Ticket is already in **{target_category.name}**."

    await interaction.followup.send(msg, ephemeral=True)


# -------------------------------------------------------------------
# 3. COMMAND: /paid
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

    clean_name = clean_channel_name(channel.name)
    new_name = f"✅{clean_name}"
    channel_renamed = False

    if channel.name != new_name:
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
# 4. COMMAND: /sayall
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


# -------------------------------------------------------------------
# 5. COMMAND: /specialticket
# -------------------------------------------------------------------
@bot.tree.command(name="specialticket", description="Moves the current ticket to the Special Category")
async def specialticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    target_category = guild.get_channel(SPECIAL_CATEGORY_ID)

    if not target_category or not isinstance(target_category, discord.CategoryChannel):
        await interaction.followup.send(f"❌ Category with ID `{SPECIAL_CATEGORY_ID}` was not found!", ephemeral=True)
        return

    if channel.category_id == SPECIAL_CATEGORY_ID:
        await interaction.followup.send("⚠️ This ticket is already in the Special Category!", ephemeral=True)
        return

    try:
        await channel.edit(category=target_category)
        await interaction.followup.send(f"📁 Ticket successfully moved to **{target_category.name}**!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot does not have permissions to move this channel.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error while moving ticket: {e}", ephemeral=True)


# -------------------------------------------------------------------
# 6. COMMAND: /movechannel
# -------------------------------------------------------------------
@bot.tree.command(name="movechannel", description="Moves the current channel to a specific category ID")
@app_commands.describe(category_id="The ID of the target category")
async def movechannel(interaction: discord.Interaction, category_id: str):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    channel = interaction.channel

    try:
        parsed_category_id = int(category_id.strip())
    except ValueError:
        await interaction.followup.send("❌ Invalid Category ID! It must contain numbers only.", ephemeral=True)
        return

    target_category = guild.get_channel(parsed_category_id)

    if not target_category or not isinstance(target_category, discord.CategoryChannel):
        await interaction.followup.send(f"❌ Category with ID `{parsed_category_id}` was not found!", ephemeral=True)
        return

    if channel.category_id == parsed_category_id:
        await interaction.followup.send("⚠️ This channel is already in the specified category!", ephemeral=True)
        return

    try:
        await channel.edit(category=target_category)
        await interaction.followup.send(f"📁 Channel successfully moved to **{target_category.name}**!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot does not have permissions to move this channel.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error while moving channel: {e}", ephemeral=True)


# Start Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: No DISCORD_TOKEN found in environment variables!")
    else:
        bot.run(BOT_TOKEN)
