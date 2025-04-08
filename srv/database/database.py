import pymysql
import logging
import json
from dotenv import load_dotenv
import os
from sensitiveVariables import sensitiveVariables
import asyncio

sensitivevars = sensitiveVariables.SensitiveVariables()
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class MariaDB:
    """
    Class to interact with a MariaDB database using pymysql.
    """

    def __init__(self):
        """
        Initialize the MariaDB class with database connection parameters.
        """
        self.db_data = {
            "host": sensitivevars.database['host'],
            "user": sensitivevars.database['user'],
            "password": sensitivevars.database['password'],
            "database": sensitivevars.database['database']
        }

    async def connect_db(self, retries=3):
        """
        Establish a connection to the MariaDB database with retry logic.

        Args:
            retries (int): Number of retry attempts in case of connection failure. Defaults to 3.

        Returns:
            pymysql connection object
        """
        attempt = 0
        while attempt < retries:
            try:
                connection = pymysql.connect(
                    host=self.db_data["host"],
                    user=self.db_data["user"],
                    password=self.db_data["password"],
                    database=self.db_data["database"],
                )
                logger.info("Successfully connected to the database.")
                return connection
            except pymysql.MySQLError as e:
                attempt += 1
                logger.error(f"Database connection failed (attempt {attempt}/{retries}): {e}")
                if attempt == retries:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def log_filter(self, message, author, channel, time_sent, harmful_word):
        """
        Log filtered messages to the database.

        Parameters:
        - message: The content of the message.
        - author: The author of the message.
        - channel: The channel where the message was sent.
        - time_sent: The time when the message was sent.
        - harmful_word: The harmful word detected in the message.
        """
        try:
            db = self.connect_db()
            cursor = db.cursor()

            # Ensure all inputs are strings
            message = str(message)
            author = str(author)
            channel = str(channel)
            time_sent = str(time_sent)
            harmful_word = str(harmful_word)

            insert_query = (
                "INSERT INTO messages (message, author, channel, time_sent, word) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
            logger.info("Executing filter query")
            cursor.execute(
                insert_query, (message, author, channel, time_sent, harmful_word)
            )

            db.commit()
            db.close()
        except pymysql.MySQLError as e:
            logger.error(f"Database error: {e}")

    async def log_ai(self, message, author, channel, time_sent, flags, scores):
        """
        Log AI-generated messages to the database.

        Parameters:
        - message: The content of the message.
        - author: The author of the message.
        - channel: The channel where the message was sent.
        - time_sent: The time when the message was sent.
        - flags: Flags associated with the AI message.
        - scores: The scores for each flag associated with the AI message.
        """
        try:
            db = self.connect_db()
            cursor = db.cursor()

            # Ensure all inputs are strings or properly serialized
            message = str(message)
            author = str(author)
            channel = str(channel)
            time_sent = str(time_sent)
            flags = str(flags)
            scores = json.dumps(scores)  # Serialize scores to JSON

            insert_query = (
                "INSERT INTO ai_messages "
                "(message, author, channel, time_sent, flags, scores) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            )
            logger.info("Executing AI log query")
            cursor.execute(
                insert_query, (message, author, channel, time_sent, flags, scores)
            )

            db.commit()
            db.close()
        except pymysql.MySQLError as e:
            logger.error(f"Database error: {e}")

    async def retrieve_user_data(self, ctx):
        """
        Retrieve user data from the database and send it to the context.

        Parameters:
        - ctx: The context from which the request was made.
        """
        author = ctx.author
        try:
            db = self.connect_db()
            cursor = db.cursor()

            query = "SELECT * FROM messages WHERE author = %s;"
            cursor.execute(query, (author.name,))
            logger.info(f"Retrieved data for user: {author.name}")

            rows = cursor.fetchall()
            row_list = [row for row in rows]

            await ctx.send(row_list)
            db.close()
        except pymysql.MySQLError as e:
            logger.error(f"Database error: {e}")
    

    async def scan_database_for_word(self, word):
        """
        Scans the database for messages containing a specific word.

        This function searches the 'messages' table in the database for any entries
        where the 'message' column contains the specified word.

        Parameters:
        word (str): The word to search for in the database messages.

        Returns:
        list: A list of tuples, where each tuple represents a row from the database
              that contains the specified word. Returns an empty list if no matches
              are found or if there's a database error.

        Raises:
        pymysql.MySQLError: If there's an error in database connection or query execution.
        """
        try:
            db = self.connect_db()
            cursor = db.cursor()

            query = "SELECT * FROM messages WHERE message LIKE %s;"
            cursor.execute(query, (f"%{word}%",))

            rows = cursor.fetchall()

            db.close()

            return rows
        except pymysql.MySQLError as e:
            logger.error(f"Database error while scanning for word '{word}': {e}")
            return []

