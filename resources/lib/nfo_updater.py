#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *

########################

def update_nfo(dbtype,dbid,details=None,file=None):
    if not ADDON.getSettingBool('nfo_updating'):
        return

    if not details:
        db = Database(dbid, dbtype)
        getattr(db, dbtype)()
        details = db.result().get(dbtype)[0]

    if not details:
        log('NFO updater: No item details found or provided --> ID: %s Type: %s' % (dbid, dbtype), ERROR)
        return

    if not file:
        file = details.get('file')
        if not file:
            log('NFO updater: No item path available --> ID: %s Type: %s' % (dbid, dbtype), ERROR)
            return

    if dbtype == 'tvshow':
        path = os.path.join(file,'tvshow.nfo')
    else:
        path = file.replace(os.path.splitext(file)[1], '.nfo')

    UpdateNFO(file=path,
              dbtype=dbtype,
              dbid=dbid,
              details=details)

    # support for additional movie.nfo
    if dbtype == 'movie':
        UpdateNFO(file=file.replace(os.path.basename(file), 'movie.nfo'),
                  dbtype=dbtype,
                  dbid=dbid,
                  details=details)


class UpdateNFO():
    def __init__(self,file,dbtype,dbid,details):
        self.targetfile = file
        self.dbtype = dbtype
        self.dbid = dbid
        self.details = details
        self.run()

    def run(self):
        with busy_dialog():
            try:
                if xbmcvfs.exists(self.targetfile):
                    self.root = self.read_file()

                    if len(self.root):
                        self.handle_details()
                        self.write_file()

            except Exception as error:
                log('Cannot update .nfo file: %s' % error, ERROR)

    def read_file(self):
        file = xbmcvfs.File(self.targetfile)
        content = file.read()
        file.close()

        if content:
            tree = ET.ElementTree(ET.fromstring(content))
            root = tree.getroot()
            return root

    def write_file(self):
        xml_prettyprint(self.root)
        log(self.root)
        content = ET.tostring(self.root, encoding='UTF-8')

        file = xbmcvfs.File(self.targetfile, 'w')
        file.write(content)
        file.close()

    def handle_details(self):
        li = [{'key': 'title', 'value': self.details.get('title')},
              {'key': 'originaltitle', 'value': self.details.get('originaltitle')},
              {'key': 'showtitle', 'value': self.details.get('showtitle')},
              {'key': 'sorttitle', 'value': self.details.get('sorttitle')},
              {'key': 'userrating', 'value': self.details.get('userrating')},
              {'key': 'outline', 'value': self.details.get('plotoutline')},
              {'key': 'plot', 'value': self.details.get('plot')},
              {'key': 'tagline', 'value': self.details.get('tagline')},
              {'key': 'mpaa', 'value': self.details.get('mpaa')},
              {'key': 'premiered', 'value': self.details.get('premiered')},
              {'key': 'year', 'value': self.details.get('premiered', '')[:4]}, #emby
              {'key': 'country', 'value': self.details.get('country')},
              {'key': 'studio', 'value': self.details.get('studio')},
              {'key': 'director', 'value': self.details.get('director')},
              {'key': 'credits', 'value': self.details.get('writer')},
              {'key': 'writer', 'value': self.details.get('writer')}, #emby
              {'key': 'tag', 'value': self.details.get('tag')},
              {'key': 'isuserfavorite', 'value': 'true' if 'Favorite movies' in self.details.get('tag', []) or 'Favorite tvshows' in self.details.get('tag', []) else 'false'}, #emby
              {'key': 'genre', 'value': self.details.get('genre')},
              {'key': 'ratings', 'value': self.details.get('ratings')},
              {'key': 'uniqueid', 'value': self.details.get('uniqueid')},
              {'key': 'status', 'value': self.details.get('status')},
              {'key': 'aired', 'value': self.details.get('firstaired')},
              {'key': 'playcount', 'value': self.details.get('playcount')},
              {'key': 'watched', 'value': 'true' if self.details.get('playcount', 0) > 0 else 'false'}, #emby
              {'key': 'lastplayed', 'value': self.details.get('lastplayed')}
              ]

        for item in li:
            key = item.get('key')
            value = item.get('value')

            if key == 'ratings':
                self.handle_ratings(value)

            elif key == 'uniqueid':
                self.handle_uniqueid(value, self.details.get('episodeguide', ''))

            else:
                self.handle_elem(key, value)

    def handle_elem(self,key,value):
        for elem in self.root.findall(key):
            self.root.remove(elem)

        if isinstance(value, list):
            for i in value:
                if i:
                    elem = ET.SubElement(self.root, key)
                    elem.text = unicode_string(i)
        else:
            if value:
                elem = ET.SubElement(self.root, key)
                elem.text = unicode_string(value)

    def handle_ratings(self,value):
        for elem in self.root.findall('ratings'):
            self.root.remove(elem)

        elem = ET.SubElement(self.root, 'ratings')
        for item in value:
            rating = float(value[item].get('rating', 0.0))
            rating = str(round(rating, 1))
            votes = str(value[item].get('votes', 0))

            subelem = ET.SubElement(elem, 'rating')
            subelem.set('name', item)
            subelem.set('max', '10')

            if value[item].get('default'):
                subelem.set('default', 'true')

                # Emby <votes>, <rating>
                for key in ['rating', 'votes']:
                    for defaultelem in self.root.findall(key):
                        self.root.remove(defaultelem)

                    defaultelem = ET.SubElement(self.root, key)
                    defaultelem.text = eval(key)

            else:
                subelem.set('default', 'false')

            rating_elem = ET.SubElement(subelem, 'value')
            rating_elem.text = rating

            votes_elem = ET.SubElement(subelem, 'votes')
            votes_elem.text = votes

            # Emby <criticrating> Rotten ratings
            if item == 'tomatometerallcritics':
                normalized_rating = int(float(rating) * 10)
                if normalized_rating > 100:
                    normalized_rating = ''

                for emby_elem in self.root.findall('criticrating'):
                    self.root.remove(emby_elem)

                emby_rotten = ET.SubElement(self.root, 'criticrating')
                emby_rotten.text = str(normalized_rating)

    def handle_uniqueid(self,uniqueids,episodeguide):
        # find default uniqueid
        default = ''
        if 'tvdb' in episodeguide:
            default = 'tvdb'
        elif 'tmdb' in episodeguide:
            default = 'tmdb'
        else:
            for elem in self.root.findall('uniqueid'):
                if elem.get('default'):
                    default = elem.get('type')
                    break

        # set fallback default uniqueid
        if not default:
            if self.dbtype == 'movie':
                if uniqueids.get('tmdb'):
                    default = 'tmdb'
                elif uniqueids.get('imdb'):
                    default = 'imdb'

            elif self.dbtype == 'tvshow':
                scraper_default = ADDON.getSetting('tv_scraper_base')

                if (scraper_default == 'TVDb' and uniqueids.get('tvdb')):
                    default = 'tvdb'
                elif scraper_default == 'TMDb' and uniqueids.get('tmdb'):
                    default = 'tmdb'

        # <uniqueid> fields
        for elem in self.root.findall('uniqueid'):
            self.root.remove(elem)

        for item in uniqueids:
            value = uniqueids.get(item, '')

            elem = ET.SubElement(self.root, 'uniqueid')
            elem.set('type', item)
            elem.text = value

            if default == item:
                elem.set('default', 'true')
                if self.dbtype == 'tvshow':
                    self._set_episodeguide(item, value)

        # Emby <imdbid>, <tmdbid>, etc.
        for item in uniqueids:
            elem_name = item + 'id'

            for elem in self.root.findall(elem_name):
                self.root.remove(elem)

            if value:
                elem = ET.SubElement(self.root, elem_name)
                elem.text = uniqueids.get(item, '')

    def _set_episodeguide(self,type,value):
        post = False
        cache = ''

        if type == 'tvdb':
            post = 'yes'
            cache = 'auth.json'
            url = 'https://api.thetvdb.com/login?{"apikey":"439DFEBA9D3059C6","id":%s}|Content-Type=application/json' % str(value)
            json_value = '<episodeguide><url post="%s" cache="%s"><url>%s</url></episodeguide>' % (post, cache, url)

        elif type == 'tmdb':
            language = ADDON.getSetting('tmdb_language')
            cache = 'tmdb-%s-%s.json' % (str(value), language)
            url = 'http://api.themoviedb.org/3/tv/%s?api_key=6a5be4999abf74eba1f9a8311294c267&amp;language=%s' % (str(value), language)
            json_value = '<episodeguide><url cache="%s"><url>%s</url></episodeguide>' % (cache, url)

        else:
            url = ''
            json_value = '<episodeguide><url cache=""><url></url></episodeguide>'

        for elem in self.root.findall('episodeguide'):
            self.root.remove(elem)

        episodeguide_elem = ET.SubElement(self.root, 'episodeguide')
        url_elem = ET.SubElement(episodeguide_elem, 'url')
        if post:
            url_elem.set('post', post)
        url_elem.set('cache', cache)
        url_elem.text = url

        json_call('VideoLibrary.SetTVShowDetails',
                  params={'episodeguide': json_value, 'tvshowid': int(self.dbid)},
                  debug=LOG_JSON
                  )