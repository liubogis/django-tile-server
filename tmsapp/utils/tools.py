# Library
#-----------------------------------------------------------------------------------------------------------------------

from   rasterio.warp import reproject
import rasterio      as     rio
import numpy         as     np
from tmsapp.constant import *
from django.contrib.gis.geos import Polygon
from rasterio import Affine as A
from django.contrib.gis.gdal import GDALRaster
from PIL import Image
from io  import BytesIO



# Utils for create tiles
#-----------------------------------------------------------------------------------------------------------------------

# calculate pixel sizep
def __pixel_size__(world_size : float, tile_size : int, zoom : int) -> float:
    return ( world_size / (2. ** zoom) ) / tile_size

# calculate tile world bounds
def __tile_world_bbox__(x : int, y : int, zoom : int, world_size : float, tile_size : int) -> (float, float, float, float):

    # get total column of world
    world_columns = world_size / 2. ** zoom

    # get tile shift
    tile_shift = world_size / 2.

    # get rcoord
    xmin =   x     * world_columns - tile_shift
    xmax =   (x+1) * world_columns - tile_shift
    ymin = - y     * world_columns + tile_shift
    ymax = - (y+1) * world_columns + tile_shift

    return xmin, ymin, xmax, ymax

# calculate tile index
def __tile_index_bbox__(bbox : (float, float, float, float), zoom : int, world_size : float) -> (int, int, int, int):

    # get total column of world
    world_columns = world_size / 2. ** zoom

    # get tile shift
    tile_shift = world_size / 2.

    xmin = int( (  bbox[0] + tile_shift) / world_columns )
    xmax = int( (  bbox[2] + tile_shift) / world_columns )
    ymin = int( (- bbox[1] + tile_shift) / world_columns )
    ymax = int( (- bbox[3] + tile_shift) / world_columns )

    return xmin, ymin, xmax, ymax

# get all quadrants
def __make_quadrants__(bbox, zoom, world_size, quadrant_size=50):

    xmin, ymin, xmax, ymax = __tile_index_bbox__(bbox, zoom, world_size)
    quadrants              = []

    for tile_x in range(xmin, xmax +1, quadrant_size):
        for tile_y in range(ymin, ymax +1, quadrant_size):
            quadrant = (tile_x, tile_y, min(tile_x + quadrant_size - 1, xmax), min(tile_y + quadrant_size - 1, ymax))
            quadrants.append( quadrant )

    return quadrants



# Raster tiles creation
#-----------------------------------------------------------------------------------------------------------------------

def __make_rastertiles_Z__(src_dataset : rio.DatasetReader, world_size : float, tile_size : int, zoom : int) -> list():

    # get bands
    src_bands = src_dataset.read()

    # structure for store tiles
    tiles = []

    # get bounds
    src_bbox = src_dataset.bounds
    src_bbox = [src_bbox.left, src_bbox.top, src_bbox.right, src_bbox.bottom]

    # get pixel size
    pixel_size = __pixel_size__(world_size, tile_size, zoom)

    # get all quadrant
    quadrants = __make_quadrants__(src_bbox, zoom, world_size, 1)

    for xmin, ymin, xmax, ymax in quadrants:

        # get bbox of quadrant
        Xmin, Ymin, Xmax, Ymax = list( __tile_world_bbox__(xmin, ymin, zoom, world_size, tile_size) )

        # get pixel size
        pixel_size = __pixel_size__(world_size, tile_size, zoom)

        # make dst shape (3, tsize, tsize), 3 is fix because it's an image RGB
        dst_shape     = (3, tile_size, tile_size)

        # make transform with orig (Xmin, Ymin) and scale (psize, -psize)
        dst_transform = A.translation(Xmin, Ymin) * A.scale(pixel_size, -pixel_size)

        dtype    = src_dataset.dtypes[ 0 ]

        if dtype == rio.uint8:
            datatype = 1
        elif dtype == rio.uint16:
            datatype = 2
        elif dtype == rio.int16:
            datatype = 3
        elif dtype == rio.uint32:
            datatype = 4
        elif dtype == rio.int32:
            datatype = 5
        elif dtype == rio.float32:
            datatype = 6
        elif dtype == rio.float64:
            datatype = 7
        else:
            assert False


        # init dst bands
        dst_bands     = np.zeros(dst_shape, dtype=dtype)

        count  = dst_bands.shape[0]
        nodata = 0 if src_dataset.nodata is None else src_dataset.nodata

        # make reprojection for each bands
        for i in range(count):

            try:

                reproject(
                    source        = src_bands[i],
                    destination   = dst_bands[i],
                    src_transform = src_dataset.transform,
                    src_crs       = src_dataset.crs,
                    src_nodata    = nodata,
                    dst_transform = dst_transform,
                    dst_crs       = src_dataset.crs
                )

            except IndexError:
                continue

        gdal_bands  = [ { 'data' : dst_bands[x], 'nodata_value' : nodata } for x in range(count) ]

        gdal_raster = GDALRaster({

            'srid'        : WEB_MERCATOR_SRID,
            'width'       : tile_size,
            'height'      : tile_size,
            'datatype'    : datatype,
            'nr_of_bands' : count,
            'origin'      : [ Xmin, Ymin ],
            'scale'       : [ pixel_size, -pixel_size ],
            'bands'       : gdal_bands

        })

        tiles.append( (zoom, xmin, ymin, gdal_raster) )

    del src_bands

    # return structure
    return tiles


def make_rastertiles(src : str, world_size : float, tilesize : int, minZ : int, maxZ : int, push_in_db_fun) -> list():

    # Open raster dataset
    src_dataset = rio.open(src, 'r')

    # Create tiles dictionary with zoom as key
    tiles = []

    # for each zoom between minZ and maxZ, create tiles
    for zoom in range(minZ, maxZ+1):

        # get tile for zoom
        tiles = __make_rastertiles_Z__(src_dataset, world_size, tilesize, zoom)

        # push all tile for zoom in database
        for _, x, y, buffer in tiles:
            push_in_db_fun(zoom, x, y, buffer)

    # return ret structure
    return tiles



# Image tiles creation
#-----------------------------------------------------------------------------------------------------------------------

# make imagetiles for a specific zoom
def __make_imagetiles_Z__(src_dataset : rio.DatasetReader, world_size : float, tile_size : int, zoom : int) -> list():

    # structure for store tiles
    tiles = []

    # get bounding box
    src_bbox = src_dataset.bounds
    src_bbox = [src_bbox.left, src_bbox.top, src_bbox.right, src_bbox.bottom]

    # get pixel size
    pixel_size = __pixel_size__(world_size, tile_size, zoom)

    # get all quadrant
    quadrants = __make_quadrants__(src_bbox, zoom, world_size, 1)

    for xmin, ymin, xmax, ymax in quadrants:

        # get bbox of quadrant
        Xmin, Ymin, Xmax, Ymax = list( __tile_world_bbox__(xmin, ymin, zoom, world_size, tile_size) )

        # get pixel size
        pixel_size = __pixel_size__(world_size, tile_size, zoom)

        # make dst shape (3, tsize, tsize), 3 is fix because it's an image RGB
        dst_shape     = (3, tile_size, tile_size)

        # make transform with orig (Xmin, Ymin) and scale (psize, -psize)
        dst_transform = A.translation(Xmin, Ymin) * A.scale(pixel_size, -pixel_size)

        # init dst bands
        dst_bands     = np.zeros(dst_shape, dtype=np.uint8)

        # make reprojection for each bands
        for i in range(3):

            reproject(
                source        = src_dataset.read(i+1),
                destination   = dst_bands[i],
                src_transform = src_dataset.transform,
                src_crs       = src_dataset.crs,
                dst_transform = dst_transform,
                dst_crs       = src_dataset.crs
            )

        # switch channel fst to channel last
        dst_bands = np.rollaxis(dst_bands, 0, 3)

        # make alpha band for no data
        dst_sum            = np.sum(dst_bands, axis=2)
        alpha              = np.zeros( (tile_size, tile_size, 3) )
        alpha[dst_sum > 0] = np.array([255, 255, 255])

        # convert alpha as pilimage
        pil_alpha = Image.fromarray( alpha.astype(dtype=np.uint8) ).convert('L')

        # convert dst_bands as pilimage & put alpha
        pil_tile = Image.fromarray( dst_bands )
        pil_tile.putalpha( pil_alpha )

        # write in a buffer as bytes
        buffer = BytesIO()
        pil_tile.save(fp=buffer, format="PNG")

        # push all in ret structure
        tiles.append( (zoom, xmin, ymin, buffer) )

    # return structure
    return tiles

# make image tiles for zoom between minZ and maxZ
def make_imagetiles(src : str, world_size : float, tilesize : int, minZ : int, maxZ : int, push_in_db_fun) -> list():

    # Open raster dataset
    src_dataset = rio.open(src, 'r')

    # Create tiles dictionary with zoom as key
    tiles = []

    # for each zoom between minZ and maxZ, create tiles
    for zoom in range(minZ, maxZ+1):

        # get tile for zoom
        tiles = __make_imagetiles_Z__(src_dataset, world_size, tilesize, zoom)

        # push all tile for zoom in database
        for _, x, y, buffer in tiles:
            push_in_db_fun(zoom, x, y, buffer)

    # return ret structure
    return tiles



# Get images extent
#-----------------------------------------------------------------------------------------------------------------------

def __extent_to_polyset__( extent : list() ) -> list():

    # get xmin, ymin, xmax, ymax
    xmin = extent.left
    ymin = extent.bottom
    xmax = extent.right
    ymax = extent.top

    # make polyset
    polyset = [ (xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin) ]

    return polyset

def get_raster_extent(src : str, crs : int = 3857 ):

    # get dataset
    src_dataset = rio.open( src, 'r' )

    # get bounds
    extent = src_dataset.bounds

    # get polyset
    polyset = __extent_to_polyset__( extent )

    # make polygon
    polygon = Polygon(polyset , srid=crs)

    return polygon
