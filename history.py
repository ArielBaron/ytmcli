import os

class YTMCLIHistory:
    def __init__(self, max_entries=100):
        self.history_file = os.path.expanduser("~/.ytmcli/history")
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.max_entries = max_entries
        self._load()

    def _load(self):
        if not os.path.exists(self.history_file):
            self.entries = []
        else:
            with open(self.history_file, "r") as f:
                self.entries = [line.strip() for line in f.readlines() if line.strip()]

    def add(self, entry: str):
        if entry in self.entries:
            self.entries.remove(entry)  # move to the end
        self.entries.append(entry)
        self.entries = self.entries[-self.max_entries:]
        self._save()

    def delete_last(self):
        """Remove the most recent entry from history."""
        if self.entries:
            removed = self.entries.pop()
            self._save()
            return removed
        return None

    def _save(self):
        with open(self.history_file, "w") as f:
            f.write("\n".join(self.entries) + "\n")

    def all(self):
        return list(self.entries)


# Example usage:
# history = YTMCLIHistory()
# history.add("never gonna give you up")
# print(history.delete_last())  # removes and returns the last entry
# print(history.all())
