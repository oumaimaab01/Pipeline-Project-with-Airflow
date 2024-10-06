
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import requests
import csv

API_KEY='AIzaSyCwjIRc3jvlfwdIElXVVil0-HzbOZnpfAA'
CHANNEL_ID = 'UCtYLUTtgS3k1Fg4y5tAhLbw'

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
}

dag = DAG(
    'generate_csv',
    default_args=default_args,
    description='Extract YouTube data',
    schedule_interval='@daily',
)

def fetch_channel_info(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails,statistics&id={channel_id}&key={API_KEY}"
    response = requests.get(url).json()
    channel_info = response['items'][0]
    filename = f'/opt/airflow/dags/channel_info.csv'
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=channel_info.keys())
        writer.writeheader()
        writer.writerow(channel_info)
    return channel_info['contentDetails']['relatedPlaylists']['uploads']

def fetch_playlists(channel_id):
    playlists = []
    next_page_token = None
    while True:
        url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId={channel_id}&maxResults=50&key={API_KEY}"
        if next_page_token:
            url += f"&pageToken={next_page_token}"
        response = requests.get(url).json()
        playlists.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    return playlists

def fetch_all_videos_in_playlist(playlist_id):
    videos = []
    next_page_token = None
    while True:
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={API_KEY}"
        if next_page_token:
            url += f"&pageToken={next_page_token}"
        response = requests.get(url).json()
        videos.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    return videos

def fetch_video_info(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={video_id}&key={API_KEY}"
    response = requests.get(url).json()
    return response['items'][0]

def fetch_comments(video_id, max_results=10):
    url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&maxResults={max_results}&key={API_KEY}"
    response = requests.get(url).json()
    comments = response['items']
    comments_data = [{'comment': item['snippet']['topLevelComment']['snippet']['textDisplay']} for item in comments]
    return comments_data

def process_playlist(playlist_id):
    videos = fetch_all_videos_in_playlist(playlist_id)
    latest_video = None
    latest_date = None
    for video in videos:
        video_id = video['snippet']['resourceId']['videoId']
        video_info = fetch_video_info(video_id)
        publish_date = video_info['snippet']['publishedAt']
        if latest_date is None or publish_date > latest_date:
            latest_date = publish_date
            latest_video = video_id
    if latest_video:
        comments = fetch_comments(latest_video)
        filename = f'/opt/airflow/dags/comments_playlist_{playlist_id}.csv'
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['comment'])
            writer.writeheader()
            writer.writerows(comments)

extract_channel_info_task = PythonOperator(
    task_id='fetch_channel_info',
    python_callable=fetch_channel_info,
    op_kwargs={'channel_id': CHANNEL_ID},
    dag=dag,
)

def fetch_and_process_playlists(channel_id, **kwargs):
    playlists = fetch_playlists(channel_id)
    for playlist in playlists:
        playlist_id = playlist['id']
        process_playlist(playlist_id)

fetch_and_process_playlists_task = PythonOperator(
    task_id='fetch_and_process_playlists',
    python_callable=fetch_and_process_playlists,
    op_kwargs={'channel_id': CHANNEL_ID},
    provide_context=True,
    dag=dag,
)

extract_channel_info_task >> fetch_and_process_playlists_task
