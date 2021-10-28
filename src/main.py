import discord
import requests
from discord import Intents
from discord.ext import commands, tasks
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from src import config
import pymysql

bot = commands.Bot(command_prefix=config.command_prefix, intents=Intents.all())
slash = SlashCommand(bot, sync_commands=True)


def connection():
    return pymysql.connect(host=config.database_host,
                           user=config.database_user,
                           password=config.database_password,
                           database=config.database_name,
                           port=config.database_port,
                           cursorclass=pymysql.cursors.DictCursor)


def check_code(code):
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute("""SELECT uuid FROM verify_codes WHERE code=%s""", code)
            return cursor.fetchone()


def delete_code(code):
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute("""DELETE FROM verify_codes WHERE code=%s""", code)
            con.commit()
            return True


def create_table():
    sql = """CREATE TABLE IF NOT EXISTS discord_users (
    uuid VARCHAR(36),
    username VARCHAR(16),
    discord_id BIGINT,
    banned BOOL
    )"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql)
            con.commit()
            return True


def get_current_nickname(uuid: str):
    r = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid.replace('-', '')}")
    return r.json()["name"]


def check_if_member_exist(uuid: str):
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute("""SELECT * FROM discord_users WHERE uuid=%s""", uuid)
            data = cursor.fetchone()
            if data:
                return data
            else:
                return False


def add_new_member_to_db(member: discord.Member, uuid: str, nick: str):
    sql = """INSERT INTO discord_users (uuid, username, discord_id, banned) VALUES (%s, %s, %s, %s)"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, (uuid, nick, member.id, False))
            con.commit()
            return True


def edit_discord_id(discord_id_old: int, discord_id_new: int):
    sql = """UPDATE discord_users SET discord_id=%s WHERE discord_id=%s"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, (discord_id_new, discord_id_old))
            con.commit()
            return True


def edit_nick(nick_old: int, nick_new: int):
    sql = """UPDATE discord_users SET username=%s WHERE username=%s"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, (nick_new, nick_old))
            con.commit()
            return True


def ban_member(user: discord.User):
    sql = """UPDATE discord_users SET banned=%s WHERE discord_id=%s"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, (True, user.id))
            con.commit()
            return True


def unban_member(user: discord.User):
    sql = """UPDATE discord_users SET banned=%s WHERE discord_id=%s"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, (False, user.id))
            con.commit()
            return True


async def give_role_and_nick(member: discord.Member, nick: str):
    role = member.guild.get_role(config.common_role_id)
    try:
        await member.add_roles(role)
        await member.edit(nick=nick)
    except discord.errors.Forbidden as e:
        print(e)


@tasks.loop(hours=24)
async def check_nicks():
    print("started")
    sql = """SELECT * FROM discord_users"""
    with connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql)
            data = cursor.fetchall()
    for user in data:
        current_nick = get_current_nickname(user["uuid"])
        try:
            if user["username"] != current_nick:
                edit_nick(user["username"], current_nick)
                await bot.get_guild(config.guild_id).get_member(user["discord_id"]).edit(nick=current_nick)
            elif bot.get_guild(config.guild_id).get_member(user["discord_id"]).display_name != current_nick:
                await bot.get_guild(config.guild_id).get_member(user["discord_id"]).edit(nick=current_nick)
        except Exception as e:
            print(e)
    print('all nicks checked')


@bot.event
async def on_ready():
    create_table()
    print("Bot is ready!")
    await bot.wait_until_ready()
    check_nicks.start()


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    if guild.id == config.guild_id:
        ban_member(user)


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    if guild.id == config.guild_id:
        unban_member(user)


@slash.slash(name="verify", guild_ids=[config.guild_id], options=[
    create_option(name="code",
                  description="Your verification code from server",
                  option_type=4,
                  required=True)
])
async def verify(ctx: SlashContext, code: int):
    data = check_code(code)
    await ctx.defer(hidden=True)
    if data:
        uuid = data["uuid"]
        member_exist = check_if_member_exist(uuid)
        if not member_exist:
            nick = get_current_nickname(uuid)
            add_new_member_to_db(ctx.author, uuid, nick)
            await give_role_and_nick(ctx.author, nick)
            await ctx.send(config.success_message, hidden=True)
        elif member_exist["discord_id"] == ctx.author.id:
            if not member_exist["banned"]:
                nick = get_current_nickname(uuid)
                await give_role_and_nick(ctx.author, nick)
                await ctx.send(config.success_message, hidden=True)
            else:
                await ctx.send(config.ban_message, hidden=True)
        elif member_exist["discord_id"] != ctx.author.id:
            if not member_exist["banned"]:
                guild = bot.get_guild(config.guild_id)
                old_member = guild.get_member(int(member_exist["discord_id"]))
                if old_member:
                    msg = config.move_message
                    msg = msg.replace("{old}", old_member.mention)
                    msg = msg.replace("{new}", ctx.author.mention)
                    await old_member.remove_roles(ctx.guild.get_role(config.common_role_id))
                    await old_member.send(msg)
                nick = get_current_nickname(uuid)
                edit_discord_id(member_exist["discord_id"], ctx.author.id)
                await give_role_and_nick(ctx.author, nick)
                await ctx.send(config.success_message, hidden=True)
            else:
                await ctx.send(config.ban_message, hidden=True)
    else:
        await ctx.send(config.error_message, hidden=True)


if __name__ == '__main__':
    bot.run(config.bot_token)
