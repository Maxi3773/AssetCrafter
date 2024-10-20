import json
import os
import sys
from typing import Self

from PIL import Image


class Asset:
    def __init__(self, source: str | Image.Image):
        self.image: Image.Image
        if isinstance(source, str):
            self.image = Image.open(f"src/{source}.png")
        else:
            self.image = source

    def format(self, mode: str) -> Self:
        self.image = self.image.convert(mode)
        return self

    def store(self, name: str) -> Self:
        self.image.save(f"out/{name}.png")
        return self


class AssetMap(Asset):
    def __init__(self, source: str, rows: int = 1, cols: int = 1):
        super().__init__(source)
        self.rows: int = rows
        self.cols: int = cols

    def select(self, row: int, col: int) -> Asset:
        width = self.image.size[0] / self.cols
        height = self.image.size[1] / self.rows
        x = width * (col - 1)
        y = height * (row - 1)
        return Asset(self.image.crop((x, y, x + width, y + height)))


def main() -> None:
    path: str = sys.argv[1] if len(sys.argv) >= 2 else "."
    os.chdir(path)

    try:
        with open("assets.json", "r") as build_config_file:
            build_config = json.load(build_config_file)
    except FileNotFoundError:
        print('Build config "assets.json" not found')
        return
    except IsADirectoryError:
        print('Build config "assets.json" is a directory')
        return

    try:
        os.mkdir("out")
    except FileExistsError:
        if not os.path.isdir("out"):
            print('Cannot write output because "out" is not a directory')

    assets: dict[str, Asset] = {}

    for source in build_config["sources"]:
        try:
            if "rows" in source and "cols" in source:
                assets[source["name"]] = AssetMap(source["path"], source["rows"], source["cols"])
                continue
            assets[source["name"]] = Asset(source["path"])
        except FileNotFoundError:
            print(f'Missing source file "{source["path"]}"')


if __name__ == "__main__":
    main()
