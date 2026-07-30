# save.py

import json
import os


SAVE_FILE = "save.json"


class SaveManager:

    def __init__(self):

        self.data = {
            "money": 0,
            "selected_car": 0,
            "owned_cars": [0],
            "best_distance": 0,
            "total_distance": 0,
            "games_played": 0
        }

    def load(self):

        if not os.path.exists(SAVE_FILE):
            self.save()
            return

        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def save(self):

        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                self.data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def get(self, key):

        return self.data.get(key)

    def set(self, key, value):

        self.data[key] = value

    def add_money(self, amount):

        self.data["money"] += amount

    def unlock_car(self, index):

        if index not in self.data["owned_cars"]:
            self.data["owned_cars"].append(index)

    def owns_car(self, index):

        return index in self.data["owned_cars"]

    def select_car(self, index):

        if self.owns_car(index):
            self.data["selected_car"] = index
