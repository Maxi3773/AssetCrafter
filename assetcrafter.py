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

    @property
    def format(self) -> str:
        return self.image.mode

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    def store(self, name: str, format_: str) -> None:
        self.image.convert(format_).save(f"out/{name}.png")


class AssetMap(Asset):
    def __init__(self, source: str, rows: int = 1, cols: int = 1):
        super().__init__(source)
        self.rows: int = rows
        self.cols: int = cols

    @property
    def tile_size(self) -> tuple[int, int]:
        return self.image.width // self.cols, self.image.height // self.rows

    def select(self, row: int, col: int) -> Asset:
        width, height = self.tile_size
        x = width * col
        y = height * row
        return Asset(self.image.crop((x, y, x + width, y + height)))


def map_(sources: list[Asset], content: list[list[list[int]]]) -> Asset:
    tile_sizes = set()
    for source in sources:
        if isinstance(source, AssetMap):
            tile_sizes.add(source.tile_size)
        else:
            tile_sizes.add(source.size)
    if len(tile_sizes) != 1:
        raise ValueError()
    tile_width, tile_height = tile_sizes.pop()
    size = tile_width * len(content[0]), tile_height * len(content)
    format_ = "RGBA" if "RGBA" in [source.format for source in sources] else "RGB"
    image = Image.new(format_, size)
    for row, cols in enumerate(content):
        for col, tile in enumerate(cols):
            source = sources[tile[0]]
            if isinstance(source, AssetMap):
                image.paste(source.select(tile[1], tile[2]).image, (col * tile_width, row * tile_height))
            else:
                image.paste(source.image, (col * tile_width, row * tile_height))
    return Asset(image)


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

    # 1. Load sources
    for source in build_config["sources"]:
        try:
            if "rows" in source and "cols" in source:
                assets[source["name"]] = AssetMap(source["path"], source["rows"], source["cols"])
                continue
            assets[source["name"]] = Asset(source["path"])
        except FileNotFoundError:
            print(f'Missing source file "{source["path"]}"')

    # 2. Process
    for process in build_config["process"]:
        if "map" in process:
            assets[process["name"]] = map_([assets[source] for source in process["sources"]], process["map"])

    # 3. Output
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
