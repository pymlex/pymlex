import os

from utils.update_readme import update_readme


if __name__ == "__main__":
    token = os.environ["GITHUB_TOKEN"]
    update_readme(token)
