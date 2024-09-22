from re import match as re_match
from typing import Callable, Dict, List

from utils.libs.ythumanizer import YTHumanizerTools


class URLClassifier:
    def __init__(self, raw_name: str, fancy_name: str, regexes: Dict[str, str], extract_playlist_func: Callable = None) -> None:
        self.raw_name: str = raw_name
        self.fancy_name: str = fancy_name
        self.mixed_urls: Dict[str, List[str]] = {'single': [], 'playlist': []}
        self.single_urls: List[str] = []
        self.regexes: Dict[str, str] = regexes
        self.extract_playlist_func: Callable = extract_playlist_func

    def classify(self, url: str) -> None:
        if re_match(self.regexes['playlist'], url):
            self.mixed_urls['playlist'].append(url)

            if self.extract_playlist_func:
                media_urls = self.extract_playlist_func(url)

                if media_urls:
                    self.single_urls.extend(media_urls)

        elif re_match(self.regexes['single'], url):
            self.mixed_urls['single'].append(url)
            self.single_urls.append(url)


youtube_classifier = URLClassifier(
    'youtube', 'YouTube', {
        'single': r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+(&[^\s]*)?$',
        'playlist': r'(https?://)?(www\.)?youtube\.com/(watch\?v=[\w-]+&list=|playlist\?list=)[\w-]+'
    },
    extract_playlist_func=YTHumanizerTools.extract_playlist_urls
)

youtube_music_classifier = URLClassifier(
    'youtubeMusic', 'YouTube Music', {
        'single': r'(https?://)?(www\.)?music\.youtube\.com/watch\?v=[\w-]+(&[^\s]*)?$',
        'playlist': r'(https?://)?(www\.)?music\.youtube\.com/playlist\?list=[\w-]+'
    },
    extract_playlist_func=YTHumanizerTools.extract_playlist_urls
)


def sort_urls_by_type_and_domain(input_queries_obj: type) -> type:
    """
    Sort URLs by type (single or playlist) and domain.
    :param input_queries_obj: The InputQueries object.
    :return: The updated InputQueries object.
    """

    classifiers = [youtube_classifier, youtube_music_classifier]

    for url in input_queries_obj._urls:
        for classifier in classifiers:
            classifier.classify(url)

    input_queries_obj.SortedURLs.youtube = youtube_classifier
    input_queries_obj.SortedURLs.youtube_music = youtube_music_classifier

    return input_queries_obj
