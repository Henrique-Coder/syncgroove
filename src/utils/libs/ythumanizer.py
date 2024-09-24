# Built-in imports
from re import sub as re_sub, search as re_search, IGNORECASE
from unicodedata import normalize
from locale import getlocale
from typing import Any, AnyStr, Dict, List, Literal, Optional, Type, Union

# Third-party imports
from yt_dlp import YoutubeDL, utils as yt_dlp_utils
from scrapetube import get_search as scrape_youtube_search, get_playlist as scrape_youtube_playlist, get_channel as scrape_youtube_channel


def get_value(data: Dict[Any, Any], key: Any, fallback_key: Any = None, convert_to: Type = None, default_to: Any = None) -> Any:
    """
    Get a value from a dictionary, with optional fallback key, conversion and default value.
    :param data: The dictionary to search for the key.
    :param key: The key to search for in the dictionary.
    :param fallback_key: The fallback key to search for in the dictionary if the main key is not found.
    :param convert_to: The type to convert the value to. If the conversion fails, return the default value. If None, return the value as is.
    :param default_to: The default value to return if the key is not found.
    :return: The value from the dictionary, or the default value if the key is not found.
    """

    try:
        value = data[key]
    except KeyError:
        if fallback_key is not None:
            try:
                value = data[fallback_key]
            except KeyError:
                return default_to
        else:
            return default_to

    if convert_to is not None:
        try:
            value = convert_to(value)
        except (ValueError, TypeError):
            return default_to

    return value

def format_string(query: AnyStr, max_length: int = 128) -> Optional[str]:
    """
    Format a string to be used as a filename or directory name. Remove special characters, limit length etc.
    :param query: The string to be formatted.
    :param max_length: The maximum length of the formatted string. If the string is longer, it will be truncated.
    :return: The formatted string. If the input string is empty or None, return None.
    """

    if not query or not query.strip():
        return None

    normalized_string = normalize('NFKD', str(query)).encode('ASCII', 'ignore').decode('utf-8')
    sanitized_string = re_sub(r'\s+', ' ', re_sub(r'[^a-zA-Z0-9\-_()[\]{}!$#+;,. ]', '', normalized_string)).strip()

    if len(sanitized_string) > max_length:
        cutoff = sanitized_string[:max_length].rfind(' ')
        sanitized_string = sanitized_string[:cutoff] if cutoff != -1 else sanitized_string[:max_length]

    return sanitized_string


class YTHumanizer:
    """
    A class for extracting and formatting data from YouTube videos using yt-dlp, facilitating access to general media information.
    """

    def __init__(self, quiet: bool = True, no_warnings: bool = True, ignore_errors: bool = True) -> None:
        """
        Initialize the YTHumanizer class.
        :param quiet: Whether to suppress console output from yt-dlp.
        :param no_warnings: Whether to suppress warnings from yt-dlp.
        :param ignore_errors: Whether to ignore errors from yt-dlp.
        """

        self._ydl_opts: Dict[str, bool] = {'extract_flat': True, 'geo_bypass': True, 'noplaylist': True, 'age_limit': None, 'quiet': quiet, 'no_warnings': no_warnings, 'ignoreerrors': ignore_errors}
        self._raw_youtube_data: Dict[Any, Any] = {}
        self._raw_youtube_streams: List[Dict[Any, Any]] = []
        self._raw_youtube_subtitles: Dict[str, List[Dict[str, str]]] = {}

        self.system_language = getlocale()[0].split('_')[0].lower()

        self.media_info: Dict[str, Any] = {}

        self.best_video_streams: List[Dict[str, Any]] = []
        self.best_video_stream: Dict[str, Any] = {}
        self.best_video_download_url: Optional[str] = None

        self.best_audio_streams: List[Dict[str, Any]] = []
        self.best_audio_stream: Dict[str, Any] = {}
        self.best_audio_download_url: Optional[str] = None

        self.subtitle_streams: Dict[str, List[Dict[str, str]]] = {}

        self.available_video_qualities: List[str] = []
        self.available_audio_languages: List[str] = []

    def run(self, url: str = None) -> None:
        """
        Run the YTHumanizer class to extract and format data from a YouTube video.
        :param url: The URL of the YouTube video to extract data from.
        """

        media_id = YTHumanizerTools.extract_media_id(url)

        if not media_id:
            raise ValueError(f'Invalid YouTube video URL: "{url}"')

        url = f'https://www.youtube.com/watch?v={media_id}'

        try:
            with YoutubeDL(self._ydl_opts) as ydl:
                self._raw_youtube_data = ydl.extract_info(url, download=False, process=True)
        except (yt_dlp_utils.DownloadError, yt_dlp_utils.ExtractorError, Exception) as e:
            raise ValueError(f'Error extracting data from YouTube video: "{url}"') from e

        self._raw_youtube_streams = self._raw_youtube_data.get('formats', [])
        self._raw_youtube_subtitles = self._raw_youtube_data.get('subtitles', {})

    def analyze_media_info(self) -> None:
        """
        Extract and format relevant media information from the raw YouTube data.
        """

        data = self._raw_youtube_data

        id_ = data.get('id')
        title = get_value(data, 'fulltitle', 'title')
        clean_title = format_string(title)
        channel_name = get_value(data, 'channel', 'uploader')
        clean_channel_name = format_string(channel_name)
        chapters = data.get('chapters', [])

        if chapters:
            chapters = [
                {
                    'title': chapter.get('title'),
                    'startTime': get_value(chapter, 'start_time', convert_to=float),
                    'endTime': get_value(chapter, 'end_time', convert_to=float)
                }
                for chapter in chapters
            ]

        media_info = {
            'fullUrl': f'https://www.youtube.com/watch?v={id_}',
            'shortUrl': f'https://youtu.be/{id_}',
            'embedUrl': f'https://www.youtube.com/embed/{id_}',
            'id': id_,
            'title': title,
            'cleanTitle': clean_title,
            'description': data.get('description'),
            'channelId': data.get('channel_id'),
            'channelUrl': get_value(data, 'uploader_url', 'channel_url'),
            'channelName': channel_name,
            'cleanChannelName': clean_channel_name,
            'isVerifiedChannel': get_value(data, 'channel_is_verified', default_to=False),
            'duration': get_value(data, 'duration'),
            'viewCount': get_value(data, 'view_count'),
            'isAgeRestricted': get_value(data, 'age_limit', convert_to=bool),
            'categories': get_value(data, 'categories', default_to=[]),
            'tags': get_value(data, 'tags', default_to=[]),
            'isStreaming': get_value(data, 'is_live'),
            'uploadTimestamp': get_value(data, 'timestamp', 'release_timestamp'),
            'availability': get_value(data, 'availability'),
            'chapters': chapters,
            'commentCount': get_value(data, 'comment_count'),
            'likeCount': get_value(data, 'like_count'),
            'followCount': get_value(data, 'channel_follower_count'),
            'language': get_value(data, 'language'),
            'thumbnails': [
                f'https://img.youtube.com/vi/{id_}/maxresdefault.jpg',
                f'https://img.youtube.com/vi/{id_}/sddefault.jpg',
                f'https://img.youtube.com/vi/{id_}/hqdefault.jpg',
                f'https://img.youtube.com/vi/{id_}/mqdefault.jpg',
                f'https://img.youtube.com/vi/{id_}/default.jpg'
            ]
        }

        self.media_info = dict(sorted(media_info.items()))

    def analyze_video_streams(self, preferred_quality: Literal['all', 'best', '144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p', '4320p'] = 'all') -> None:
        """
        Extract and format the best video streams from the raw YouTube data.
        :param preferred_quality: The preferred quality of the video stream. If "all", all streams will be considered and sorted by quality. If "best", only the best quality streams will be considered. If a specific quality is provided, the stream will be selected according to the chosen quality, however if the quality is not available, the best quality will be selected.
        """

        data = self._raw_youtube_streams

        format_id_extension_map = {
            702: 'mp4', 571: 'mp4', 402: 'mp4', 272: 'webm',  # 7680x4320
            701: 'mp4', 401: 'mp4', 337: 'webm', 315: 'webm', 313: 'webm', 305: 'mp4', 266: 'mp4',  # 3840x2160
            700: 'mp4', 400: 'mp4', 336: 'webm', 308: 'webm', 271: 'webm', 304: 'mp4', 264: 'mp4',  # 2560x1440
            699: 'mp4', 399: 'mp4', 335: 'webm', 303: 'webm', 248: 'webm', 299: 'mp4', 137: 'mp4', 216: 'mp4', 170: 'webm',  # 1920x1080 (616: 'webm' - Premium [m3u8])
            698: 'mp4', 398: 'mp4', 334: 'webm', 302: 'webm', 612: 'webm', 247: 'webm', 298: 'mp4', 136: 'mp4', 169: 'webm',  # 1280x720
            697: 'mp4', 397: 'mp4', 333: 'webm', 244: 'webm', 135: 'mp4', 168: 'webm',  # 854x480
            696: 'mp4', 396: 'mp4', 332: 'webm', 243: 'webm', 134: 'mp4', 167: 'webm',  # 640x360
            695: 'mp4', 395: 'mp4', 331: 'webm', 242: 'webm', 133: 'mp4',  # 426x240
            694: 'mp4', 394: 'mp4', 330: 'webm', 278: 'webm', 598: 'webm', 160: 'mp4', 597: 'mp4',  # 256x144
        }

        video_streams = [
            stream for stream in data
            if stream.get('vcodec') != 'none' and int(get_value(stream, 'format_id').split('-')[0]) in format_id_extension_map
        ]

        def calculate_score(stream: Dict[Any, Any]) -> float:
            width = stream.get('width', 0)
            height = stream.get('height', 0)
            framerate = stream.get('fps', 0)
            bitrate = stream.get('tbr', 0)

            return width * height * framerate * bitrate

        sorted_video_streams = sorted(video_streams, key=calculate_score, reverse=True)

        def extract_stream_info(stream: Dict[Any, Any]) -> Dict[str, Any]:
            codec = stream.get('vcodec', '')
            codec_parts = codec.split('.', 1)
            quality_note = stream.get('format_note')
            youtube_format_id = int(get_value(stream, 'format_id').split('-')[0])

            return {
                'url': stream.get('url'),
                'codec': codec_parts[0] if codec_parts else None,
                'codecVariant': codec_parts[1] if len(codec_parts) > 1 else None,
                'rawCodec': codec,
                'extension': format_id_extension_map.get(youtube_format_id, 'mp3'),
                'width': stream.get('width'),
                'height': stream.get('height'),
                'framerate': stream.get('fps'),
                'bitrate': stream.get('tbr'),
                'quality': stream.get('height'),
                'qualityNote': quality_note,
                'isHDR': 'hdr' in quality_note.lower() if quality_note else False,
                'size': stream.get('filesize'),
                'language': stream.get('language'),
                'youtubeFormatId': youtube_format_id
            }

        self.best_video_streams = [extract_stream_info(stream) for stream in sorted_video_streams] if sorted_video_streams else None
        self.best_video_stream = self.best_video_streams[0] if self.best_video_streams else None
        self.best_video_download_url = self.best_video_stream['url'] if self.best_video_stream else None

        self.available_video_qualities = list(dict.fromkeys([f'{stream['quality']}p' for stream in self.best_video_streams if stream['quality']]))

        if preferred_quality != 'all':
            preferred_quality = preferred_quality.strip().lower()

            if preferred_quality == 'best' or preferred_quality not in self.available_video_qualities:
                best_available_quality = max([stream['quality'] for stream in self.best_video_streams])
                self.best_video_streams = [stream for stream in self.best_video_streams if stream['quality'] == best_available_quality]
            else:
                self.best_video_streams = [stream for stream in self.best_video_streams if stream['quality'] == int(preferred_quality.replace('p', ''))]

            self.best_video_stream = self.best_video_streams[0] if self.best_video_streams else {}
            self.best_video_download_url = self.best_video_stream['url'] if self.best_video_stream else None

    def analyze_audio_streams(self, preferred_language: Union[str, Literal['all', 'original', 'auto']] = 'auto') -> None:
        """
        Extract and format the best audio streams from the raw YouTube data.
        :param preferred_language: The preferred language code of the audio stream. If "all", all audio streams will be considered, regardless of language. If "original", only the original audios will be considered. If "auto", the language will be automatically selected according to the current operating system language (if not found or video is not available in that language, the fallback will be "original").
        """

        data = self._raw_youtube_streams

        format_id_extension_map = {
            338: 'webm',  # Opus - (VBR) ~480 Kbps (?) - Quadraphonic (4)
            380: 'mp4',  # AC3 - 384 Kbps - Surround (5.1) - Rarely
            328: 'mp4',  # EAC3 - 384 Kbps - Surround (5.1) - Rarely
            258: 'mp4',  # AAC (LC) - 384 Kbps - Surround (5.1) - Rarely
            325: 'mp4',  # DTSE (DTS Express) - 384 Kbps - Surround (5.1) - Rarely*
            327: 'mp4',  # AAC (LC) - 256 Kbps - Surround (5.1) - ?*
            141: 'mp4',  # AAC (LC) - 256 Kbps - Stereo (2) - No, YT Music*
            774: 'webm',  # Opus - (VBR) ~256 Kbps - Stereo (2) - Some, YT Music*
            256: 'mp4',  # AAC (HE v1) - 192 Kbps - Surround (5.1) - Rarely
            251: 'webm',  # Opus - (VBR) <=160 Kbps - Stereo (2) - Yes
            140: 'mp4',  # AAC (LC) - 128 Kbps - Stereo (2) - Yes, YT Music
            250: 'webm',  # Opus - (VBR) ~70 Kbps - Stereo (2) - Yes
            249: 'webm',  # Opus - (VBR) ~50 Kbps - Stereo (2) - Yes
            139: 'mp4',  # AAC (HE v1) - 48 Kbps - Stereo (2) - Yes, YT Music
            600: 'webm',  # Opus - (VBR) ~35 Kbps - Stereo (2) - Yes
            599: 'mp4',  # AAC (HE v1) - 30 Kbps - Stereo (2) - Yes
        }

        audio_streams = [
            stream for stream in data
            if stream.get('acodec') != 'none' and int(get_value(stream, 'format_id').split('-')[0]) in format_id_extension_map
        ]

        def calculate_score(stream: Dict[Any, Any]) -> float:
            bitrate = stream.get('abr', 0)
            sample_rate = stream.get('asr', 0)

            return bitrate * 0.4 + sample_rate / 1000

        sorted_audio_streams = sorted(audio_streams, key=calculate_score, reverse=True)

        def extract_stream_info(stream: Dict[Any, Any]) -> Dict[str, Any]:
            codec = stream.get('acodec', '')
            codec_parts = codec.split('.', 1)
            youtube_format_id = int(get_value(stream, 'format_id').split('-')[0])
            youtube_format_note = stream.get('format_note', '')

            return {
                'url': stream.get('url'),
                'codec': codec_parts[0] if codec_parts else None,
                'codecVariant': codec_parts[1] if len(codec_parts) > 1 else None,
                'rawCodec': codec,
                'extension': format_id_extension_map.get(youtube_format_id, 'mp3'),
                'bitrate': stream.get('abr'),
                'qualityNote': youtube_format_note,
                'isOriginalAudio': '(default)' in youtube_format_note or youtube_format_note.islower(),
                'size': stream.get('filesize'),
                'samplerate': stream.get('asr'),
                'channels': stream.get('audio_channels'),
                'language': stream.get('language'),
                'youtubeFormatId': youtube_format_id
            }

        self.best_audio_streams = [extract_stream_info(stream) for stream in sorted_audio_streams] if sorted_audio_streams else None
        self.best_audio_stream = self.best_audio_streams[0] if self.best_audio_streams else None
        self.best_audio_download_url = self.best_audio_stream['url'] if self.best_audio_stream else None

        self.available_audio_languages = list(dict.fromkeys([stream['language'].lower() for stream in self.best_audio_streams if stream['language']]))

        if preferred_language != 'all':
            preferred_language = preferred_language.strip().lower()

            if preferred_language == 'auto':
                try:
                    if self.system_language not in self.available_audio_languages:
                        raise Exception

                    self.best_audio_streams = [stream for stream in self.best_audio_streams if stream['language'] == self.system_language]
                except Exception:
                    preferred_language = 'original'
            if preferred_language == 'original':
                self.best_audio_streams = [stream for stream in self.best_audio_streams if stream['isOriginalAudio']]
            elif preferred_language != 'auto':
                self.best_audio_streams = [stream for stream in self.best_audio_streams if stream['language'] == preferred_language]

            self.best_audio_stream = self.best_audio_streams[0] if self.best_audio_streams else {}
            self.best_audio_download_url = self.best_audio_stream['url'] if self.best_audio_stream else None

    def analyze_subtitle_streams(self) -> None:
        """
        Extract and format the subtitle streams from the raw YouTube data.
        """

        data = self._raw_youtube_subtitles

        subtitle_streams = {}

        for stream in data:
            subtitle_streams[stream] = [
                {
                    'extension': subtitle.get('ext'),
                    'url': subtitle.get('url'),
                    'language': subtitle.get('name')
                }
                for subtitle in data[stream]
            ]

        self.subtitle_streams = dict(sorted(subtitle_streams.items()))


class YTHumanizerTools:
    """
    A class with independent tools to be used with the YTHumanizer class or separately.
    """

    _youtube_media_id_regex = r'(?:https?:)?(?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtu\.be\/|youtube(?:-nocookie)?\.com\S*?[^\w\s-])([\w-]{11})(?=[^\w-]|$)(?![?=&+%\w.-]*(?:[\'"][^<>]*>|<\/a>))[?=&+%\w.-]*'
    _youtube_media_playlist_id_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:playlist\?list=|watch\?v=|embed\/|v\/)|youtu\.be\/)(?:.*?list=)?([\w-]{34})'

    def extract_media_id(url: str) -> Optional[str]:
        """
        Extract the YouTube media ID from a URL.
        :param url: The URL to extract the media ID from.
        :return: The YouTube media ID extracted from the URL. If the URL is invalid or the media ID is not found, return None.
        """

        match = re_search(YTHumanizerTools._youtube_media_id_regex, url, IGNORECASE)
        return match.group(1) if match else None

    def extract_playlist_id(url: str) -> Optional[str]:
        """
        Extract the YouTube playlist ID from a URL.
        :param url: The URL to extract the media playlist ID from.
        :return: The YouTube media playlist ID extracted from the URL. If the URL is invalid or the media playlist ID is not found, return None.
        """

        match = re_search(YTHumanizerTools._youtube_media_playlist_id_regex, url, IGNORECASE)
        return match.group(1) if match else None

    def get_url_from_query(query: str) -> Optional[str]:
        """
        Get a YouTube video URL from a query string.
        :param query: The query string to search for a YouTube video URL.
        :return: The YouTube video URL found in the query. If no URL is found, return None.
        """

        try:
            data = list(scrape_youtube_search(query, sort_by='relevance', results_type='video', limit=1))
        except Exception:
            return None

        if data:
            for video in data:
                return f'https://www.youtube.com/watch?v={video['videoId']}'

    def get_playlist_urls(url: str) -> Optional[List[str]]:
        """
        Get all the video URLs from a YouTube playlist URL.
        :param url: The URL of the YouTube playlist.
        :return: A list of all the video URLs in the playlist. If the playlist is invalid or no videos are found, return None.
        """

        playlist_id = YTHumanizerTools.extract_playlist_id(url)

        if not playlist_id:
            return None

        try:
            data = list(scrape_youtube_playlist(playlist_id, limit=None))
        except Exception:
            return None

        if data:
            return [f'https://www.youtube.com/watch?v={video['videoId']}' for video in data]

    def get_channel_urls(channel_id: str = None, channel_url: str = None, channel_username: str = None) -> Optional[List[str]]:
        """
        Get all the video URLs from a YouTube channel URL.
        :param channel_id: The ID of the YouTube channel.
        :param channel_url: The URL of the YouTube channel.
        :param channel_username: The username of the YouTube channel.
        :return: A list of all the video URLs in the channel. If the channel is invalid or no videos are found, return None.
        """

        if sum([bool(channel_id), bool(channel_url), bool(channel_username)]) != 1:
            raise ValueError('You must provide only one of the following: channel_id, channel_url, channel_username')

        try:
            data = list(scrape_youtube_channel(channel_id=channel_id, channel_url=channel_url, channel_username=channel_username, sort_by='newest', content_type='videos', limit=None))
        except Exception:
            return None

        if data:
            return [f'https://www.youtube.com/watch?v={video['videoId']}' for video in data]
