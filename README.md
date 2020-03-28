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



```
