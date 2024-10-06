from googleapiclient.discovery import build
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'airscholar',
    'start_date': datetime(2024, 5, 29)}

api_key='AIzaSyCwjIRc3jvlfwdIElXVVil0-HzbOZnpfAA'
channel_ids = ['UCtYLUTtgS3k1Fg4y5tAhLbw', # Statquest 
'UCCezIgC97PvUuR4_gbFUs5g', # Corey Schafer 
'UCfzlCWGWYyIQ0aLC5w48gBQ', # Sentdex 
'UCNU_lfiiWBdtULKOw6X0Dig', # Krish Naik 
'UCzL_0nIe8B4-7ShhVPfJkgw', # DatascienceDoJo 
'UCLLw7jmFsvfIVaUFsLs8mlQ', # Luke Barousse  
'UCiT9RITQ9PW6BhXK0y2jaeg', # Ken Jee 
'UC7cs8q-gJRlGwj4A8OmCmXg', # Alex the analyst 
'UCmOwsoHty5PrmE-3QhUBfPQ' ]# Jay Alammar 

channel_id=['UCmOwsoHty5PrmE-3QhUBfPQ' ]

videoId='-QH8fRhqFHM'

youtube = build('youtube', 'v3', developerKey=api_key)

output='C:/Users/Fatima-Ezzahra BOUR/Desktop/Project Kerzazi/nifi'


def get_data_channel(youtube,channel_ids):

        request = youtube.channels().list(
               part='snippet,contentDetails,statistics',
               id=','.join(channel_ids)
               )
        response = request.execute()

        return response

def format_data_channel(response):
        all_data=[]
        for i in range(len(response['items'])):
                data=dict(
                        Channel_name=response['items'][i]['snippet']['title'],
                        Subscribers=response['items'][i]['statistics']['subscriberCount'],
                        Views=response['items'][i]['statistics']['viewCount'],
                        Total_videos=response['items'][i]['statistics']['videoCount']
                        )
                all_data.append(data)

        return all_data

def get_comments_video(videoId):
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=videoId,
        maxResults=100
    )
    response = request.execute()
    comments=[]

    for item in response['items']:
        comment = item['snippet']['topLevelComment']['snippet']
        public = item['snippet']['isPublic']
        comments.append([
            comment['authorDisplayName'],
            comment['publishedAt'],
            comment['likeCount'],
            comment['textOriginal'],
            public
    ])
    while (1 == 1):
        try:
            nextPageToken = response['nextPageToken']
        except KeyError:
            break  
            
        nextRequest = youtube.commentThreads().list(part="snippet", videoId=videoId, maxResults=100, pageToken=nextPageToken)
        response = nextRequest.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            public = item['snippet']['isPublic']
            comments.append([
                comment['authorDisplayName'],  
                comment['publishedAt'],         
                comment['likeCount'],           
                comment['textOriginal'],        
                public                          
            ])
    return comments

def delivery_callback(err, msg):
    if err:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def get_videos_id(youtube,playlist_id):
    request=youtube.playlistItems().list(
        part='ContentDetails',
        playlistId=playlist_id,
        maxResults=100
    )
    response=request.execute()
    video_ids=[]
    for i in range(len(response['items'])):
        video_ids.append(response['items'][i]['contentDetails']['videoId'])
    next_page_token=response.get('nextPageToken')
    more_pages=True

    while more_pages:
        if next_page_token is None:
            more_pages=False
        else:
            request=youtube.playlistItems().list(
                 part='ContentDetails',
                 playlistId=playlist_id,
                 maxResults=50,
                 pageToken=next_page_token)
            response=request.execute()
        
            for i in range(len(response['items'])):
                video_ids.append(response['items'][i]['contentDetails']['videoId'])
            next_page_token=response.get('nextPageToken')
    return video_ids

def get_playlist_videos(youtube,video_ids):
    all_videos_stat = []
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids[i:i+50]))
        response = request.execute()
        
        for video in response['items']:
            video_stats = {
                'Title': video['snippet']['title'],
                'published_date': video['snippet']['publishedAt'],
                'Views': video['statistics']['viewCount']
            }
            # Vérifier si la clé 'commentCount' existe dans video['statistics']
            if 'commentCount' in video['statistics']:
                video_stats['Comments'] = video['statistics']['commentCount']
            if 'likeCount' in video['statistics']:
                video_stats['Likes'] = video['statistics']['likeCount']
            all_videos_stat.append(video_stats)
    return all_videos_stat

def f(data,topic_name):
    import json
    from confluent_kafka import Producer 

    producer = Producer({'bootstrap.servers': 'broker:29092'})
    producer.produce(topic_name, value=json.dumps(data), callback=delivery_callback)
    producer.flush()
def scrape_channel_statistics():

    topic_name='channels_data'
    channel_data=get_data_channel(youtube,channel_ids)
    channel_data=format_data_channel(channel_data)
    for data in channel_data:
        f(data,topic_name)


def get_playlist_id(youtube, channel_id):
    request = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    )
    response = request.execute()

    if 'items' in response:
        if len(response['items']) > 0:
            return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    return None
def get_channel_name(youtube,channel_id):
    request = youtube.channels().list(
        part='contentDetails,snippet',
        id=channel_id
    )
    response = request.execute()

    if 'items' in response:
        if len(response['items']) > 0:
            return response['items'][0]['snippet']['title']
    return None
def scrape_playlist_statistics(channel_id):
    channel_name=get_channel_name(youtube,channel_id)
    channel_name_sans_espaces = channel_name.replace(" ", "")

    topic_name= channel_name_sans_espaces+'_details'
    playlist_id = get_playlist_id(youtube,channel_id)
    videos = get_videos_id(youtube, playlist_id)
    video_details = get_playlist_videos(youtube, videos)
    for detail in video_details :
        f(detail,topic_name)
    #write_csv(video_details, f'{channel_name_sans_espaces}_videos.csv')

def scrape_video_comments(videoId):
    topic_name='comments'
    video_comments=get_comments_video(videoId)
    for comment in video_comments:
        f(comment,topic_name)
    '''comments_data = [{
        'authorDisplayName': comment[0],
        'publishedAt': comment[1],
        'likeCount': comment[2],
        'textOriginal': comment[3],
        'isPublic': comment[4]
    } for comment in video_comments] '''
    # write_csv(comments_data, 'video_comments.csv')


dag=DAG('kafka_stream', default_args=default_args, schedule_interval='@daily',catchup=False) 

task_scrape_channel_statistics = PythonOperator(
    task_id='scrape_channel_statistics',
    python_callable=scrape_channel_statistics,
    dag=dag
    )
for channel_1 in channel_id:
    task_id = f'scrape_playlist_statistics_{channel_1}'
    scrape_playlist_task = PythonOperator(
        task_id=task_id,
        python_callable=scrape_playlist_statistics,
        op_args=[channel_1],
        dag=dag
    )
task_scrape_comments= PythonOperator(
        task_id='scrape_comments',
        python_callable=scrape_video_comments,
        op_args=[videoId],
        dag=dag
    )
