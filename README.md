# geo-gridded-gdp
This repository is to manipulate gridded GDP data for GeoHub

## Download data

Download original data under from the below website.

https://zenodo.org/records/7898409

- GDP_2000-2009.7z
- GDP_2010-2010.7z
- SSP2.7z

## Usage

- Install dependencies

```shell
pip install -e .
```

- convert Tiff to COG

Edit `tiff2cog.py` to point data folder you downloaded. Then execute

```shell
python src/gridded_gdp/tiff2cog.py
```

COG will be created under output folder.

## Upload ouputted folder to Azure

Authenticate to Azure by using `az login`

```shell
az login
```

using `az blob copy sync` to upload files to Azure, Make sure pointing output folder location at `--source`.

```shell
az storage blob sync \
              --auth-mode login \
              --account-name "undpgeohub" \
              --container 'stacdata' \
              --destination 'gdp/' \
              --source "/Volumes/Data/gridded-gdp/stac" \
              --include-pattern "*.tif" \
              --delete-destination true
```