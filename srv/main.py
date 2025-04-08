import json
import logging
import time
import discord
from discord.ext import commands, tasks
from openai import OpenAI
from database import database
from sensitiveVariables import sensitiveVariables
from ai import autoMod
from colorama import Fore, Style


sensitivevariables = sensitiveVariables.SensitiveVariables()
database = database.MariaDB()
staff_roles = sensitivevariables.staff_roles
automod = autoMod.AutoMod(sensitivevariables.OPENAI_key)

# Define a new logging level for success messages
SUCCESS_LEVEL_NUM = 25
NOTICE_LEVEL_NUM = 24
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

def notice(self, message, *args, **kws):
    if self.isEnabledFor(NOTICE_LEVEL_NUM):
        self._log(NOTICE_LEVEL_NUM, message, args, **kws)

logging.Logger.success = success
logging.Logger.notice = notice

# Custom logging formatter to add colors to log messages based on their severity
class CustomFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.WARNING:  # If the log level is WARNING
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"

        elif record.levelno == logging.ERROR:  # If the log level is ERROR
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"

        elif record.levelno == logging.DEBUG:  # If the log level is DEBUG
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}" 

        elif record.levelno == SUCCESS_LEVEL_NUM:
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"  # If the log level is SUCCESS
        
        elif record.levelno == NOTICE_LEVEL_NUM:
            record.msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"  # If the log level is NOTICE
        return super().format(record)

# Configure logging to include timestamps and log levels in the output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Apply the custom formatter to all existing log handlers to ensure colored output
for handler in logging.getLogger().handlers:
    handler.setFormatter(CustomFormatter(handler.formatter._fmt))

logger = logging.getLogger(__name__)


class Main:
    def __init__(self, ai_key, bot_class_var):
        self.status = discord.Activity(type=discord.ActivityType.watching, name="for =help", start=0)
        # start=0 is the timestamp for when activity starts
        self.client = OpenAI(api_key=ai_key)
        self.bot = bot_class_var


    async def create_embed(self, message, author=None, title="", color=discord.Color.default()):
        """
        Creates a Discord embed object with the specified content and style.

        Args:
            message (str): The main content of the embed.
            author (discord.Member, optional): The author of the message. Defaults to None.
            title (str, optional): The title of the embed. Defaults to an empty string.
            color (discord.Color, optional): The color of the embed. Defaults to discord.Color.default().

        Returns:
            discord.Embed: The created embed object with the specified content and style.
        """
        embed = discord.Embed(description=message, color=color, title=title)
        if author:
            embed.set_footer(text=f"Sent by: {author}")
        return embed


    async def send_embed(self, *, channel_id=None, message, author=None, title="", color=discord.Color.default(), dm=False):
        if not dm and channel_id is None:
            raise ValueError("channel_id must be provided when dm is False.")
        if dm and author is None:
            raise ValueError("author must be provided when dm is True.")
        """
        Send an embedded message to a specified channel or user.

        Args:
            channel_id (int, optional): The ID of the channel to send the embed to. Defaults to None.
            message (str): The main content of the embed.
            author (discord.Member, optional): The author of the message. Defaults to None.
            title (str, optional): The title of the embed. Defaults to an empty string.
            color (discord.Color, optional): The color of the embed. Defaults to discord.Color.default().
            dm (bool, optional): Whether to send the embed as a DM. Defaults to False.

        Returns:
            None
        """
        embed = await self.create_embed(message=message, author=author, title=title, color=color)
        if dm:
            dm_channel = author.dm_channel
            if dm_channel is None:
                dm_channel = await author.create_dm()
            await dm_channel.send(embed=embed)
            logger.info(f"Sent Embed DM to {author}: {message}")
        else:
            channel = self.bot.get_channel(channel_id)
            await channel.send(embed=embed)
            logger.notice(f"Created Embed for message {message}")


    async def send_dm(self, *, message, author):
        """
        Sends a direct message to a specified user.

        This function checks if the user has an existing DM channel. If not, it creates one
        and sends the provided message to the user.

        Args:
            message (str): The content of the message to be sent.
            author (discord.Member): The user to whom the DM will be sent.

        Returns:
            None
        """
        dm_channel = author.dm_channel
        if dm_channel is None:
            dm_channel = await author.create_dm()
        await dm_channel.send(message)
        logger.info(f"Sent DM to {author}: {message}")



def setup_bot():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='==', intents=intents)
    bypass_roles = ["Owner", "Admin", "General Manager", "Community manager", "Staff manager",
                    "Events Manager", "Consultant", "Senior Moderator", "Developer"]
    debug_role = ["bot debug perms"]
    start_time = int(time.time())

    main = Main(sensitivevariables.OPENAI_key, bot)


    @bot.event
    async def on_ready():
        """Logs in the bot."""
        tybalt_logs = bot.get_channel(982548416376750100)
        logger.info(f"Logged in as {bot.user.name}")
        await bot.change_presence(activity=main.status)
        message = (
            f"AutoMod started up at <t:{start_time}>"
        )
        await main.send_embed(channel_id=tybalt_logs.id, message=message, title="**AutoMod Online**", color=discord.Color.green())
        check_for_spammers.start(manual=False)


    @bot.event
    async def on_message(message):
        """Handles incoming messages."""
        if message.author.bot:
            return
        user_roles = [role.name for role in message.author.roles]

        if not any(role in user_roles for role in bypass_roles) or any(role in user_roles for role in debug_role):
            if message.author == bot.user:
                return

            """Part for AI mod"""

            flagged_categories = automod.get_flagged_categories(text=message.content)
            if flagged_categories:
                await main.send_embed(channel_id=1250475863976312944,
                                        message=f"Harmful message: {message.content}.\n"
                                                f"Category: {automod.categories['flagged_categories']}.\n "
                                                f"Scores: {automod.categories['category_scores']}\n"
                                                f"Sent by: {message.author}.\n"
                                                f"Channel: {message.channel}.\n"
                                                f"Timestamp: {message.created_at}.",
                                        author=message.author)
                                        
                await database.log_ai(message=message.content,
                                      author=message.author,
                                      channel=message.channel,
                                      time_sent=message.created_at,
                                      flags=automod.categories["flagged_categories"],
                                      scores=automod.categories["category_scores"])

            """Part for bad words list"""

            with open("srv/nono_words.json", "r") as file:
                data = json.loads(file.read())
            words = message.content.split()
            for word in data:
                if word in words:
                    logger.info(f"Bad word ({word}) detected")
                    await main.send_embed(channel_id=1250475863976312944,
                                            message=f"Offending word: {word}.\n"
                                                    f"Message: {message.content}.\n "
                                                    f"Sent by: {message.author}.\n"
                                                    f"Channel: {message.channel}.\n"
                                                    f"Timestamp: {message.created_at}.",
                                            author=message.author,
                                            title="Harmful word in message",
                                            color=discord.Color.red())
                    await message.channel.send(f"Please do not say vulgar things {message.author.mention}")
                    await database.log_filter(message=message.content,
                                              author=message.author,
                                              channel=message.channel,
                                              time_sent=message.created_at,
                                              harmful_word=word)
                    
                    await main.send_embed(author=message.author,
                     message=f"Hey {message.author}, your message goes against our community guidelines. "
                            f"Please keep things respectful to maintain a positive environment!\n\n"
                            f"Offending word: {word}.\n"
                            f"Message: {message.content}.\n"
                            f"Sent by: {message.author}.\n"
                            f"Channel: {message.channel}.\n"
                            f"Timestamp: {message.created_at}.",
                    title="**Harmful language**",
                    color=discord.Color.red(),
                    dm=True)
                    await message.delete()
        else:
            await bot.process_commands(message)


    @tasks.loop(minutes=1)
    async def check_for_spammers(manual):
        """
        Checks the server for potential spammers and sends notifications.

        This function iterates through all members of a specified guild and checks if any member
        has been flagged as a spammer. If a spammer is found, an embedded message is sent to a
        specified channel. The function can be triggered manually or automatically.

        Args:
            manual (bool): Indicates whether the check was initiated manually. If True, a log
                           message and an embed are sent indicating a manual start.

        Returns:
            None
        """
        logger.notice(f"Started spammer check: manually?: {manual}")
        if manual:
            logger.notice("Started spammer check manually")
            await main.send_embed(channel_id=1250475863976312944, message="Started spammer check manually", title="**Spammer Check**", color=discord.Color.green())
        else:
            logger.info("Started spammer check automatically")
        guild_id = bot.get_guild(272148882048155649)
        channel = bot.get_channel(1250475863976312944)
        members = guild_id.members
        if len(members) == 0 and manual:
            await main.send_embed(channel_id=channel.id, message="No suspicious accounts found.", title="**No Suspicious Accounts**", color=discord.Color.green())
            logger.info(f"No suspicious accounts found.")
        else:
            for member in members:
                if member.public_flags.spammer:
                    await main.send_embed(channel_id=channel.id,
                                            message=f"User {member.mention} ({member.name}) has been flagged as suspicious.",
                                            title="**Suspicious Account**", color=discord.Color.red())
                    logger.info(f"User {member.name} has been flagged as potential spammer.")


    """Commands are from here below"""
    def get_staff_role_ids():
        return list(staff_roles.values())


    @bot.command(name="uptime")
    @commands.has_any_role(*get_staff_role_ids())
    async def uptime(ctx):
        """Checks the uptime of the bot"""
        message = (
            f"AutoMod went online <t:{start_time}:R>"
        )

        await main.send_embed(channel_id=ctx.channel.id, message=message, title="Uptime", color=discord.Color.green())


    @bot.command(name="checkflags")
    @commands.has_any_role(*get_staff_role_ids())
    async def check_flags(ctx):
        """
        Asynchronously checks and displays the flags of a user.
        If a user is mentioned in the context message, retrieves and displays the flags of the mentioned user.
        If no user is mentioned, retrieves and displays the flags of the message author.
        Args:
            ctx (commands.Context): The context in which the command was invoked.
        Returns:
            None
        """
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
            flag_list = []
            flags = target.public_flags

            for flag in flags:
                flag_list.append(flag)
            message = (
                flag_list
            )
            await main.send_embed(channel_id=ctx.channel.id, message=message, title=f"Flags of {target.name}", color=discord.Color.green())
            logger.info(f"Presented tags of {target.name}")
        else:
            flag_list = []
            author = ctx.author
            flags = author.public_flags

            for flag in flags:
                flag_list.append(flag)
            message = (
                flag_list
            )
            await main.send_embed(channel_id=ctx.channel.id, message=message, title=f"Flags of {author.name}", color=discord.Color.green())
            logger.info(f"Presented tags of {author.name}")


    @bot.command(name="spamcheck")
    @commands.has_any_role(*get_staff_role_ids())
    async def check_for_spam_warnings(ctx):
        """Check the server for any potential spammers"""
        await check_for_spammers(manual=True)


    @bot.command(name="scan")
    @commands.has_any_role(*get_staff_role_ids())
    async def database_query_user(ctx):
        """Check the database for messages from a specific user"""
        await database.retrieve_user_data(ctx=ctx)

    
    @bot.command(name="wordScan")
    @commands.has_any_role(*get_staff_role_ids())
    async def database_query_word(ctx, word):
        """
        Scans the database for messages containing a specific word.
        """
        # Call the method without the ctx parameter
        rows = await database.scan_database_for_word(word=word)

        if rows:
            # Format and send the results
            results = "\n".join([str(row) for row in rows])
            await ctx.send(f"Found the following messages:\n{results}")
        else:
            await ctx.send(f"No messages found containing the word '{word}'.")


    return bot


if __name__ == "__main__":
    bot = setup_bot()
    bot.run(sensitivevariables.bot_token)
