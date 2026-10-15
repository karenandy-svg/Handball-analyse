"""Export public league games and verified PDF rosters/goals for WURFBILD.

Based on the endpoint and parsing approach in karenandy-svg/h4all-statistik.
No changes are made to that project or Handball4all. Requires pdfplumber.
"""
import argparse
import io
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API = 'https://spo.handball4all.de/service/if_g_json.php'
REPORT = 'https://spo.handball4all.de/misc/sboPublicReports.php?sGID='

def fetch(url, limit=5_000_000):
    req = urllib.request.Request(url, headers={'User-Agent': 'Wurfbild/0.3'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(limit+1)
    if len(data)>limit:
        raise ValueError('Response too large')
    return data

def parse_report(data, home, away, expected, game_no=None):
    import pdfplumber
    if not data.startswith(b'%PDF'):
        raise ValueError('Not a PDF')
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text='\n'.join(page.extract_text() or '' for page in pdf.pages)
    if game_no and not re.search(r'Spiel Nr\.\s*'+re.escape(game_no)+r'\b',text):
        raise ValueError('Report game number differs from schedule')
    report_names={}
    rosters={'home': [], 'away': []}
    if 'Mannschaftslisten' in text:
        section=text.split('Mannschaftslisten',1)[1].split('Spielverlauf',1)[0]
        side=None
        for line in section.splitlines():
            m=re.match(r'^(Heim|Gast):\s*(.+)$',line)
            if m:
                side='home' if m[1]=='Heim' else 'away'
                report_names[side]=m[2].strip()
                continue
            if line.startswith(('Handball4all','Presseinformation')):
                side=None
            m=re.match(r'^(\d{1,2})\s+(.+?)(?=\s+\d|$)',line)
            if side and m and re.search(r'[A-Za-zÄÖÜäöüß]',m[2]):
                n=str(int(m[1]))
                if any(p['number']==n for p in rosters[side]):
                    raise ValueError('Duplicate roster number')
                rosters[side].append({'number':n,'name':m[2].strip()})
    if not all(rosters.values()):
        raise ValueError('Both rosters required')
    goals=[]
    if 'Spielverlauf' not in text:
        raise ValueError('Missing goal timeline')
    timeline=text.split('Spielverlauf',1)[1]
    pattern=re.compile(r'^\d{2}:\d{2}:\d{2}\s+(\d{2,3}:[0-5]\d)\s+(\d+):(\d+)\s+(7m-Tor|Tor) durch\s+(.+?)\s+\((\d{1,2}),\s*(.+?)\)\s*$')
    previous=(0,0)
    for line in timeline.splitlines():
        if 'KEIN Tor durch' in line:
            continue
        if 'Tor durch' not in line:
            continue
        m=pattern.match(line)
        if not m:
            raise ValueError('Unrecognized goal event')
        clock,h,a,kind,name,number,label=m.groups()
        labels={'home': {home,report_names.get('home')},'away': {away,report_names.get('away')}}
        candidates=[side for side,names in labels.items() if label.strip() in names]
        side=candidates[0] if len(candidates)==1 else None
        score=(int(h),int(a))
        if side is None or score!=(previous[0]+(side=='home'),previous[1]+(side=='away')):
            raise ValueError('Nonsequential or ambiguous scoreboard')
        previous=score
        goals.append({'time':clock,'side':side,'player':str(int(number)),'playerName':name.strip(),'homeScore':score[0],'awayScore':score[1],'sevenMeter':kind=='7m-Tor'})
    if previous!=tuple(expected) or len(goals)!=sum(expected):
        raise ValueError('Goal total differs from official result')
    return rosters,goals

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--org',default='216');parser.add_argument('--league',default='161291')
    parser.add_argument('--half-minutes',type=int,default=25)
    parser.add_argument('--reports',type=int,default=20)
    parser.add_argument('--output',default='output/handball4all-161291.json')
    args=parser.parse_args()
    if not args.org.isdigit() or not args.league.isdigit() or not 0<=args.reports<=100 or args.half_minutes not in (20,25,30):
        parser.error('Invalid organization, league, report limit or half length')
    url=API+'?'+urllib.parse.urlencode({'cmd':'ps','og':args.org,'cl':args.league,'ca':'1','do':datetime.now().strftime('%Y-%m-%d')})
    raw=json.loads(fetch(url));root=raw[0]
    season=str(root.get('menu',{}).get('period',{}).get('selectedID',''))
    games=root.get('content',{}).get('futureGames',{}).get('games',[])
    if not isinstance(games,list) or not games or not season:
        raise ValueError('Missing league schedule or season')
    result={'format':'wurfbild-handball4all','version':1,'organization':args.org,'league':args.league,'season':season,'exportedAt':datetime.now().astimezone().isoformat(timespec='seconds'),'halfMinutes':args.half_minutes,'games':[]}
    checked=0
    for row in games:
        home=row.get('gHomeTeam','').strip();away=row.get('gGuestTeam','').strip()
        if not home or not away or not str(row.get('gID','')).isdigit():
            continue
        g={'externalId':str(row['gID']),'reportId':str(row.get('sGID','')),'number':str(row.get('gNo','')),'date':datetime.strptime(row['gDate'],'%d.%m.%y').strftime('%Y-%m-%d'),'startTime':row.get('gTime',''),'home':home,'away':away,'rosters':{'home':[],'away':[]},'officialGoals':[],'reportVerified':False}
        h=str(row.get('gHomeGoals','')).strip();a=str(row.get('gGuestGoals','')).strip()
        g['officialScore']=[int(h),int(a)] if h.isdigit() and a.isdigit() else None
        if g['officialScore'] is not None and g['reportId'].isdigit() and g['reportId']!='0' and checked<args.reports:
            checked+=1
            try:
                rosters,goals=parse_report(fetch(REPORT+g['reportId'],2_000_000),home,away,g['officialScore'],g['number'])
                g.update(rosters=rosters,officialGoals=goals,reportVerified=True)
                print(f"Verified game {g['number']}: {len(goals)} goals",flush=True)
            except Exception as exc:
                g['reportNote']=str(exc)
                print(f"Skipped report {g['number']}: {exc}",flush=True)
            time.sleep(.3)
        result['games'].append(g)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'path':str(path),'games':len(result['games']),'verifiedReports':sum(g['reportVerified'] for g in result['games']),'season':season}))

if __name__=='__main__':
    main()
