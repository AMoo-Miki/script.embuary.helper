#!/usr/bin/python

########################

import xbmc
import xbmcgui
import json
import datetime

from resources.lib.helper import *
from resources.lib.json_map import *
from resources.lib.library import get_joined_items

########################

class KodiMonitor(xbmc.Monitor):

    def __init__(self):
        self.fullscreen_lock = False


    def onNotification(self, sender, method, data):
        if method in ['Player.OnPlay', 'Player.OnStop', 'Player.OnAVChange', 'Playlist.OnAdd', 'VideoLibrary.OnUpdate', 'AudioLibrary.OnUpdate']:
            log('Kodi_Monitor: sender %s - method: %s  - data: %s' % (sender, method, data))
            self.data = json.loads(data)

        if method == 'Player.OnPlay':
            xbmc.stopSFX()
            pvr_playback = visible('String.StartsWith(Player.Filenameandpath,pvr://)')

            if not self.fullscreen_lock:
                self.do_fullscreen()

            if pvr_playback:
                self.get_channellogo()

            if PLAYER.isPlayingVideo() and not pvr_playback:
                self.get_videoinfo()
                self.get_nextitem(clear=True)
                self.get_nextitem()

            if PLAYER.isPlayingAudio() and not pvr_playback and visible('!String.IsEmpty(MusicPlayer.DBID) + [String.IsEmpty(Player.Art(thumb)) | String.IsEmpty(Player.Art(album.discart))]'):
                self.get_songartworks()

        if method == 'VideoLibrary.OnUpdate' or method == 'AudioLibrary.OnUpdate':
            reload_widgets()

        if method == 'Player.OnAVChange':
            self.get_audiotracks()

        if method == 'Player.OnStop':
            xbmc.sleep(3000)
            if not PLAYER.isPlaying() and xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                self.fullscreen_lock = False
                self.get_nextitem(clear=True)
                self.get_channellogo(clear=True)
                self.get_audiotracks(clear=True)
                self.get_videoinfo(clear=True)

        if method == 'Playlist.OnAdd':
            self.clear_playlists()


    def clear_playlists(self):
        if self.data['position'] == 0 and visible('Skin.HasSetting(ClearPlaylist)'):
                if self.data['playlistid'] == 0:
                    VIDEOPLAYLIST.clear()
                    log('Music playlist has been filled. Clear existing video playlist')

                elif self.data['playlistid'] == 1:
                    MUSICPLAYLIST.clear()
                    log('Video playlist has been filled. Clear existing music playlist')


    def do_fullscreen(self):
        xbmc.sleep(1000)
        if visible('Skin.HasSetting(StartPlayerFullscreen)'):

            for i in range(1,200):
                if xbmcgui.getCurrentWindowId() in [12005, 12006]:
                    self.fullscreen_lock = True
                    break

                elif xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                    execute('Dialog.Close(all,true)')
                    execute('action(fullscreen)')
                    self.fullscreen_lock = True
                    log('Playback started. Force switch to fullscreen.')
                    break

                else:
                    xbmc.sleep(50)


    def get_audiotracks(self,clear=False):
        xbmc.sleep(100)
        audiotracks = PLAYER.getAvailableAudioStreams()
        if len(audiotracks) > 1 and not clear:
            winprop('EmbuaryPlayerAudioTracks.bool', True)
        else:
            winprop('EmbuaryPlayerAudioTracks', clear=True)


    def get_channellogo(self,clear=False):
        try:
            if clear:
                raise Exception

            channel_details = get_channeldetails(xbmc.getInfoLabel('VideoPlayer.ChannelName'))
            winprop('Player.ChannelLogo', channel_details['icon'])

        except Exception:
            winprop('Player.ChannelLogo', clear=True)


    def get_videoinfo(self,clear=False):
        dbid = xbmc.getInfoLabel('VideoPlayer.DBID')

        for i in range(1,50):
            winprop('VideoPlayer.AudioCodec.%i' % i, clear=True)
            winprop('VideoPlayer.AudioChannels.%i' % i, clear=True)
            winprop('VideoPlayer.AudioLanguage.%i' % i, clear=True)
            winprop('VideoPlayer.SubtitleLanguage.%i' % i, clear=True)

        if clear or not dbid:
            return

        if visible('VideoPlayer.Content(movies)'):
            method = 'VideoLibrary.GetMovieDetails'
            mediatype = 'movieid'
            details = 'moviedetails'
        elif visible('VideoPlayer.Content(episodes)'):
            method = 'VideoLibrary.GetEpisodeDetails'
            mediatype = 'episodeid'
            details = 'episodedetails'
        else:
            return

        json_query = json_call(method,
                            properties=['streamdetails'],
                            params={mediatype: int(dbid)}
                            )

        try:
            results_audio = json_query['result'][details]['streamdetails']['audio']

            i = 1
            for track in results_audio:
                winprop('VideoPlayer.AudioCodec.%i' % i, track['codec'])
                winprop('VideoPlayer.AudioChannels.%i' % i, str(track['channels']))
                winprop('VideoPlayer.AudioLanguage.%i' % i, track['language'])
                i += 1

        except Exception:
            pass

        try:
            results_subtitle = json_query['result'][details]['streamdetails']['subtitle']

            i = 1
            for subtitle in results_subtitle:
                winprop('VideoPlayer.SubtitleLanguage.%i' % i, subtitle['language'])
                i += 1

        except Exception:
            return


    def get_nextitem(params,clear=False):
        try:
            if clear:
                raise Exception

            position = int(VIDEOPLAYLIST.getposition())

            json_query = json_call('Playlist.GetItems',
                                    properties=playlist_properties,
                                    limits={"start": position+1, "end": position+2},
                                    params={'playlistid': 1}
                                    )

            nextitem = json_query['result']['items'][0]

            arts = nextitem['art']
            for art in arts:
                if art in ['clearlogo','tvshow.clearlogo','landscape','tvshow.landscape','poster','tvshow.poster','clearart','tvshow.clearart','banner','tvshow.banner']:
                    winprop('VideoPlayer.Next.Art(%s)' % art, arts[art])

            try:
                runtime = int(nextitem.get('runtime'))
                minutes = runtime / 60
                winprop('VideoPlayer.Next.Duration(m)', str(round(minutes)))
                winprop('VideoPlayer.Next.Duration', str(datetime.timedelta(seconds=runtime)))
                winprop('VideoPlayer.Next.Duration(s)', str(runtime))

            except Exception:
                winprop('VideoPlayer.Next.Duration', clear=True)
                winprop('VideoPlayer.Next.Duration(m)', clear=True)
                winprop('VideoPlayer.Next.Duration(s)', clear=True)

            winprop('VideoPlayer.Next.Title', nextitem.get('title',''))
            winprop('VideoPlayer.Next.TVShowTitle', nextitem.get('showtitle',''))
            winprop('VideoPlayer.Next.Genre', get_joined_items(nextitem.get('genre','')))
            winprop('VideoPlayer.Next.Plot', nextitem.get('plot',''))
            winprop('VideoPlayer.Next.Tagline', nextitem.get('tagline',''))
            winprop('VideoPlayer.Next.Season', str(nextitem.get('season','')))
            winprop('VideoPlayer.Next.Episode', str(nextitem.get('episode','')))
            winprop('VideoPlayer.Next.Year', str(nextitem.get('year','')))
            winprop('VideoPlayer.Next.Rating', str(float(nextitem.get('rating','0'))))
            winprop('VideoPlayer.Next.UserRating', str(float(nextitem.get('userrating','0'))))
            winprop('VideoPlayer.Next.DBID', str(nextitem.get('id','')))
            winprop('VideoPlayer.Next.DBType', nextitem.get('type',''))
            winprop('VideoPlayer.Next.Art(fanart)', nextitem.get('fanart',''))
            winprop('VideoPlayer.Next.Art(thumbnail)', nextitem.get('thumbnail',''))

        except Exception:
            for art in ['fanart','thumbnail','clearlogo','tvshow.clearlogo','landscape','tvshow.landscape','poster','tvshow.poster','clearart','tvshow.clearart','banner','tvshow.banner']:
                winprop('VideoPlayer.Next.Art(%s)' % art, clear=True)

            for info in ['Duration','Duration(m)','Duration(s)','Title','TVShowTitle','Genre','Plot','Tagline','Season','Episode','Year','Rating','UserRating','DBID','DBType']:
                winprop('VideoPlayer.Next.%s' % info, clear=True)


    def get_songartworks(self):
        try:
            songdetails = json_call('AudioLibrary.GetSongDetails',
                                properties=['art', 'albumid'],
                                params={'songid': int(xbmc.getInfoLabel('MusicPlayer.DBID'))},
                                )

            songdetails = songdetails['result']['songdetails']
            fanart = songdetails['art'].get('fanart', '')
            thumb = songdetails['art'].get('thumb', '')
            clearlogo = songdetails['art'].get('clearlogo', '')

        except Exception:
            return

        try:
            albumdetails = json_call('AudioLibrary.GetAlbumDetails',
                                properties=['art'],
                                params={'albumid': int(songdetails['albumid'])},
                                )

            albumdetails = albumdetails['result']['albumdetails']
            discart = albumdetails['art'].get('discart', '')

        except Exception:
            pass

        item = xbmcgui.ListItem()
        item.setPath(xbmc.Player().getPlayingFile())
        item.setArt({'thumb': thumb, 'fanart': fanart, 'clearlogo': clearlogo, 'discart': discart, 'album.discart': discart})
        xbmc.Player().updateInfoTag(item)