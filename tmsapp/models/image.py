# Library
#-----------------------------------------------------------------------------------------------------------------------

from    django.contrib.gis.db   import models
from    tmsapp.utils            import *
from    tmsapp.constant         import WEB_MERCATOR_SRID
from    django.contrib.gis.geos import MultiPolygon
from    threading               import Thread
import  time



# Image layer
#-----------------------------------------------------------------------------------------------------------------------

class ImageLayer(models.Model):

    class Meta:
        verbose_name_plural = 'Image Layers'

    imagelayer_id        = models.AutoField(primary_key=True)
    imagelayer_name      = models.CharField(max_length=200, verbose_name='Name')
    imagelayer_file      = models.FileField(upload_to='upload-imagelayer', verbose_name='File (.tif / .zip)')
    imagelayer_crs       = models.IntegerField(default=3857, editable=False, verbose_name='CRS')
    imagelayer_minz      = models.IntegerField(default=0, verbose_name='Min zoom')
    imagelayer_maxz      = models.IntegerField(default=18, verbose_name='Max zoom')
    imagelayer_available = models.BooleanField(default=False, editable=False, verbose_name='Available')
    imagelayer_crea      = models.DateTimeField(auto_now_add=True, verbose_name='Creation')

    geom                 = models.MultiPolygonField(srid=3857, editable=False, null=True)

    # override
    def save(self : object, *args : tuple(), **kwargs : dict()) -> None:

        """ Save ImageLayer object """

        # override
        super(ImageLayer, self).save( *args, **kwargs )

        # start job creation
        self.__start_imagetiles_creation__( *args, **kwargs )

    def get_tile(self : object, z : int, x : int, y : int) -> object:
        """ Get ImageTile by Zomm, X, Y"""
        return ImageTile.get(self, z, x, y)


    def __create_imagetile__(self, zoom : int, x : int, y : int, buffer) -> None:

        ImageTile.objects.create(
            imagetile_x=x,
            imagetile_y=y,
            imagetile_zoom=zoom,
            imagetile_layer=self,
            image=buffer.getvalue()
        )

    def __start_imagetiles_creation__(self, *args, **kwargs ) -> None:
        _job = Thread(target=self.__create_imagetiles__, args=args, kwargs=kwargs).start()

    def __create_imagetiles__(self, *args, **kwargs):

        if self.imagelayer_file.path.split('.')[ -1 ] == 'tif':

            # create tiles for one image
            seconds, polygon = self.__create_imagetiles_one__( self.imagelayer_file.path, *args, **kwargs )

            # update layer
            self.geom                 = MultiPolygon([ polygon ])
            self.imagelayer_available = True

            # override again
            super(ImageLayer, self).save(*args, **kwargs)

        elif self.imagelayer_file.path.split('.')[ -1 ] == 'zip':

            # data
            m_polyset = []
            seconds   = 0

            # unzip file
            for path in unzip(self.imagelayer_file.path, '/tmp'):

                # create tiles for one image
                second, polygon = self.__create_imagetiles_one__(path, *args, **kwargs)
                print( polygon )

                # update data
                seconds += second
                m_polyset.append( polygon )

            # update layer
            self.geom = MultiPolygon( m_polyset )
            self.imagelayer_available = True

            print( seconds )

            # override again
            super(ImageLayer, self).save(*args, **kwargs)


        else:
            assert False

    def __create_imagetiles_one__(self, image_path, *args, **kwargs):

        # get time at start
        start_time = time.time()

        # first, reprojected raster to WEB_MERCATOR SRID
        reprojected_raster(image_path, image_path, dst_crs=WEB_MERCATOR_SRID)

        # get raster extent as polygon
        polygon   = get_raster_extent( image_path )

        # get min & max zoom
        minZ = self.imagelayer_minz
        maxZ = self.imagelayer_maxz

        # then, make image tiles
        make_imagetiles(
            image_path ,
            WEB_MERCATOR_WORLD_SIZE   ,
            WEB_MERCATOR_TILE_SIZE    ,
            minZ                      ,
            maxZ                      ,
            self.__create_imagetile__
        )

        # get time at end
        end_time = time.time()
        total_time = end_time - start_time

        # return time & polygon
        return total_time, polygon

    def __str__(self):
        return "%s" % self.imagelayer_name

    def __repr__(self):
        return self.__str__()



# Image tile
#-----------------------------------------------------------------------------------------------------------------------

class ImageTile(models.Model):

    class Meta:
        verbose_name_plural = 'Image Tiles'

    imagetile_id    = models.AutoField(primary_key=True)
    imagetile_x     = models.IntegerField(null=True, verbose_name="X")
    imagetile_y     = models.IntegerField(null=True, verbose_name="Y")
    imagetile_zoom  = models.IntegerField(null=True, verbose_name="Zoom")
    imagetile_size  = models.IntegerField(null=True, verbose_name="Tile size")
    imagetile_layer = models.ForeignKey(ImageLayer, null=True, on_delete=models.CASCADE, verbose_name='Image Layer')

    image          = models.BinaryField(null=True)

    def __str__(self):
        params = (self.imagetile_layer.imagelayer_name, self.imagetile_zoom, self.imagetile_x, self.imagetile_y)
        return '%s [Z=%d X=%d Y=%d]' % params

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def get(imagelayer : object, zoom : int, x : int, y : int) -> object:

        """ Get image tile by imagelayer, X, Y, Zoom """

        # create params
        params   = { 'imagetile_layer' : imagelayer, 'imagetile_x' : x, 'imagetile_y' : y, 'imagetile_zoom' : zoom }

        # get queryset
        queryset = ImageTile.objects.filter( **params )

        # get first elt
        tile     = queryset.first()

        # return value
        return tile
