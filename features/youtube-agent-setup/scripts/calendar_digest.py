#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone, timedelta
import requests


from zoneinfo import ZoneInfo
def parse_ics_dt(value: str, tzid: str = None):
    value = (value or '').strip()
    try:
        if value.endswith('Z') and 'T' in value:
            return datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        if 'T' in value:
            dt = datetime.strptime(value, '%Y%m%dT%H%M%S')
            if tzid == 'Eastern Standard Time':
                dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
            elif tzid == 'Central Standard Time':
                dt = dt.replace(tzinfo=ZoneInfo('America/Chicago'))
            elif tzid == 'Mountain Standard Time':
                dt = dt.replace(tzinfo=ZoneInfo('America/Denver'))
            elif tzid == 'Pacific Standard Time':
                dt = dt.replace(tzinfo=ZoneInfo('America/Los_Angeles'))
            else:
                dt = dt.replace(tzinfo=ZoneInfo('America/Chicago'))
            return dt.astimezone(timezone.utc)
        return datetime.strptime(value, '%Y%m%d').replace(tzinfo=ZoneInfo('America/Chicago')).astimezone(timezone.utc)
    except Exception:
        return None


def fetch_calendar_lookahead(calendar_url: str, hours: int = 24, max_items: int = 12):
    candidates = [calendar_url]
    if calendar_url.endswith('calendar.html'):
        base_ics = calendar_url.replace('calendar.html', 'calendar.ics')
        candidates = [base_ics + '?cmd=ics', base_ics, calendar_url]

    raw = None
    last_err = None
    for u in candidates:
        try:
            r = requests.get(u, timeout=25)
            if r.status_code == 200 and 'BEGIN:VCALENDAR' in r.text:
                raw = r.text
                break
            last_err = f'HTTP {r.status_code}'
        except Exception as e:
            last_err = str(e)

    if not raw:
        return {'ok': False, 'error': f'Unable to fetch ICS ({last_err})'}

    lines = []
    for line in raw.splitlines():
        if line.startswith(' ') and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)

    events = []
    in_event = False
    current = {}
    for line in lines:
        if line == 'BEGIN:VEVENT':
            in_event = True
            current = {}
            continue
        if line == 'END:VEVENT':
            in_event = False
            events.append(current)
            current = {}
            continue
        if in_event and ':' in line:
            k_raw, v = line.split(':', 1)
            k = k_raw.split(';', 1)[0]
            current[k] = v
            if k == 'DTSTART' and 'TZID=' in k_raw:
                current['TZID'] = k_raw.split('TZID=')[1].split(';')[0]

    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)
    upcoming = []
    for e in events:
        start = parse_ics_dt(e.get('DTSTART', ''), e.get('TZID'))
        if not start:
            continue
        if now <= start <= end:
            upcoming.append({
                'start_cdt': start,
                'summary': e.get('SUMMARY', '(no title)'),
                'location': e.get('LOCATION', ''),
            })

    upcoming.sort(key=lambda x: x['start_cdt'])
    return {'ok': True, 'events': upcoming[:max_items]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--calendar-url', required=True)
    ap.add_argument('--hours', type=int, default=24)
    args = ap.parse_args()

    res = fetch_calendar_lookahead(args.calendar_url, hours=args.hours)
    if not res.get('ok'):
        print(f"Calendar digest unavailable: {res.get('error')}")
        return

    events = res['events']
    out = [
        f"📅 **Work Lookahead ({args.hours}h)**",
        ""
    ]
    if not events:
        out.append("No upcoming events.")
    else:
        for i, ev in enumerate(events, 1):
            t_cdt = ev['start_cdt'].astimezone(timezone(timedelta(hours=-5)))
            t = t_cdt.strftime('%I:%M %p').lstrip('0')
            loc = f" @ {ev['location']}" if ev.get('location') else ''
            out.append(f"• **{t}**: {ev['summary']}{loc}")

    print('\n'.join(out))


if __name__ == '__main__':
    main()
