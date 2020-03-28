# Library
#-----------------------------------------------------------------------------------------------------------------------

from django.http             import HttpResponse
from django.views.generic    import View
from .models                 import RasterLayer, ImageLayer, ImageTile
from django.db.models        import Max
from tmsapp.utils            import __tile_world_bbox__
from .constant               import *
from django.db               import connection



# Structure
#-----------------------------------------------------------------------------------------------------------------------

# dictionary who contains tiles
_IMAGE_TILE  = dict()
_RASTER_TILE = dict()

# function who create key for dictionary
def __make_key__(layer : str, zoom : int, x : int, y : int) -> str:
    return 'key::%s:%d:%d:%d' % (layer, zoom, x, y)



# Raster Tile Map Service View
#-----------------------------------------------------------------------------------------------------------------------

class RasterTMSView(View):

    @staticmethod
    def __tile_response__(zoom : int, x : int, y : int, layer : str, frmt : str) -> object:

        # get raster layer
        rasterlayer = RasterLayer.objects.filter(rasterlayer_name=layer).first()

        # make key
        key = __make_key__(layer, zoom, x, y)

        if key in _RASTER_TILE.keys():
            rastertile = _RASTER_TILE[ key ]

        else:
            rastertile = rasterlayer.get_tile(zoom, x, y)
            _RASTER_TILE[ key ] = rastertile


        # test if image tile exist
        if rastertile is None:
            return HttpResponse(content_type="image/%s" % frmt)

        # if exist
        else:
            print(rastertile)

            buffer        = rastertile.to_png()
            response      = HttpResponse(content_type="image/%s" % frmt)
            response.write( buffer.getvalue() )

            return response

    def get(self, request, *_args, **kwargs):

        # Get kwargs
        X       = kwargs.get( 'x'    )
        Y       = kwargs.get( 'y'    )
        Z       = kwargs.get( 'z'    )
        frmt    = kwargs.get( 'frmt' )

        # Get arguments
        layer   = request.GET['layer']

        # Get image tile
        return RasterTMSView.__tile_response__(Z, X, Y, layer, frmt)


# Image Tile Map Service View
#-----------------------------------------------------------------------------------------------------------------------

class ImageTMSView(View):

    @staticmethod
    def __tile_response__(zoom: int, x: int, y: int, layer: str, frmt : str) -> object:

        # get image layer
        imagelayer = ImageLayer.objects.filter(imagelayer_name=layer).first()

        # make key
        key = __make_key__(layer, zoom, x, y)

        if key in _IMAGE_TILE.keys():
            imagetile  = _IMAGE_TILE[ key ]

        else:
            imagetile  = imagelayer.get_tile(zoom, x, y)
            _IMAGE_TILE[ key ] = imagetile

        # test if image tile exist
        if imagetile is None:
            return HttpResponse(content_type="image/%s" % frmt)

        # if exist
        else:
            response = HttpResponse(content_type="image/%s" % frmt)
            response.write( imagetile.image.tobytes() )
            return response

    @staticmethod
    def __max_zoom__(layer : str) -> int:

        # get image layer
        layer = ImageLayer.objects.filter(imagelayer_name=layer).first()

        # get max zoom
        zoom = ImageTile.objects.filter(imagetile_layer=layer).aggregate( zoom=Max('imagetile_zoom') ) [ 'zoom' ]

        return zoom

    def get(self, request, *_args, **kwargs):

        # Get kwargs
        X       = kwargs.get( 'x'    )
        Y       = kwargs.get( 'y'    )
        Z       = kwargs.get( 'z'    )
        frmt    = kwargs.get( 'frmt' )

        # Get arguments
        layer   = request.GET['layer']

        # Get image tile
        return ImageTMSView.__tile_response__(Z, X, Y, layer, frmt)



# Vector Tile Map Service View
#-----------------------------------------------------------------------------------------------------------------------

class VectorTMSView(View):

    def get(self, request, *args, **kwargs):

        # Get kwargs
        X = kwargs.get('x')
        Y = kwargs.get('y')
        Z = kwargs.get('z')
        frmt = kwargs.get('frmt')

        # Get arguments
        layer = request.GET['layer']

        print( X, Y, Z )

        xmin, ymin, xmax, ymax = __tile_world_bbox__(X, Y, Z, WEB_MERCATOR_WORLD_SIZE, WEB_MERCATOR_TILE_SIZE)

        cursor = connection.cursor()
        query  = "SELECT ST_AsMVTGeom( geom ) FROM tmsapp_vectorgeometry"

        cursor.execute( query )
        binary = cursor.fetchall()

        if len( binary ) == 0:
            return HttpResponse(content_type="image/%s" % frmt)

        else:

            response = HttpResponse(content_type="image/%s" % frmt)
            response.write( binary[0][0].tobytes() )

        return response