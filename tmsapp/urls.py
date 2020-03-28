from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('raster/tms/<int:z>/<int:x>/<int:y>.<str:frmt>', RasterTMSView.as_view(), name='image-tms'),
    path('image/tms/<int:z>/<int:x>/<int:y>.<str:frmt>', ImageTMSView.as_view(), name='image-tms'),
    path('vector/tms/<int:z>/<int:x>/<int:y>.<str:frmt>', VectorTMSView.as_view(), name='vector-tms'),
]
