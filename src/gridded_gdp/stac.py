import pystac

def create_catalog():
    catalog = pystac.Catalog(
        id="gridded-gdp",
        description="a global gridded dataset consistent with the Shared Socioeconomic Pathways"
    )
    print(list(catalog.get_children()))
    print(list(catalog.get_items()))


if __name__ == '__main__':
    create_catalog()