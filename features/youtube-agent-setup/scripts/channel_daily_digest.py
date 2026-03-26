#!/usr/bin/env python3
import argparse, json, os, re, subprocess, random
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
from agentmail import AgentMail

API_BASE = "https://www.googleapis.com/youtube/v3"
STATE_PATH = Path('/home/ec2-user/.openclaw/workspace/features/youtube-agent-setup/data/channel_state.json')

AI_CHANNELS = [
    "https://youtube.com/@natebjones",
    "https://youtube.com/@MattWolfe",
    "https://youtube.com/@aiexplained-official",
    "https://youtube.com/@MatthewBerman",
    "https://youtube.com/@Fireship",
    "https://youtube.com/@DaveShap",
    "https://youtube.com/@WesRoth",
    "https://youtube.com/@AIAdvantage"
]

def yt_key():
    if os.getenv('YOUTUBE_API_KEY'):
        return os.getenv('YOUTUBE_API_KEY')
    cfg = json.loads(Path('/home/ec2-user/.openclaw/openclaw.json').read_text())
    return cfg['skills']['entries']['goplaces']['apiKey']

def api_get(path, params):
    r = requests.get(f"{API_BASE}/{path}", params=params, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"YouTube API {r.status_code}: {r.text[:300]}")
    return r.json()

def resolve_channel_id(handle_or_url, key):
    s = handle_or_url.strip()
    if s.startswith('http'):
        m = re.search(r'/@([A-Za-z0-9._-]+)', s)
        if m:
            handle = m.group(1)
            d = api_get('channels', {'part':'id,snippet','forHandle':handle,'key':key})
            items=d.get('items',[])
            if items:
                return items[0]['id'], items[0].get('snippet',{}).get('title', handle)
    if s.startswith('@'):
        s=s[1:]
    d = api_get('channels', {'part':'id,snippet','forHandle':s,'key':key})
    items=d.get('items',[])
    if not items:
        raise RuntimeError('Could not resolve channel handle/url')
    return items[0]['id'], items[0].get('snippet',{}).get('title', s)

def load_state():
    if STATE_PATH.exists():
        try: return json.loads(STATE_PATH.read_text())
        except: return {}
    return {}

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2)+"\n")

def priority(meta, transcript):
    if not meta.get('ok'):
        return '🧊 Skip'
    st = meta['data']['video'].get('statistics', {})
    views = int(st.get('viewCount', 0) or 0)
    comments = int(st.get('commentCount', 0) or 0)
    text = ''
    if transcript.get('ok'):
        text = (transcript['data'].get('full_text') or '').lower()
    hot = any(k in text for k in ['breaking','urgent','warning','leak','lawsuit','security'])
    if hot or comments > 2000:
        return '🔥 Watch now'
    if views > 10000 or comments > 200:
        return '👀 Worth a look'
    return '🧊 Skip'

def run_pipeline(video_id, email_to):
    key = yt_key()
    cmd = [
        'python3', '/home/ec2-user/.openclaw/workspace/features/youtube-agent-setup/scripts/run_pipeline.py',
        '--video', video_id,
        '--api-key', key,
        '--comment-pages', '1',
        '--comment-max-results', '5',
        '--languages', 'en',
        '--save-pgmemory'
    ]
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        return {'ok': False, 'error': p.stdout or p.stderr}
    return json.loads(p.stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--channel', required=True)
    ap.add_argument('--email-to', required=True)
    ap.add_argument('--max-videos', type=int, default=5)
    ap.add_argument('--inbox', default='dougyfresh@agentmail.to')
    args = ap.parse_args()

    key = yt_key()
    
    # If the user passed 'AI_MIX', pick random channels
    if args.channel == 'AI_MIX':
        channel_list = random.sample(AI_CHANNELS, 3) # Pick 3 channels
        is_mix = True
    elif ',' in args.channel:
        channel_list = [c.strip() for c in args.channel.split(',') if c.strip()]
        is_mix = True
    else:
        channel_list = [args.channel]
        is_mix = False

    state = load_state()
    all_new_items = []
    
    channel_titles = []
    channel_ids = []

    for c in channel_list:
        try:
            ch_id, ch_title = resolve_channel_id(c, key)
            channel_ids.append(ch_id)
            channel_titles.append(ch_title)
            
            last_seen = state.get(ch_id, {}).get('last_seen_published_at')
            
            params = {
                'part':'snippet', 'channelId':ch_id, 'order':'date', 'type':'video',
                'maxResults': 5, 'key': key
            }
            data = api_get('search', params)
            items = data.get('items', [])
            
            for it in items:
                pub = it['snippet'].get('publishedAt')
                if (not last_seen) or (pub and pub > last_seen):
                    it['source_channel'] = ch_title
                    it['source_channel_id'] = ch_id
                    all_new_items.append((it, pub))
                    
            if items:
                newest_pub = max((x['snippet'].get('publishedAt') for x in items if x.get('snippet')), default=last_seen)
                state[ch_id] = {'last_seen_published_at': newest_pub, 'channel': c, 'updated_at': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            print(f"Failed to fetch for channel {c}: {e}")

    # Sort new items by date (newest first)
    all_new_items.sort(key=lambda x: x[1], reverse=True)
    
    # Take the top N across all checked channels
    # Or shuffle if they wanted 'randomly pick and choose'
    if is_mix:
        random.shuffle(all_new_items)
        
    selected_items = [it[0] for it in all_new_items][:args.max_videos]

    videos = []
    for it in selected_items:
        vid = it['id']['videoId']
        result = run_pipeline(vid, args.email_to)
        meta = result.get('results',{}).get('metadata',{})
        tr = result.get('results',{}).get('transcript',{})
        title = it['snippet'].get('title')
        videos.append({
            'video_id': vid,
            'title': title,
            'channel_name': it.get('source_channel', channel_titles[0]),
            'url': f'https://www.youtube.com/watch?v={vid}',
            'published_at': it['snippet'].get('publishedAt'),
            'priority': priority(meta, tr),
            'status': 'OK' if result.get('results',{}).get('metadata',{}).get('ok') else 'PARTIAL',
            'summary': (tr.get('data',{}).get('full_text','')[:220] + '...') if tr.get('ok') else 'Transcript unavailable'
        })

    subject_title = "AI News Mix" if is_mix else channel_titles[0]
    
    lines = [
        f'YouTube Daily Digest',
        f'Run: {datetime.now(timezone.utc).isoformat()}',
        f'Channels: {", ".join(channel_titles)}',
        f'New videos found: {len(videos)}',
        ''
    ]

    if videos:
        for i,v in enumerate(videos,1):
            lines += [
                f'{i}) {v["priority"]} {v["title"]} (from {v["channel_name"]})',
                f'   URL: {v["url"]}',
                f'   Published: {v["published_at"]}',
                f'   Pipeline: {v["status"]}',
                f'   Summary: {v["summary"]}',
                f'   📚 Send to NotebookLLM: https://t.me/TheDoug50_bot?start=notebook_upload_{v["video_id"]}',
                ''
            ]
    else:
        lines += ['No new uploads since last check.']

    client = AgentMail(api_key=os.getenv('AGENTMAIL_API_KEY'))
    resp = client.inboxes.messages.send(
        inbox_id=args.inbox,
        to=args.email_to,
        subject=f'YouTube daily digest: {subject_title}',
        text='\n'.join(lines)
    )

    save_state(state)
    print(json.dumps({'ok': True, 'channels': channel_titles, 'videos_in_digest': len(videos), 'message_id': getattr(resp,'message_id',None)}))

if __name__ == '__main__':
    main()
