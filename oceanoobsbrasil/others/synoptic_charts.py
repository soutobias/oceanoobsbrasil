import os
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from PIL import Image

from oceanoobsbrasil.access_bucket import AccessBucket
from oceanoobsbrasil.db import GetData


class SynopticChart:
    """get images from marinha.mil.br and save to bucket"""

    load_dotenv()
    os.environ["CLOUDINARY_URL"] = os.getenv("CLOUDINARY_URL")

    def __init__(self, days=5):
        self.url = "https://www.marinha.mil.br/chm/sites/www.marinha.mil.br.chm/files/cartas-sinoticas/"
        self.days = days
        self.db = GetData()

    def get(self):
        """get images from marinha.mil.br and save to bucket"""
        # self.delete()
        for i in range(7):
            for ii in ["00", "12"]:
                name = datetime.strftime(
                    datetime.now() - timedelta(days=i), format="%y%m%d" + ii
                )
                print(name)
                try:
                    response = requests.get(f"{self.url}c{name}.png", verify=False)
                    img = Image.open(BytesIO(response.content))
                    left = 26
                    top = 222
                    right = 1475
                    bottom = 2154
                    img = img.crop((left, top, right, bottom))
                    img = img.convert("RGBA")
                    img_np = np.array(img)
                    df = pd.DataFrame(
                        img_np.reshape(1932 * 1449, 4),
                        columns=["red", "green", "blue", "opacity"],
                    )
                    df.loc[
                        (
                            (df["red"] < 220)
                            & (df["green"] < 220)
                            & (df["blue"] < 220)
                            & (df["red"] > 0)
                            & (df["green"] > 0)
                            & (df["blue"] > 0)
                            & (df["opacity"] == 255)
                        ),
                        "opacity",
                    ] = 0
                    df.loc[
                        (
                            (df["red"] == 255)
                            & (df["green"] == 255)
                            & (df["blue"] == 255)
                            & (df["opacity"] == 255)
                        ),
                        "opacity",
                    ] = 0
                    x = (
                        (df["red"] == 0)
                        & (df["green"] == 0)
                        & (df["blue"] == 0)
                        & (df["opacity"] == 255)
                    )
                    df.loc[x, "red"] = 255
                    df.loc[x, "green"] = 255
                    df.loc[x, "blue"] = 255
                    df.loc[x, "opacity"] = 255
                    x = pd.DataFrame(np.array(df["opacity"]).reshape(1932, 1449))
                    x[
                        (x != 0)
                        & (x.diff() != 0)
                        & (x.diff(periods=-1) != 0)
                        & (x.diff(axis=1) != 0)
                        & (x.diff(axis=1, periods=-1) != 0)
                        & (x.notna())
                    ] = 0
                    df["opacity"] = np.array(x).reshape(1932 * 1449)
                    im = Image.fromarray(np.array(df).reshape(1932, 1449, 4))
                    im.save(f"{name}.png")

                    self.add_image(f"{name}.png")
                except Exception as e:
                    print(e)

    def add_image(self, name):
        """add image to bucket

        Args:
            name (string): image to be uploaded to the bucket
        """
        bucket_access = AccessBucket(bucket=os.environ.get("BUCKET_NAME"))
        bucket_access.upload(
            file_names=[name],
            path="./",
            bucket_folder=os.environ.get("BUCKET_PATH"),
            verbose=1,
        )
