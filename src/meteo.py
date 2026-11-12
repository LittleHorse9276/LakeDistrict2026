# Météo spot par spot, 100 % AccuWeather.
# Usage : python3 meteo.py in.html out.html   (retire d'abord tout bloc météo existant)
# Mise à jour : modifier EMIS, FC (prévision journalière par station) et HOURLY
# (prévision à l'heure de passage, à remplir à J-3), puis relancer.
import re, sys, json, html as H

EMIS = "12 nov. 2026"
BASE = "https://www.accuweather.com/en/gb/{slug}/november-weather/{key}"

STATIONS = {  # clé AccuWeather, nom, slug
 "NB":("327507","Newby Bridge","newby-bridge/la12-8"),   "CO":("327480","Coniston","coniston/la21-8"),
 "HK":("713440","Hawkshead","hawkshead/la22-0"),         "SA":("2524487","Sawrey","sawrey/la22-0"),
 "EL":("714498","Elterwater","elterwater/la22-9"),       "LL":("2522965","Little Langdale","little-langdale/la22-9"),
 "GR":("327488","Grasmere","grasmere/la22-9"),           "AM":("327467","Ambleside","ambleside/la22-0"),
 "PA":("327510","Patterdale","patterdale/ca11-0"),       "HT":("2522463","Howtown","howtown/ca10-2"),
 "DO":("714953","Dockray","dockray/ca11-0"),             "KE":("327458","Keswick","keswick/ca12-4"),
 "RO":("709969","Rosthwaite","rosthwaite/ca12-5"),       "SE":("2524522","Seatoller","seatoller/ca12-5"),
 "BU":("327476","Buttermere","buttermere/ca13-9"),       "LO":("711704","Loweswater","loweswater/ca13-0"),
 "BR":("2530896","Braithwaite","braithwaite/ca12-5"),    "AP":("2519576","Applethwaite","applethwaite/ca12-4"),
 "WA":("2525740","Wasdale Head","wasdale-head/ca20-1"),  "EG":("2521450","Eskdale Green","eskdale-green/ca19-1"),
}
# Libellés AccuWeather -> (français, icône)
TR = {
 "Mostly sunny and cool":("Plutôt ensoleillé et frais","🌤️"),
 "Hazy and cool":("Brumeux et frais","🌫️"),
 "Sunny and cool":("Ensoleillé et frais","☀️"),
 "Cloudy with a couple of showers":("Couvert, quelques averses","🌧️"),
 "Mostly cloudy with a little rain":("Plutôt nuageux, un peu de pluie","🌦️"),
 "Partly sunny with a couple of showers":("Éclaircies, quelques averses","🌦️"),
 "Mostly sunny with a shower in spots":("Plutôt ensoleillé, averse locale","🌦️"),
 "Partly sunny with a shower in spots":("Éclaircies, averse locale","🌦️"),
 "Sunny":("Ensoleillé","☀️"),
 "Increasing cloudiness":("Nuages en augmentation","⛅"),
 "Mostly sunny":("Plutôt ensoleillé","🌤️"),
 "Decreasing clouds":("Nuages en dissipation","🌤️"),
 "Mostly cloudy with a couple of showers":("Plutôt nuageux, quelques averses","🌦️"),
 "Mostly cloudy with a shower in spots":("Plutôt nuageux, averse locale","🌦️"),
 "Cloudy with a shower in spots":("Couvert, averse locale","🌦️"),
 "Cloudy with showers":("Nuageux, averses","🌦️"),
 "Cloudy with showery rains":("Nuageux, pluies en averses","🌦️"),
 "Cloudy with occasional rain":("Nuageux, pluie par moments","🌧️"),
 "A shower and thunderstorm":("Averse et orage","⛈️"),
 "A few showers in the morning":("Quelques averses le matin","🌦️"),
 "Showers around in the morning":("Averses éparses le matin","🌦️"),
 "Cloudy with a touch of rain":("Nuageux, un peu de pluie","🌦️"),
 "Windy; a little p.m. rain":("Venteux, un peu de pluie l'après-midi","🌬️"),
 "A little morning rain":("Un peu de pluie le matin","🌦️"),
 "A little rain in the morning":("Un peu de pluie le matin","🌦️"),
 "Mostly cloudy":("Plutôt nuageux","☁️"),
 "Cloudy most of the time":("Nuageux la plupart du temps","☁️"),
 "Partly sunny":("Éclaircies","⛅"),
 "Periods of rain":("Pluie par périodes","🌧️"),
 "Cloudy":("Couvert","☁️"),
 "Cloudy with a little rain":("Couvert, un peu de pluie","🌦️"),
}
F2C = lambda f: round((f-32)*5/9)
# FC[station][jour] = (libellé AccuWeather, max °F, min °F) — relevé du 25 oct.
C  = {8:("Cloudy with showery rains",52,42),9:("Cloudy with occasional rain",52,43),
      10:("A shower and thunderstorm",51,41),11:("Cloudy with occasional rain",49,41),
      12:("Windy; a little p.m. rain",51,42),13:("A little rain in the morning",51,41)}
K  = {8:("Periods of rain",53,44),9:("Showers around in the morning",53,43),
      10:("A morning t-shower; some sun",52,41),11:("Cloudy with a touch of rain",48,41),
      12:("Windy; a little p.m. rain",51,43),13:("A little morning rain",52,41)}
FC = {s:C for s in ("CO","HK","SA","EL","LL","GR","AM","PA")}
FC.update({s:K for s in ("KE","RO","SE","BU","BR","AP")})
FC["NB"]={8:("Cloudy with showers",53,44)}
FC["HT"]={11:("A few showers in the morning",46,39)}
FC["DO"]={11:("Showers around in the morning",46,38)}
FC["LO"]={12:("Windy; a little p.m. rain",51,41)}
FC["WA"]={13:("Mostly cloudy",54,42)}
FC["EG"]={13:("Cloudy most of the time",54,43)}


# HALF[(station, date, "m"|"a")] = (libellé, T °F, RealFeel °F, dir vent, vent mph, rafales mph, humidité %, pluie %, nuages %)
# Relevé AccuWeather du 9 nov. 2026 (J1 figé au relevé du 8). Croisement Met Office (pluie %, T °C à l'heure la plus proche ; 0 = <5 %) : Coniston J1-J2, Grasmere J3, Patterdale/Keswick J4, Keswick J5-J6 (Applethwaite seulement)
HALF = {
 ("NB",8,"a"):('Partly sunny',49,50,"SSE",4,10,90,25,70),
 ("HK",8,"a"):('Partly sunny',49,50,"SSW",4,8,91,25,70),
 ("SA",8,"a"):('Partly sunny',49,50,"SSW",4,8,91,25,70),
 ("CO",8,"a"):('Partly sunny',49,50,"SSW",4,8,91,25,70),
 ("EL",9,"m"):('Decreasing clouds',46,45,"NE",5,13,95,4,96),
 ("LL",9,"m"):('Decreasing clouds',46,45,"NE",5,13,95,4,96),
 ("CO",9,"m"):('Decreasing clouds',46,45,"NE",5,13,95,4,96),
 ("HK",9,"a"):('Decreasing clouds',48,49,"ENE",5,13,88,2,39),
 ("GR",10,"m"):('Cloudy',44,45,"NE",4,10,91,2,99),
 ("GR",10,"a"):('Cloudy',46,47,"NE",5,13,85,25,99),
 ("AM",10,"a"):('Cloudy',46,47,"NE",5,13,85,25,99),
 ("AM",11,"m"):('Partly sunny',45,47,"NNE",6,10,86,1,68),
 ("PA",11,"m"):('Partly sunny',45,47,"NNE",6,10,86,1,68),
 ("HT",11,"m"):('Partly sunny',42,46,"NNE",4,8,89,1,75),
 ("HT",11,"a"):('Partly sunny',44,47,"NW",4,9,86,3,41),
 ("DO",11,"a"):('Partly sunny',43,46,"SW",4,8,87,3,46),
 ("KE",11,"a"):('Partly sunny',48,52,"W",2,7,80,2,46),
 ("KE",12,"m"):('Sunny and cool',42,41,"NNW",5,16,81,0,3),
 ("RO",12,"m"):('Sunny and cool',42,41,"NNW",5,16,81,0,3),
 ("SE",12,"m"):('Sunny and cool',42,41,"NNW",5,16,81,0,3),
 ("BU",12,"m"):('Sunny and cool',42,41,"NNW",5,16,81,0,3),
 ("BU",12,"a"):('Sunny and cool',44,44,"NNW",6,15,68,0,0),
 ("LO",12,"a"):('Sunny and cool',44,41,"N",8,14,72,0,0),
 ("BR",12,"a"):('Sunny and cool',44,44,"NNW",6,15,68,0,0),
 ("AP",13,"m"):('Increasing cloudiness',42,45,"W",4,10,89,5,9),
 ("WA",13,"m"):('Increasing cloudiness',45,46,"S",6,10,80,4,9),
 ("EG",13,"m"):('Increasing cloudiness',44,45,"SW",6,10,82,4,6),
 ("EG",13,"a"):('Increasing cloudiness',47,46,"W",7,13,79,25,78),
}
# Relevé AccuWeather du 3 nov. 2026. Croisement Met Office (pluie %, T °C à l'heure la plus proche ; 0 = <5 %) pour les jours couverts (jusqu'au 12 nov.)
MO = {
 (1,"14h05"):(10,10),(1,"15h20"):(20,10),(1,"15h47"):(30,9),(1,"16h19"):(30,9),
 (2,"09h01"):(0,8),(2,"09h55"):(0,9),(2,"11h33"):(0,10),(2,"12h49"):(0,10),(2,"15h03"):(0,10),
 (3,"09h35"):(0,8),(3,"12h22"):(0,9),(3,"13h29"):(0,9),(3,"15h50"):(0,8),(3,"16h14"):(0,8),
 (4,"09h18"):(0,4),(4,"09h31"):(0,5),(4,"10h36"):(0,7),(4,"12h38"):(0,8),(4,"13h04"):(0,8),
 (4,"14h03"):(0,8),(4,"15h13"):(0,8),(4,"15h33"):(0,4),(4,"16h07"):(0,4),
 (5,"09h41"):(0,2),(5,"09h56"):(0,2),(5,"10h09"):(0,2),(5,"10h34"):(0,4),(5,"12h51"):(0,6),
 (5,"13h12"):(0,6),(5,"15h46"):(0,2),
 (6,"09h18"):(20,5),
}
KMH = lambda m: round(m*1.609)

DATE = {1:8,2:9,3:10,4:11,5:12,6:13}
# (jour, heure de passage, station)
STOPS = [
 (1,"14h05","NB"),(1,"15h20","CO"),(1,"15h47","HK"),(1,"16h19","SA"),
 (2,"09h01","EL"),(2,"09h55","LL"),(2,"11h33","LL"),(2,"12h49","CO"),(2,"15h03","HK"),
 (3,"09h35","GR"),(3,"12h22","GR"),(3,"13h29","GR"),(3,"15h50","AM"),(3,"16h14","AM"),
 (4,"09h18","AM"),(4,"09h31","PA"),(4,"10h36","HT"),(4,"12h38","HT"),(4,"13h04","HT"),(4,"14h03","DO"),(4,"15h13","KE"),(4,"15h33","KE"),(4,"16h07","KE"),
 (5,"09h41","KE"),(5,"09h56","KE"),(5,"10h09","KE"),(5,"10h34","RO"),(5,"12h51","SE"),
 (5,"13h12","BU"),(5,"15h46","LO"),
 (6,"09h18","AP"),(6,"11h26","WA"),(6,"12h34","EG"),
]
# HOURLY[(jour,"HHhMM")] = dict(txt=..., t=°C, rf=RealFeel °C, pop=%)  — à remplir à J-3
HOURLY = {
 (1,"14h05"):dict(txt='Intermittent clouds',t=9,rf=10,pop=20),
 (1,"15h20"):dict(txt='Intermittent clouds',t=8,rf=9,pop=20),
 (1,"15h47"):dict(txt='Intermittent clouds',t=8,rf=8,pop=20),
 (1,"16h19"):dict(txt='Intermittent clouds',t=8,rf=8,pop=20),
 (2,"09h01"):dict(txt='Cloudy',t=5,rf=6,pop=0),
 (2,"09h55"):dict(txt='Cloudy',t=6,rf=7,pop=0),
 (2,"11h33"):dict(txt='Cloudy',t=8,rf=7,pop=0),
 (2,"12h49"):dict(txt='Intermittent clouds',t=8,rf=8,pop=0),
 (2,"15h03"):dict(txt='Mostly sunny',t=8,rf=8,pop=0),
 (3,"09h35"):dict(txt='Cloudy',t=4,rf=5,pop=0),
 (3,"12h22"):dict(txt='Cloudy',t=7,rf=7,pop=0),
 (3,"13h29"):dict(txt='Cloudy',t=7,rf=8,pop=7),
 (3,"15h50"):dict(txt='Cloudy',t=7,rf=6,pop=7),
 (3,"16h14"):dict(txt='Cloudy',t=7,rf=6,pop=7),
 (4,"09h18"):dict(txt='Cloudy',t=4,rf=3,pop=0),
 (4,"09h31"):dict(txt='Intermittent clouds',t=4,rf=5,pop=0),
 (4,"10h36"):dict(txt='Intermittent clouds',t=4,rf=7,pop=0),
 (4,"12h38"):dict(txt='Partly sunny',t=6,rf=8,pop=0),
 (4,"13h04"):dict(txt='Partly sunny',t=6,rf=8,pop=0),
 (4,"14h03"):dict(txt='Partly sunny',t=6,rf=8,pop=0),
 (4,"15h13"):dict(txt='Partly sunny',t=8,rf=9,pop=0),
 (4,"15h33"):dict(txt='Partly sunny',t=7,rf=8,pop=0),
 (4,"16h07"):dict(txt='Partly sunny',t=7,rf=8,pop=0),
 (5,"09h41"):dict(txt='Sunny',t=2,rf=3,pop=0),
 (5,"09h56"):dict(txt='Sunny',t=2,rf=3,pop=0),
 (5,"10h09"):dict(txt='Sunny',t=2,rf=3,pop=0),
 (5,"10h34"):dict(txt='Sunny',t=4,rf=3,pop=0),
 (5,"12h51"):dict(txt='Sunny',t=6,rf=6,pop=0),
 (5,"13h12"):dict(txt='Sunny',t=6,rf=6,pop=0),
 (5,"15h46"):dict(txt='Sunny',t=4,rf=1,pop=0),
 (6,"09h18"):dict(txt='Sunny',t=1,rf=2,pop=0),
 (6,"11h26"):dict(txt='Mostly sunny',t=7,rf=7,pop=0),
 (6,"12h34"):dict(txt='Partly sunny',t=7,rf=8,pop=7),
}

CSS = """
/* météo */
.dwx{background:var(--peat-2);border-top:1px solid rgba(255,255,255,.07);padding:.6rem 1.5rem .7rem;color:#C9C2B2}
.dwx .wh{display:flex;flex-wrap:wrap;align-items:baseline;gap:.3rem .9rem}
.dwx .wt{font-family:'Fraunces',serif;font-size:1rem;color:#fff}
.dwx .wsrc{font-family:'JetBrains Mono',monospace;font-size:.56rem;letter-spacing:.08em;text-transform:uppercase;
  color:var(--peat);background:var(--bracken-l);padding:.12rem .45rem;border-radius:2px}
.dwx .wl{font-size:.8rem;margin:.3rem 0 0}
.dwx .wl b{color:#fff;font-weight:500}
.dwx .wl i{color:#9E9683}
.wx{display:flex;flex-wrap:wrap;gap:.3rem;margin:.3rem 0 .25rem}
.wx span,.wx a{font-family:'JetBrains Mono',monospace;font-size:.64rem;padding:.12rem .5rem;border-radius:10px;
  background:var(--paper-2);color:var(--ink-2);white-space:nowrap;text-decoration:none}
.wx .wd{background:#E3DCC4;color:var(--ink);white-space:normal}
.wx .wh0{background:transparent;border:1px dashed var(--paper-3);color:var(--ink-3)}
.wx .wmo{background:transparent;border:1px solid var(--paper-3);color:var(--ink-3)}
.wx .winc{background:#F6D9C7;color:#8A3B12;font-weight:600}
.wx a{background:transparent;color:var(--bracken);border:1px solid var(--paper-3)}
"""

def day_block(n):
    d=DATE[n]
    st=sorted({STATIONS[s][1] for j,_,s in STOPS if j==n})
    return ('<div class="dwx" data-wx="day"><div class="wh"><span class="wt">Météo AccuWeather</span>'
            '<span class="wsrc">Prévision émise le %s · J−%d · mise à jour à J−3</span></div>'
            '<div class="wl">Stations utilisées : <b>%s</b></div>'
            '<div class="wl"><i>Chaque spot porte la prévision de la station AccuWeather la plus proche. '
            'L\'heure par heure s\'affichera à l\'heure de passage quand AccuWeather la publiera (~J−3).</i></div></div>'
           )%(EMIS,d+6,H.escape(" · ".join(st)))

def mo_cell(n,hhmm,pop,tc):
    m=MO.get((n,hhmm))
    if not m: return ''
    inc=abs(m[0]-pop)>30 or abs(m[1]-tc)>3
    c='<span class="wmo">Met Office : pluie %s %% · %d°</span>'%(('<5' if m[0]<5 else str(m[0])),m[1])
    if inc: c+='<span class="winc">⚠ incertain</span>'
    return c

def stop_line(n,hhmm,s):
    key,name,slug=STATIONS[s]; d=DATE[n]
    hf="m" if int(hhmm[:2])<13 else "a"
    en,t,rf,wd,w,g,hu,pop,cl=HALF[(s,d,hf)]; fr,ic=TR.get(en,(en,"🌥️"))
    url=BASE.format(slug=slug,key=key)
    per="matin" if hf=="m" else "après-midi"
    hr=HOURLY.get((n,hhmm))
    if hr:
        hcell='<span class="wd">%s · %d° · ressenti %d° · pluie %d %%</span>'%(hhmm,hr["t"],hr["rf"],hr["pop"])
    else:
        hcell='<span class="wh0">%s : horaire à venir</span>'%hhmm
    return ('<div class="wx" data-wx="stop"><span class="wd" title="%s">%s %s (%s)</span>'
            '<span>%d° · ressenti %d°</span><span>☔ pluie %d %%</span><span>☁️ nuages %d %%</span>'
            '<span>💧 humidité %d %%</span><span>💨 %s %d km/h · rafales %d</span>%s'
            '%s<a href="%s" target="_blank" rel="noopener">%s ↗</a></div>')%(
            H.escape(en),ic,H.escape(fr),per,F2C(t),F2C(rf),pop,cl,hu,wd,KMH(w),KMH(g),hcell,mo_cell(n,hhmm,pop,F2C(t)),url,H.escape(name))

def strip(s):
    s=re.sub(r'<div class="dwx" data-wx="day">.*?</div></div>(?=<div class="dbody">)','',s,flags=re.S)
    s=re.sub(r'<div class="wx" data-wx="stop">.*?</div>','',s,flags=re.S)
    s=re.sub(r'\n/\* météo \*/.*?(?=</style>)','\n',s,flags=re.S)
    s=re.sub(r'<script type="application/json" id="wx-data">.*?</script>','',s,flags=re.S)
    return s

def main(src,dst):
    s=strip(open(src,encoding="utf-8").read())
    s=s.replace("</style>",CSS+"</style>",1)
    # Bandeau météo par jour supprimé à la demande (25 oct.) : la météo est uniquement sur les spots.
    miss=[]
    for n,hhmm,st in STOPS:
        a=s.find('id="j%d"'%n); b=s.find('class="day"',a+10); b=b if b>0 else len(s)
        m=re.compile(r'<div class="stop[^"]*"><div class="h">'+hhmm+r'</div><div class="c">.*?<div class="tt">.*?</div>',re.S).search(s,a,b)
        if not m: miss.append((n,hhmm)); continue
        s=s[:m.end()]+stop_line(n,hhmm,st)+s[m.end():]
    s=re.sub(r'Mis à jour le [^<]*?2026\.[^<]*','Mis à jour le 31 octobre 2026. Météo AccuWeather émise le %s.'%EMIS,s,count=1)
    s=s.replace("</body>",'<script type="application/json" id="wx-data">%s</script></body>'%json.dumps(
        {"emis":EMIS,"stations":STATIONS,"fc":{k:{str(d):v for d,v in x.items()} for k,x in FC.items()},
         "half":{"%s %d %s"%k:v for k,v in HALF.items()},"stops":STOPS,"hourly":{"%d %s"%k:v for k,v in HOURLY.items()}},ensure_ascii=False),1)
    open(dst,"w",encoding="utf-8").write(s)
    print("manquants:",miss)

if __name__=="__main__": main(sys.argv[1],sys.argv[2])
