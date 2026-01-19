import emoji
import json


class StringsParser:
    def __init__(self, strings_path: str):
        with open(strings_path, "r", encoding="utf-8") as strings:
            self.loaded_strings = json.load(strings)

    def get(self, string: str, **kwargs):
        template = self.loaded_strings.get(string, string)
        if kwargs:
            formatted_string = template.format(**kwargs)
        else:
            formatted_string = template
        return emoji.emojize(formatted_string)


parser = StringsParser("locales/ru.json")
