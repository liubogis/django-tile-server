# Library
#-----------------------------------------------------------------------------------------------------------------------

from    django.contrib.gis.db   import models
from    tmsapp.utils            import *
from    tmsapp.constant         import WEB_MERCATOR_SRID
from    django.contrib.gis.geos import MultiPolygon
from    django.contrib.gis.gdal import SpatialReference, CoordTransform
import  json



# Vector layer
#-----------------------------------------------------------------------------------------------------------------------

class VectorLayer(models.Model):

    class Meta:
        verbose_name_plural = 'Vector Layers'

    vectorlayer_id        = models.AutoField(primary_key=True)
    vectorlayer_name      = models.CharField(max_length=200, verbose_name='Name')
    vectorlayer_file      = models.FileField(upload_to='upload-vectorlayer', null=True, verbose_name='File (.geojson)')
    vectorlayer_crs       = models.IntegerField(default=3857, editable=False, verbose_name='CRS')
    vectorlayer_available = models.BooleanField(default=False, verbose_name='Available')
    vectorlayer_crea = models.DateTimeField(auto_now_add=True, verbose_name='Creation')

    def __load_geojson__(self, crs : int ):

        # Load geojson
        fd      = open(self.vectorlayer_file.path, 'r')
        geojson = json.load( fd )
        src_crs = 4326

        for item in geojson['features']:

            # get data
            _properties = item['properties']
            coords      = item['geometry'  ]['coordinates']

            # create multipolygon
            polygons   = [ Polygon( coord[0] ) for coord in coords ]
            mpolygon   = MultiPolygon( polygons )

            # Tranform geometry
            gcoord  = SpatialReference( src_crs )
            mycoord = SpatialReference( crs )
            trans   = CoordTransform(gcoord, mycoord)
            mpolygon.transform(trans)

            # Create vector geometry
            VectorGeometry.objects.create(vectorgeometry_layer=self, geom=mpolygon)

    def save(self, *args, **kwargs):

        # override
        super(VectorLayer, self).save( *args, **kwargs )

        # load geojson
        self.__load_geojson__( WEB_MERCATOR_SRID )

    def __str__(self):
        return self.vectorlayer_name

    def __repr__(self):
        return self.__str__()



# Vector geometry
#-----------------------------------------------------------------------------------------------------------------------

class VectorGeometry(models.Model):

    class Meta:
        verbose_name_plural = 'Vector Geometries'

    vectorgeometry_id    = models.AutoField(primary_key=True)
    vectorgeometry_layer = models.ForeignKey(VectorLayer, on_delete=models.CASCADE)
    geom                 = models.MultiPolygonField(srid=3857)