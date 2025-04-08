import os
from dotenv import load_dotenv


load_dotenv()


class SensitiveVariables:
    def __init__(self):
        self.OPENAI_key = os.getenv("OPENAI_API_KEY")
        self.bot_token = os.getenv("BOT_TOKEN")
        self.staff_roles = {
            "owner": 272156013493485568,
            "admin": 687271112144322604,
            "general manager": 1214710025352781894,
            "developer": 272157047498473474,
            "community manager": 1174432041627041792,
            "staff manager": 1216163713480921170,
            "events manager": 1215712136194555984,
            "media manager": 1241818185489977404,
            "consultant": 1215387561841791058,
            "build coach": 1229101678234566806,
            "sr moderator": 272157265111416833,
            "jr moderator": 1121110303330013267,
            "moderator": 272157324179800065,
            "architect": 272157380563697675,
            "builder": 673240717782548494,
            "debug role": 1228330551044472943
        }
        self.db_data = {
            "host": os.getenv("DB_HOST"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME")
        }
        print("Database configuration:", self.db_data)

    @property
    def database(self):
        return self.db_data
