from googleapiclient.discovery import build
from datetime import datetime
import re

class YouTubeFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_most_viewed_videos(self, channel_url, start_date, end_date, max_results=20):
        channel_id = self.extract_channel_id(channel_url)
        videos = self.fetch_videos(channel_id, start_date, end_date)
        sorted_videos = sorted(videos, key=lambda x: x['viewCount'], reverse=True)
        return sorted_videos[:max_results]

    def extract_channel_id(self, channel_url):
        # Handle different URL formats
        patterns = [
            r'youtube\.com/channel/([\w-]+)',
            r'youtube\.com/c/([\w-]+)',
            r'youtube\.com/user/([\w-]+)',
            r'youtube\.com/@([\w-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_url)
            if match:
                username = match.group(1)
                
                if 'channel/' in pattern:
                    return username
                elif 'user/' in pattern:
                    response = self.youtube.channels().list(
                        part='id',
                        forUsername=username
                    ).execute()
                else:  # handle @username or custom URL (c/)
                    response = self.youtube.search().list(
                        part='snippet',
                        q=username,
                        type='channel',
                        maxResults=1
                    ).execute()
                
                if response.get('items'):
                    if 'user/' in pattern:
                        return response['items'][0]['id']
                    else:
                        return response['items'][0]['snippet']['channelId']
        
        raise ValueError("Could not extract channel ID from URL")

    def fetch_videos(self, channel_id, start_date, end_date):
        # Get channel's uploads playlist
        channels_response = self.youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        
        if not channels_response['items']:
            raise ValueError("Channel not found")
            
        playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        videos = []
        next_page_token = None
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        
        while True:
            # Get videos from playlist
            playlist_items = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            video_ids = [item['snippet']['resourceId']['videoId'] 
                        for item in playlist_items['items']]
            
            if not video_ids:
                break
                
            # Get video statistics
            videos_response = self.youtube.videos().list(
                part='statistics,snippet',
                id=','.join(video_ids)
            ).execute()
            
            for video in videos_response['items']:
                published_at = datetime.strptime(
                    video['snippet']['publishedAt'], 
                    '%Y-%m-%dT%H:%M:%SZ'
                )
                
                if start_datetime <= published_at <= end_datetime:
                    videos.append({
                        'title': video['snippet']['title'],
                        'viewCount': int(video['statistics'].get('viewCount', 0)),
                        'publishedAt': published_at.strftime('%Y-%m-%d'),
                        'url': f'https://youtube.com/watch?v={video["id"]}',
                        'thumbnail': video['snippet']['thumbnails']['default']['url']  # default size is 120x90
                    })
            
            next_page_token = playlist_items.get('nextPageToken')
            if not next_page_token:
                break
        
        return videos