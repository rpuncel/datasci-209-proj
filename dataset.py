import pandas as pd

from zipfile import ZipFile
import requests
from io import BytesIO

zip_file_url = 'https://epoch.ai/data/data_centers/data_centers.zip'
r = requests.get(zip_file_url, stream=True)

z = ZipFile(BytesIO(r.content))
z.extractall(path="data/data_centers")


data_centers = pd.read_csv("data/data_centers/data_centers.csv")

data_center_chillers = pd.read_csv("data/data_centers/data_center_chillers.csv")