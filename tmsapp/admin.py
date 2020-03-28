# Library
#-----------------------------------------------------------------------------------------------------------------------

from django.contrib   import admin
from .models          import *
from django.contrib import messages



# Raster Layer Admin
#-----------------------------------------------------------------------------------------------------------------------

@admin.register(RasterLayer)
class RasterLayerAdmin(admin.ModelAdmin):

    list_display = (
        'rasterlayer_name',
        'rasterlayer_crs',
        'rasterlayer_minz',
        'rasterlayer_maxz',
        'rasterlayer_crea',
        'rasterlayer_available'
    )

    def save_model(self, request, obj, form, change):

        try:

            super(RasterLayerAdmin, self).save_model(request, obj, form, change)

        except NotValidRasterException:

            # delete object
            obj.delete()

            # set message error
            messages.set_level(request, messages.ERROR)
            messages.error(request, '[BAD FILE]: Not valid raster')


# Image Layer Admin
#-----------------------------------------------------------------------------------------------------------------------

@admin.register(ImageLayer)
class ImageLayerAdmin(admin.ModelAdmin):

    list_display = (
        'imagelayer_name',
        'imagelayer_crs',
        'imagelayer_minz',
        'imagelayer_maxz',
        'imagelayer_crea',
        'imagelayer_available'
    )



# Vector Layer Admin
#-----------------------------------------------------------------------------------------------------------------------

@admin.register(VectorLayer)
class VectorLayerAdmin(admin.ModelAdmin):

    list_display = (
        'vectorlayer_name',
        'vectorlayer_crs',
        'vectorlayer_crea',
        'vectorlayer_available'
    )