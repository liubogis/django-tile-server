# Library
#-----------------------------------------------------------------------------------------------------------------------

# Gdal library
from django.contrib.gis.gdal import GDALRaster

# Rasterio library
from   rasterio.warp import calculate_default_transform, reproject
import rasterio      as     rio



# Reproject raster with gdal
#-----------------------------------------------------------------------------------------------------------------------

def reprojected_by_gdal( src : str, dst : str, dst_crs : int = 4326 ) -> None:

    """ Reproject raster with gdal """

    # open raster
    src_gdal = GDALRaster( src , write=True )

    # make the reprojection
    src_gdal.transform( dst_crs, name=dst )



# Reproject raster with rasterio
#-----------------------------------------------------------------------------------------------------------------------

def reprojected_by_rio( src : str, dst : str, dst_crs : int = 4326 ) -> None:

    """ Reproject raster with rasterio """

    # Get src dataset
    src_dataset = rio.open(src, 'r')

    # get crs
    src_crs    = src_dataset.crs
    dst_crs    = 'EPSG:%d' % dst_crs

    # get src width x height
    src_width  = src_dataset.width
    src_height = src_dataset.height

    # get src bounds
    src_bounds = src_dataset.bounds

    # get transform
    src_transform                        = src_dataset.transform
    dst_transform, dst_width, dst_height = calculate_default_transform(src_crs, dst_crs, src_width, src_height, *src_bounds)

    # get profile
    src_profile = src_dataset.profile
    dst_profile = src_profile.copy()
    dst_profile.update(crs=dst_crs, width=dst_width, height=dst_height, transform=dst_transform)

    # make reprojection
    with rio.open(dst, 'w', **dst_profile) as dst_dataset:

        for i in range(1, src_dataset.count+1):

            reproject(
                source=rio.band(src_dataset, i),
                destination=rio.band(dst_dataset, i),
                src_transform=src_transform,
                dst_transform=dst_transform,
                src_crs=src_crs,
                dst_crs=dst_crs
            )