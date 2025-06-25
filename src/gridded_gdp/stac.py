import pystac
import os
import glob
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import Polygon, mapping, shape
from datetime import datetime
import json


def get_bbox_and_footprint(raster_uri):
    with rasterio.open(raster_uri) as ds:
        bounds = ds.bounds

        if ds.crs != 'EPSG:4326':
            bounds_4326 = transform_bounds(ds.crs, 'EPSG:4326', *bounds)
        else:
            bounds_4326 = bounds

        bbox = [bounds_4326[0], bounds_4326[1], bounds_4326[2], bounds_4326[3]]

        footprint = Polygon(
            [
                [bounds_4326[0], bounds_4326[1]],  # southwest
                [bounds_4326[0], bounds_4326[3]],  # northwest
                [bounds_4326[2], bounds_4326[3]],  # northeast
                [bounds_4326[2], bounds_4326[1]],  # southeast
            ]
        )

        return (bbox, mapping(footprint))

def create_catalog(root_dir: str, root_href: str, dist_dir: str):
    catalog = pystac.Catalog(
        id="gridded-gdp",
        description="a global gridded dataset consistent with the Shared Socioeconomic Pathways"
    )
    print(list(catalog.get_children()))
    print(list(catalog.get_items()))

    catalog.normalize_hrefs(dist_dir)
    print(catalog.get_self_href())

    unioned_footprint = None
    tif_files = sorted(glob.glob(os.path.join(root_dir, "**/*.tif"), recursive=True))
    collection_items = []

    for img_path in tif_files:
        print(f"Processing: {img_path}")

        rel_path = os.path.relpath(img_path, root_dir)
        print("Relative path:", rel_path)

        parts = rel_path.split(os.sep)

        if len(parts) == 3:
            yyyy, ssp_type, filename = parts
        elif len(parts) == 2:
            yyyy, filename = parts
            ssp_type = None
        else:
            continue

        bbox, footprint = get_bbox_and_footprint(img_path)

        if unioned_footprint is None:
            unioned_footprint = shape(footprint)
        else:
            unioned_footprint = unioned_footprint.union(shape(footprint))
        # print(bbox)
        # print(footprint)

        item_id = f"{yyyy}-{ssp_type}" if ssp_type else f"{yyyy}"
        item_datetime = datetime(int(yyyy), 1, 1)

        if ssp_type is not None:
            item_href = os.path.join(dist_dir, catalog.id, yyyy, ssp_type, "item.json")
            asset_href = os.path.join(root_href,  yyyy, ssp_type, "gdp.tif")
        else:
            item_href = os.path.join(dist_dir, catalog.id, yyyy, "item.json")
            asset_href = os.path.join(root_href, yyyy, "gdp.tif")

        collection_item = pystac.Item(
            id=item_id,
            geometry=footprint,
            bbox=bbox,
            datetime=item_datetime,
            href=item_href,
            properties={
                "year": int(yyyy),
                "ssp_type": ssp_type if ssp_type else None
            }
        )
        # catalog.add_item(item)

        collection_item.add_asset(
            key="gdp",
            asset=pystac.Asset(
                href=asset_href,
                media_type=pystac.MediaType.COG,
                title="GDP Grid Data",
                description="Global gridded GDP data in Cloud Optimized GeoTIFF format representing Gross Domestic Product values consistent with Shared Socioeconomic Pathways",
                roles= ["data"],
                extra_fields={
                    "raster:bands": [
                        {
                            "name": "gdp",
                            "description": "Global gridded GDP data in PPP 2005 U.S. dollars",
                            "data_type": "float32",
                            "unit": "PPP 2005 U.S. dollars",
                        }
                    ]
                }
            )
        )

        # collection_item.set_self_href(item_href)

        print(collection_item.get_self_href())
        # print(json.dumps(item.to_dict(), indent=4))
        collection_items.append(collection_item)

    collection_bbox = list(unioned_footprint.bounds)
    spatial_extent = pystac.SpatialExtent(bboxes=[collection_bbox])

    collection_interval = sorted([item.datetime for item in collection_items])
    temporal_extent = pystac.TemporalExtent(intervals=[[collection_interval[0], collection_interval[-1]]])

    collection_extent = pystac.Extent(spatial=spatial_extent, temporal=temporal_extent)

    collection = pystac.Collection(
        id="gridded-gdp",
        title="Global gridded GDP under the historical and future scenarios",
        description="a global gridded dataset consistent with the Shared Socioeconomic Pathways",
        extent=collection_extent,
        license="CC-BY-4.0",
        providers=[
            pystac.Provider(name="Wang et al. 2023",
                            description="Wang, T., & Sun, F. (2023). Global gridded GDP under the historical and future scenarios [Data set]. Zenodo.",
                            roles=[pystac.ProviderRole.LICENSOR, pystac.ProviderRole.PRODUCER],
                            url="https://zenodo.org/records/7898409"),
            pystac.Provider(name="United Nations Development Programme (UNDP)",
                            roles=[pystac.ProviderRole.HOST],
                            url="https://undp.org")
        ],
        assets=collection_items[0].assets
    )

    collection.set_self_href(os.path.join(dist_dir, catalog.id, "collection.json"))

    for item in collection_items:
        collection.add_item(item)

    catalog.add_child(collection, set_parent=False)

    # print(json.dumps(catalog.to_dict(), indent=4))
    # print(json.dumps(collection.to_dict(), indent=4))

    print(f"Catalog created with {len(collection_items)} items")
    print(f"Spatial extent: {collection_bbox}")
    print(f"Temporal extent: {collection_interval[0]} to {collection_interval[-1]}")

    catalog.normalize_hrefs(root_href)

    print(f"Catalog self href: {catalog.get_self_href()}")
    print(f"Collection self href: {collection.get_self_href()}")

    if collection_items:
        first_item = collection_items[0]
        print(f"First item self href: {first_item.get_self_href()}")

    try:
        # カタログを保存
        catalog.save(catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED)
        print(f"Catalog saved successfully!")
        print(f"Root href: {root_href}")
        print(f"Dist dir: {dist_dir}")

    except Exception as e:
        print(f"Error saving catalog: {str(e)}")
        import traceback
        traceback.print_exc()


def update_stac_root_links(stac_dir):
    new_root_href = "https://undpgeohub.blob.core.windows.net/stacdata/catalog.json"

    print(f"Updating root links to: {new_root_href}")

    updated_count = 0

    json_files = glob.glob(os.path.join(stac_dir, "**/*.json"), recursive=True)

    for json_file in json_files:
        if os.path.basename(json_file) == 'catalog.json':
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'links' in data:
                for link in data['links']:
                    if link.get('rel') == 'root':
                        link['href'] = new_root_href

                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        print(f"Updated: {os.path.relpath(json_file, stac_dir)}")
                        updated_count += 1
                        break

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    print(f"Updated {updated_count} files")
    return updated_count


if __name__ == '__main__':
    root_dir =  "/Volumes/Data/gridded-gdp/stac"
    dist_dir = "/Volumes/Data/gridded-gdp/stac/stac"
    root_href = "https://undpgeohub.blob.core.windows.net/stacdata/gdp"

    create_catalog(root_dir=root_dir, dist_dir=dist_dir, root_href=root_href)
    update_stac_root_links(dist_dir)