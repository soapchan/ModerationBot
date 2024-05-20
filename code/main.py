import json
import logging
import time

import discord
from discord.ext import commands, tasks
import mariadb
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Setting the logger


class Main:
    def __init__(self, ai_key, bot_class_var):
        self.status = discord.Activity(type=discord.ActivityType.watching, name="for =help", start=0)
        # start=0 is the timestamp for when activity starts
        self.client = OpenAI(api_key=ai_key)
        self.bot = bot_class_var

    async def get_flagged_categories(self, text):
        response = self.client.moderations.create(input=text)
        response_dict = response.model_dump()
        results = response_dict['results'][0]
        flagged_categories = {category: flagged for category, flagged in results['categories'].items() if flagged}
        logging.info(f"Checked text {text}")
        return flagged_categories

    async def send_message(self, channel_id, *, message):
        channel = self.bot.get_channel(channel_id)
        embed = discord.Embed(description=message, color=discord.Color.red(), title="Harmful message")
        await channel.send(embed=embed)  # Send the embed
        logging.info(f"Created Embed for harmful message {message}")

    async def send_message_dm(self, *, message, author):
        embed = discord.Embed(description=message, color=discord.Color.red(), title="Vulgar message")
        await author.send(embed=embed)  # Send the embed
        logging.info(f"Created Embed for harmful message {message}")


class MariaDB:
    def __init__(self):
        self.host = "localhost"
        self.user = "tybalt"
        self.password = "OWuq)xg4j7mdU2hr"
        self.database = "tybalt-logs"

    def log_filter(self, message, author, channel, time_sent, harmful_word):
        try:
            db = mariadb.connect(
                host=self.host,
                user=self.user,
                passwd=self.password,
                database=self.database
            )

            cursor = db.cursor()

            insert_into_table = ("INSERT INTO messages (message, author, channel, time_sent, word) "
                                 "VALUES (?, ?, ?, ?, ?)")
            cursor.execute(insert_into_table, (message, author.name, channel.name, time_sent, harmful_word))
            logging.info(f"Run database command {insert_into_table} with values {message},"
                         f" {author.name},"
                         f" {channel.name},"
                         f" {time_sent},"
                         f" {harmful_word}")
            db.commit()
            db.close()
            logging.info(f"Logged harmful word to database")
        except mariadb.Error as e:
            logging.error(e)

    def log_ai(self, message, author, channel, time_sent, flags):
        try:
            db = mariadb.connect(
                host=self.host,
                user=self.user,
                passwd=self.password,
                database=self.database
            )

            cursor = db.cursor()

            insert_into_table = ("INSERT INTO ai_messages (message, author, channel, time_sent, flags) "
                                 "VALUES (?, ?, ?, ?, ?)")
            cursor.execute(insert_into_table, (message, author.name, channel.name, time_sent, flags))
            logging.info(f"Run AI database command {insert_into_table} with values {message},"
                         f" {author.name},"
                         f" {channel.name},"
                         f" {time_sent},"
                         f" {flags}")
            db.commit()
            db.close()
            logging.info("Logged AI report to database")
        except mariadb.Error as e:
            logging.error(e)


maria_db = MariaDB()


def setup_bot():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='==', intents=intents)
    ai_key = "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"
    bypass_roles = ["Owner", "Admin", "General Manager", "Community manager", "Staff manager",
                    "Events Manager", "Consultant", "Senior Moderator"]
    bypass_roles_id = [272156013493485568,
                       687271112144322604,
                       1214710025352781894,
                       272157047498473474,
                       1174432041627041792,
                       1216163713480921170,
                       1215712136194555984,
                       1241818185489977404,
                       1215387561841791058,
                       272157265111416833]
    debug_role = ["bot debug perms"]
    start_time = int(time.time())

    main = Main(ai_key, bot)



    @bot.event
    async def on_ready():
        """Logs in the bot."""
        tybalt_logs = bot.get_channel(982548416376750100)
        logging.info(f"Logged in as {bot.user.name}")
        await bot.change_presence(activity=main.status)
        message = (
            f"AutoMod started up at <t:{start_time}>"
        )
        embed = discord.Embed(description=message, color=discord.Color.green(), title="**AutoMod Online**")
        await tybalt_logs.send(embed=embed)
        check_for_spammers.start()
        logging.info("Started spammer check")



    @bot.event
    async def on_message(message):
        """Handles incoming messages."""
        user_roles = [role.name for role in message.author.roles]

        if not any(role in user_roles for role in bypass_roles) or any(role in user_roles for role in debug_role):
            if message.author == bot.user or message.author == discord.Member.bot:
                return

            """Part for AI mod"""

            flagged_categories = await main.get_flagged_categories(text=message.content)
            if flagged_categories:
                await main.send_message(channel_id=1226672487966834778,
                                        message=f"Harmful message: {message.content}.\n"
                                                f"Category: {flagged_categories}.\n "
                                                f"Sent by: {message.author}.\n"
                                                f"Channel: {message.channel}.\n"
                                                f"Timespamp: {message.created_at}.")
                logging.info(f"User {message.author} has been privately messaged about their vulgar message")
                await message.add_reaction("⚠️")
                key = list(flagged_categories.keys())[0]
                maria_db.log_ai(message=message.content,
                                author=message.author,
                                channel=message.channel,
                                time_sent=message.created_at,
                                flags=key.strip("''"))

            """Part for bad words list"""

            with open("nono_words.json", "r") as file:
                data = json.loads(file.read())
            words = message.content.split()
            for word in data:
                if word in words:
                    logging.info(f"Bad word ({word}) detected")
                    await send_message(channel_id=999718985098600539,
                                       message=f"Harmful word: {word}.\n"
                                               f"Message: {message.content}.\n "
                                               f"Sent by: {message.author}.\n"
                                               f"Channel: {message.channel}.\n"
                                               f"Timespamp: {message.created_at}."
                                       )
                    await message.channel.send(f"Please do not say vulgar things {message.author.mention}")
                    maria_db.log_filter(message=message.content,
                                        author=message.author,
                                        channel=message.channel,
                                        time_sent=message.created_at,
                                        harmful_word=word)
                    await message.delete()

                else:
                    logging.info(f"Message was innocent")

        else:
            logging.info(f"Message sent by {message.author} was ignored through senior staff status")
            await bot.process_commands(message)


    @tasks.loop(hours=1)
    async def check_for_spammers():
        logging.info("Started spammer check")
        guild_id = bot.get_guild(272148882048155649)
        channel = bot.get_channel(1239179624689434716)
        members = guild_id.members
        for member in members:

            if member.public_flags.spammer:
                message = (
                    f"User {member.mention} has been flagged as suspicious."
                )
                embed = discord.Embed(description=message, color=discord.Color.red(), title="**Suspicious Account**")

                await channel.send(embed=embed)
                logging.info(f"User {member.name} has been flagged as potential spammer.")


    async def send_message(channel_id, message):
        channel = bot.get_channel(channel_id)
        embed = discord.Embed(description=message, color=discord.Color.red(), title="Harmful word in message")
        await channel.send(embed=embed)


    """Commands are from here below"""


    @bot.command(name="uptime")
    @commands.has_any_role(272156013493485568,
                           687271112144322604,
                           1214710025352781894,
                           272157047498473474,
                           1174432041627041792,
                           1216163713480921170,
                           1215712136194555984,
                           1241818185489977404,
                           1215387561841791058,
                           272157265111416833)
    async def uptime(ctx):

        message = (
            f"AutoMod has been online for <t:{start_time}:R>"
        )

        embed = discord.Embed(description=message, color=discord.Color.green(), title="Uptime")
        await ctx.send(embed=embed)


    @bot.command(name="checkflags")
    @commands.has_any_role(272156013493485568,
                           687271112144322604,
                           1214710025352781894,
                           272157047498473474,
                           1174432041627041792,
                           1216163713480921170,
                           1215712136194555984,
                           1241818185489977404,
                           1215387561841791058,
                           272157265111416833)
    async def check_flags(ctx):
        """Checks the flags of a user"""
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
            flag_list = []
            flags = target.public_flags

            for flag in flags:
                flag_list.append(flag)
            message = (
                flag_list
            )
            embed = discord.Embed(description=message, color=discord.Color.green(), title=f"Flags of {target.name}")
            await ctx.channel.send(embed=embed)
            logging.info(f"Presented tags of {target.name}")
        else:
            flag_list = []
            author = ctx.author
            flags = author.public_flags

            for flag in flags:
                flag_list.append(flag)
            message = (
                flag_list
            )
            embed = discord.Embed(description=message, color=discord.Color.green(), title=f"Flags of {author.name}")
            await ctx.channel.send(embed=embed)
            logging.info(f"Presented tags of {author.name}")


    @bot.command(name="spamcheck")
    @commands.has_any_role(272156013493485568,
                           687271112144322604,
                           1214710025352781894,
                           272157047498473474,
                           1174432041627041792,
                           1216163713480921170,
                           1215712136194555984,
                           1241818185489977404,
                           1215387561841791058,
                           272157265111416833)
    async def check_for_spam_warnings(ctx):
        """Check the server for any potential spammers"""
        await check_for_spammers()


    return bot


if __name__ == "__main__":
    bot = setup_bot()
    bot.run("OTc0NDc1MTYxOTI1NDU5OTk4.G6M3rx.sp4a_xyFDoJHws5hpGJ3w28pab9A-ETfNxOaRk")
