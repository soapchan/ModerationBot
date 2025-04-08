from openai import OpenAI
import json

class AutoMod:
    def __init__(self, key):
        self.client = OpenAI(api_key=key)
        self.flagged_categories = []
        self.category_scores = {}

    def get_flagged_categories(self, text):
        """
        Analyzes the given text for potentially harmful content using OpenAI's moderation API,
        only if the flagged field is True. Processes only flagged categories and their scores.

        Args:
            text (str): The text to be analyzed for harmful content.

        Returns:
            dict: A dictionary containing:
                - flagged_categories: Only flagged categories with True values.
                - category_scores: Scores only for flagged categories.
                If flagged is False, the function does nothing.
        """
        response = self.client.moderations.create(
            model="omni-moderation-latest",
            input=text
        )
        response_dict = response.model_dump()
        results = response_dict['results'][0]
        
        # Only proceed if 'flagged' is True
        if not results['flagged']:
            return None  # Do nothing if no content is flagged

        # Filter for flagged categories and their scores
        self.flagged_categories = {
            category: flagged
            for category, flagged in results['categories'].items() if flagged
        }
        self.category_scores = {
            category: results['category_scores'][category]
            for category in self.flagged_categories.keys()
        }

        result = {
            "flagged_categories": self.flagged_categories,
            "category_scores": self.category_scores
        }
        print(json.dumps(result, indent=4))
        return result

    @property
    def categories(self):
        return {
            "flagged_categories": self.flagged_categories,
            "category_scores": self.category_scores
        }
