# Library
#-----------------------------------------------------------------------------------------------------------------------

from    django.contrib.gis.db   import models
from    django.db               import connection
from    tmsapp.utils            import *
from    tmsapp.constant         import WEB_MERCATOR_SRID, WEB_MERCATOR_WORLD_SIZE, WEB_MERCATOR_TILE_SIZE
from    django.contrib.gis.geos import MultiPolygon
from    threading               import Thread
from    zipfile                 import ZipFile

import rasterio as rio
import numpy    as np
from PIL import Image
from io import BytesIO
import os



# Exception
#-----------------------------------------------------------------------------------------------------------------------

class NotValidRasterException(Exception):
    pass



# Shortcuts
#-----------------------------------------------------------------------------------------------------------------------

# Iter function
def __liter__(L : list(), Fun : object) -> None:

    """ Iter on L with Fun """

    for item in L:
        Fun( item )

# Unzip file
def __unzip__(src : str, dst : str) -> list():

    with ZipFile(src, 'r') as zip_obj:

        # Extract all the contents of zip file in different directory
        zip_obj.extractall( dst )

    return [ '%s/%s' % (dst, x) for x in zip_obj.namelist() ]

# Check raster
def __is_tif__(path : str) -> bool:

    """ Test if path is tif extension """

    return path.split('.')[ -1 ] == 'tif'

# Check raster
def __is_zip__(path : str) -> bool:

    """ Test if path is zip extension """

    return path.split('.')[ -1 ] == 'zip'

# Check raster
def __is_great_format__( path : str ) -> bool:

    """ Test if file can be open with rasterio """

    try:

        # try to open raster
        _ = rio.open( path, 'r' )

        # all is right !
        return True

    except rio.RasterioIOError:

        # damn ! can't open it
        return False

# Check raster
def __check_raster__(path : str) -> None:

    """ Check if path is a valid raster """

    if not __is_tif__( path ):
        raise NotValidRasterException

    if not __is_great_format__( path ):
        raise NotValidRasterException

# Check raster
def __check_rasters__(path : str) -> list():

    """ Check if path is valid list of raster """

    # Case zip
    if __is_zip__( path ):

        # unzip file
        paths = __unzip__( path, '/tmp' )

        # check raster on all list
        __liter__( paths, __check_raster__ )

        # ok, return path list
        return paths

    # Case tif (maybe)
    else:

        # assertion
        __check_raster__( path )

        # ok, return list of path
        return [ path ]

# Create raster tile by layer, zoom, X pos, Y pos and buffer
def __create_tile__(layer : object, zoom: int, x: int, y: int, buffer : object) -> object:

    """ Shortcut for raster tile creation """

    # create parameters objects
    kwargs = { 'rastertile_x':x, 'rastertile_y':y, 'rastertile_zoom':zoom, 'rastertile_layer':layer, 'rast':buffer }

    # create raster tile
    obj = RasterTile.objects.create( **kwargs )

    # return raster tile
    return obj

# Saving layer & create tiles for all zoom
def __save__(layer : object, *args : tuple(), **kwargs : dict()) -> None:

    # first, reprojected all rasters to WEB_MERCATOR SRID
    for path in layer.paths:
        reprojected_raster(path, path, dst_crs=WEB_MERCATOR_SRID)

    # get image_path
    for image_path in layer.paths:

        # get min & max zoom
        minZ = layer.rasterlayer_minz
        maxZ = layer.rasterlayer_maxz

        # then, make image tiles
        args0 = [image_path, WEB_MERCATOR_WORLD_SIZE, WEB_MERCATOR_TILE_SIZE, minZ, maxZ, layer.__create_tile__]
        make_rastertiles(*args0)

    # get all raster extent as polygon
    polyset = [ get_raster_extent(path) for path in layer.paths]

    # update fields
    layer.geom = MultiPolygon( polyset )
    layer.rasterlayer_available = True

    # override
    super(RasterLayer, layer).save(*args, **kwargs)

# Create a background job
def __create_background_job__(target, *args, **kwargs):

    """ Create an independant processus for make tiling """

    # Fork 1
    pid = os.fork()

    # Child execution
    if pid == 0:

        os.setsid()

        # Fork 2
        pidd = os.fork()

        if pidd == 0:

            # Make new connection to db
            connection.connect()

            # Start action
            target( *args, **kwargs )

            # kill
            os._exit( 0 )

        else:

            # kill
            os._exit( 0 )



# Raster Layer
#-----------------------------------------------------------------------------------------------------------------------

class RasterLayer(models.Model):

    class Meta:
        verbose_name_plural = 'Raster Layers'

    rasterlayer_id        = models.AutoField(primary_key=True)
    rasterlayer_name      = models.CharField(max_length=200, verbose_name='Name')
    rasterlayer_file      = models.FileField(upload_to='upload-rasterlayer', verbose_name='File (.tif / .zip)')
    rasterlayer_crs       = models.IntegerField(default=3857, editable=False, verbose_name='CRS')
    rasterlayer_minz      = models.IntegerField(default=0, verbose_name='Min zoom')
    rasterlayer_maxz      = models.IntegerField(default=18, verbose_name='Max zoom')
    rasterlayer_count     = models.IntegerField(null=True, editable=False, verbose_name='Number of band')
    rasterlayer_available = models.BooleanField(default=False, editable=False, verbose_name='Available')
    rasterlayer_crea      = models.DateTimeField(auto_now_add=True, verbose_name='Creation')

    geom                  = models.MultiPolygonField(srid=3857, editable=False, null=True)

    # hidden method
    def __create_tile__(self : object, zoom : int, x : int, y : int, buffer : object) -> object:

        """ Create tile function """

        return __create_tile__(self, zoom, x, y, buffer)

    # hidden method
    def __save__(self : object) -> None:

        """ Simple save method, without background job """

        __save__( self )

    # override save method
    def save(self : object, *args : tuple(), **kwargs : dict()) -> None:

        """ Save method """

        # override
        super(RasterLayer, self).save( *args, **kwargs )

        # check raster
        paths = __check_rasters__( self.rasterlayer_file.path )

        # store path
        self.paths = paths

        # start saving job
        __create_background_job__( self.__save__, *args, **kwargs )

    def get_tile(self : object, z : int, x : int, y : int) -> object:

        """ Get RasterTile by Zoom, X, Y"""

        return RasterTile.get(self, z, x, y)

    def __str__(self):
        return self.rasterlayer_name

    def __repr__(self):
        return self.__str__()



# Raster Tile
#-----------------------------------------------------------------------------------------------------------------------

class RasterTile(models.Model):

    class Meta:
        verbose_name_plural = 'Raster Tiles'

    rastertile_id    = models.AutoField(primary_key=True)
    rastertile_x     = models.IntegerField(null=True, verbose_name='X')
    rastertile_y     = models.IntegerField(null=True, verbose_name='Y')
    rastertile_zoom  = models.IntegerField(null=True, verbose_name='Zoom')
    rastertile_size  = models.IntegerField(default=512, verbose_name='Tile size')
    rastertile_layer = models.ForeignKey(RasterLayer, on_delete=models.CASCADE)

    rast             = models.RasterField(srid=3857)


    def to_png(self):

        """ Convert raster to png """

        raster     = self.rast
        gdal_bands = np.array( [raster.bands[x].data() for x in range(len(raster.bands))] )
        nodata     = raster.bands[0].nodata_value
        rgb        = np.rollaxis(gdal_bands, 0, 3)

        a          = (( np.sum( rgb, axis=2 ) != nodata * 3 ) * 255).astype( np.uint8 )
        p_a        = Image.fromarray( a.astype(np.uint8) , 'L' )
        p_rgb      = Image.fromarray( rgb.astype(np.uint8) )
        p_rgb.putalpha( p_a )

        buffer = BytesIO()
        p_rgb.save(fp=buffer, format="PNG")

        return buffer

    def __str__(self):
        params = (self.rastertile_layer.rasterlayer_name, self.rastertile_zoom, self.rastertile_x, self.rastertile_y)
        return '%s [Z=%d X=%d Y=%d]' % params

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def get(rasterlayer, zoom, x, y):
        return RasterTile.objects.filter(rastertile_layer=rasterlayer, rastertile_x=x, rastertile_y=y, rastertile_zoom=zoom).first()