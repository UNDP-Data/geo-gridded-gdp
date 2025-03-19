import os
import glob
import re
import rasterio
from rasterio.warp import transform_bounds
import subprocess
from tqdm import tqdm



def tiff2cog(
        input_file, output_file, dst_crs = "EPSG:3857",
        lonmin=-20037000, latmin=-20048900, lonmax=20037000, latmax=20048900,
        force=False
):
    """
    convert geotiff to cog

    :param input_file: input geotiff file
    :param output_file: output geotiff file
    """

    parent_dir = os.path.dirname(output_file)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if os.path.exists(output_file):
        if force:
            os.remove(output_file)
        else:
            return

    with rasterio.open(input_file) as src:
        src_crs = src.crs.to_string()

        # compute resolution by bounds
        res_x = (lonmax - lonmin) / src.width
        target_res_x = str(res_x)

    cmd = [
        "gdalwarp",
        input_file,
        output_file,
        "-s_srs", src_crs,
        "-t_srs", dst_crs,
        "-r", "nearest",
        "-te", str(lonmin), str(latmin), str(lonmax), str(latmax),
        "-te_srs", dst_crs,
        "-tr", target_res_x, target_res_x,
        "-tap",
        "-of", "COG",
        "-co", "COMPRESS=ZSTD",
        "-co", "PREDICTOR=2",
        "-co", "BLOCKSIZE=256",
        "-co", "BIGTIFF=YES",
        "-co", "OVERVIEW_RESAMPLING=NEAREST",
        "-co", "NUM_THREADS=ALL_CPUS",
        "-co", "OVERVIEWS=IGNORE_EXISTING",
    ]

    env = os.environ.copy()
    env["GDAL_CACHEMAX"] = "10240"

    # print("Running command:", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def process_files(input_folders, output_folder, force=False):
    # GDPYYYY_ssp2.tif
    pattern_with_ssp = re.compile(r"^GDP(\d{4})_([a-zA-Z0-9]+)\.tif$")
    # GDPYYYY.tif
    pattern_without_ssp = re.compile(r"^GDP(\d{4})\.tif$")

    target_files = []

    for folder in input_folders:
        print(f"Scanning {folder}")
        tif_files = sorted(glob.glob(os.path.join(folder, "*.tif")))
        for tif in tif_files:
            filename = os.path.basename(tif)
            m = pattern_with_ssp.match(filename)
            if m:
                year = m.group(1)
                tag = m.group(2)
                output_file = os.path.join(output_folder,  year,tag, f'gdp.tif')
                target_files.append([tif, output_file])
            else:
                m = pattern_without_ssp.match(filename)
                if m:
                    year = m.group(1)
                    output_file = os.path.join(output_folder, year, 'gdp.tif')
                    target_files.append([tif, output_file])
                else:
                    continue

    print(f"Start processing")
    for files in tqdm(target_files):
        input_file, output_file = files
        tiff2cog(input_file, output_file, force=force)
    print(f"End processing")

if __name__ == '__main__':

    input_folders = [
        "/Volumes/Data/gridded-gdp/original/GDP_2000-2009/",
        "/Volumes/Data/gridded-gdp/original/GDP_2010-2010/",
        "/Volumes/Data/gridded-gdp/original/SSP2/"
    ]
    output_path = "/Volumes/Data/gridded-gdp/stac/"
    process_files(input_folders, output_path, force=True)

    # input_path = "/Volumes/Data/gridded-gdp/original/GDP_2010-2010/GDP2010.tif"
    # output_path = os.path.join("/Volumes/Data/gridded-gdp/stac/GDP_2010-2010/", os.path.basename(input_path))
    # tiff2cog(input_path, output_path, force=True)