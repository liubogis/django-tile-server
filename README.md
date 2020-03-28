# DJANGO TILE SERVER

Serveur de rendu de tuile utilisant le protocole TMS. L'idée est que chaque tuile est non pas sur le file system, mais directement en base pour faciliter les traitements avec les requete spatial postgis.

## Prérequis

- ```GDAL```
- ```PostgreSQL >= 9.6```
- ```PostGIS >= 2.4```
- ```Python >= 3.6```

## Dépendance python

- ```django```
- ```djangorestframework```
- ```djangorestframework-gis```
- ```django-filter```
- ```rasterio```
- ```corsheaders```

## Téléchargement & installation

Pour télécharcher les sources, taper la commande suivante :

```git clone <url>```

Pour installer le packet :

```python setup.py```
```./manage.py makemigrations```
```./manage.py migrate```

Lancement du serveur :

```./manage.py runserver <ip>:<port>```

## Utilisation

### OpenLayer

```javascript

import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import XYZ from 'ol/source/XYZ';

var view = new View({
    center: [-472202, 7530279],
    zoom: 12
});

var url    = 'https://<ip>:<port>/raster/tms/{z}/{x}/{y}.png?layer=<layer_name>';

var source = new XYZ({ url: url });
var layer  = new TileLayer({ source: source });

var map = new Map({
  target: 'map',
  layers: [ layer ],
  view: view
});

```
