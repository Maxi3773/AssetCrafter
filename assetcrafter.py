import json
import os
import shutil
import sys
from typing import Any, cast

from PIL import Image


class Asset:
    def __init__(self, source: Image.Image | str):
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

    def save(self, name: str, format_: str) -> None:
        self.image.convert(format_).save(f"out/{name}.png")


class AssetMap(Asset):
    def __init__(self, source: Image.Image | str, rows: int, cols: int):
        super().__init__(source)
        self.rows: int = rows
        self.cols: int = cols

    @property
    def tile_size(self) -> tuple[int, int]:
        return self.image.width // self.cols, self.image.height // self.rows

    def select(self, row: int, col: int) -> Asset:
        width, height = self.tile_size
        x, y = width * col, height * row
        return Asset(self.image.crop((x, y, x + width, y + height)))


def get_tile_size(asset: Asset) -> tuple[int, int]:
    if isinstance(asset, AssetMap):
        return asset.tile_size
    else:
        return asset.size


def create_icon(source: Asset, width: int, height: int, scaling: dict[str, Any] | None = None) -> Asset:
    if scaling is None or scaling["smooth"]:
        resampling_filter = None
    else:
        resampling_filter = Image.Resampling.NEAREST
    content = source.image.crop(source.image.getbbox())
    original_width, original_height = content.size
    aspect_ratio = min(width / original_width, height / original_height)
    new_width, new_height = int(original_width * aspect_ratio), int(original_height * aspect_ratio)
    resized_image = content.resize((new_width, new_height), resampling_filter)
    icon = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    icon.paste(resized_image, ((width - new_width) // 2, (height - new_height) // 2))
    return Asset(icon)


def create_map(sources: list[Asset], content: list[list[list[int]]]) -> AssetMap:
    format_: str = "RGBA" if "RGBA" in (source.format for source in sources) else "RGB"
    tile_width, tile_height = max({get_tile_size(source) for source in sources})
    width, height = tile_width * len(content[0]), tile_height * len(content)
    image = Image.new(format_, (width, height))
    for row, cols in enumerate(content):
        for col, tile in enumerate(cols):
            source = sources[tile[0]]
            if isinstance(source, AssetMap):
                source = source.select(tile[1], tile[2])
            image.paste(source.image, (col * tile_width, row * tile_height))
    return AssetMap(image, height // tile_height, width // tile_width)


def main() -> None:
    path: str = sys.argv[1] if len(sys.argv) >= 2 else "."
    os.chdir(path)

    try:
        with open("assets.json", "r") as asset_config_file:
            asset_config = json.load(asset_config_file)
    except FileNotFoundError:
        print('Asset config "assets.json" not found')
        return
    except IsADirectoryError:
        print('Asset config "assets.json" is a directory')
        return

    if os.path.exists("out"):
        if not os.path.isdir("out"):
            print('Cannot write output because "out" is not a directory')
            return
        shutil.rmtree("out")
    os.mkdir("out")

    assets: dict[str, Asset] = {}

    # Sources
    for source in asset_config["sources"]:
        try:
            if "rows" in source and "cols" in source:
                assets[source["name"]] = AssetMap(source["path"], source["rows"], source["cols"])
            else:
                assets[source["name"]] = Asset(source["path"])
        except FileNotFoundError:
            print(f'Missing source file "{source["path"]}"')

    # Artifacts
    for artifact in asset_config["artifacts"]:
        sources: list[Asset] = [assets[source] for source in artifact["sources"]]
        match artifact["type"]:
            case "icon":
                if len(sources) > 1:
                    print("Icon only uses the first source")
                if "row" in artifact and "col" in artifact:
                    source = cast(AssetMap, sources[0]).select(artifact["row"], artifact["col"])
                else:
                    source = sources[0]
                assets[artifact["name"]] = create_icon(source, **artifact["attributes"])
            case "map":
                assets[artifact["name"]] = create_map(sources, **artifact["attributes"])
            case _ as type_:
                print(f'Unknown artifact type "{type_}"')
                return

    # Output
    for output in asset_config["output"]:
        if (source := output["source"]) not in assets:
            print(f'Source "{source}" undefined')
            return
        format_: str = "RGBA" if output.get("alpha", False) else "RGB"
        if "row" in output and "col" in output:
            asset = cast(AssetMap, assets[output["source"]]).select(output["row"], output["col"])
        else:
            asset = assets[output["source"]]
        asset.save(output["name"], format_)


if __name__ == "__main__":
    main()
