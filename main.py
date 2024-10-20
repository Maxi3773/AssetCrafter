import json
import os
import shutil
import sys
from typing import cast

from PIL import Image


class Asset:
    def __init__(self, source: str | Image.Image):
        self.image: Image.Image
        if isinstance(source, str):
            self.image = Image.open(f"src/{source}.png")
        else:
            self.image = source

    def store(self, name: str, format_: str) -> None:
        self.image.convert(format_).save(f"out/{name}.png")


class AssetMap(Asset):
    def __init__(self, source: str, rows: int = 1, cols: int = 1):
        super().__init__(source)
        self.rows: int = rows
        self.cols: int = cols

    def select(self, row: int, col: int) -> Asset:
        width = self.image.size[0] / self.cols
        height = self.image.size[1] / self.rows
        x = width * col
        y = height * row
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

    if os.path.exists("out"):
        if not os.path.isdir("out"):
            print('Cannot write output because "out" is not a directory')
            return
        shutil.rmtree("out")
    os.mkdir("out")

    assets: dict[str, Asset] = {}

    for source in build_config["sources"]:
        try:
            if "rows" in source and "cols" in source:
                assets[source["name"]] = AssetMap(source["path"], source["rows"], source["cols"])
                continue
            assets[source["name"]] = Asset(source["path"])
        except FileNotFoundError:
            print(f'Missing source file "{source["path"]}"')

    for output in build_config["output"]:
        if (source := output["source"]) not in assets:
            print(f'Source "{source}" undefined')
            return
        format_: str = "RGBA" if output.get("alpha", False) else "RGB"
        if "row" in output and "col" in output:
            asset = cast(AssetMap, assets[output["source"]]).select(output["row"], output["col"])
        else:
            asset = assets[output["source"]]
        asset.store(output["name"], format_)


if __name__ == "__main__":
    main()
