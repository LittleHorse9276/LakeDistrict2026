# Météo spot par spot, 100 % AccuWeather.
# Usage : python3 meteo.py in.html out.html   (retire d'abord tout bloc météo existant)
# Mise à jour : modifier EMIS, FC (prévision journalière par station) et HOURLY
# (prévision à l'heure de passage, à remplir à J-3), puis relancer.
import re, sys, json, html as H

EMIS = "6 nov. 2026"
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
# Relevé AccuWeather du 6 nov. 2026. Croisement Met Office (pluie %, T °C à l'heure la plus proche ; 0 = <5 %) : Coniston J1-J2, Grasmere J3, Patterdale/Keswick J4, Keswick J5-J6 (Applethwaite seulement)
HALF = {
 ("NB",8,"a"):('Decreasing clouds',50,52,"SE",5,9,85,25,43),
 ("CO",8,"a"):('Partly sunny',50,50,"S",5,8,86,25,63),
 ("HK",8,"a"):('Partly sunny',50,50,"S",5,8,86,25,63),
 ("SA",8,"a"):('Partly sunny',50,50,"S",5,8,86,25,63),
 ("EL",9,"m"):('Partly sunny',46,49,"ENE",5,12,90,2,40),
 ("LL",9,"m"):('Partly sunny',46,49,"ENE",5,12,90,2,40),
 ("CO",9,"m"):('Partly sunny',46,49,"ENE",5,12,90,2,40),
 ("HK",9,"a"):('Partly sunny',48,49,"NE",5,12,84,1,27),
 ("GR",10,"m"):('Mostly sunny',48,46,"ENE",7,12,81,1,15),
 ("GR",10,"a"):('Mostly cloudy with a little rain',49,47,"ENE",6,13,77,55,76),
 ("AM",10,"a"):('Mostly cloudy with a little rain',49,47,"ENE",6,13,77,55,76),
 ("AM",11,"m"):('Mostly cloudy',49,47,"NE",6,9,76,1,79),
 ("PA",11,"m"):('Mostly cloudy',49,47,"NE",6,9,76,1,79),
 ("HT",11,"m"):('Mostly cloudy',47,45,"ESE",6,10,74,1,74),
 ("HT",11,"a"):('Mostly cloudy',46,45,"ESE",6,9,66,12,80),
 ("DO",11,"a"):('Mostly sunny',46,44,"ESE",7,12,66,4,23),
 ("KE",11,"a"):('Partly sunny',48,47,"E",6,12,82,6,43),
 ("KE",12,"m"):('Mostly sunny',45,43,"ENE",6,14,79,1,47),
 ("RO",12,"m"):('Mostly sunny',45,43,"ENE",6,14,79,1,47),
 ("SE",12,"m"):('Mostly sunny',45,43,"ENE",6,14,79,1,47),
 ("BU",12,"m"):('Mostly sunny',45,43,"ENE",6,14,79,1,47),
 ("LO",12,"a"):('Mostly sunny',46,42,"NNE",8,20,59,0,0),
 ("BR",12,"a"):('Mostly sunny',46,43,"ENE",7,14,76,0,4),
 ("AP",13,"m"):('Sunny',45,45,"NE",5,10,83,1,1),
 ("WA",13,"m"):('Sunny',44,36,"NNW",12,24,62,1,0),
 ("EG",13,"a"):('Sunny',47,41,"NNW",12,24,60,0,0),
}
# Relevé AccuWeather du 3 nov. 2026. Croisement Met Office (pluie %, T °C à l'heure la plus proche ; 0 = <5 %) pour les jours couverts (jusqu'au 12 nov.)
MO = {
 (1,"14h05"):(30,10),(1,"15h20"):(30,10),(1,"15h47"):(20,9),(1,"16h19"):(20,9),
 (2,"09h01"):(0,7),(2,"09h55"):(0,8),(2,"11h33"):(0,8),(2,"12h49"):(0,9),(2,"15h03"):(0,8),
 (3,"09h35"):(20,10),(3,"12h22"):(20,11),(3,"13h29"):(20,11),(3,"15h50"):(30,10),(3,"16h14"):(30,10),
 (4,"09h18"):(20,8),(4,"09h31"):(20,9),(4,"10h36"):(20,10),(4,"12h38"):(20,10),(4,"13h04"):(20,10),
 (4,"14h03"):(20,10),(4,"15h13"):(10,10),(4,"15h33"):(10,10),(4,"16h07"):(10,10),
 (5,"09h20"):(20,7),(5,"09h35"):(20,8),(5,"09h48"):(20,8),(5,"10h21"):(20,8),(5,"12h20"):(20,8),
 (5,"12h39"):(20,8),(5,"15h25"):(20,8),(5,"16h17"):(10,8),
 (6,"09h50"):(0,7),
}
KMH = lambda m: round(m*1.609)

DATE = {1:8,2:9,3:10,4:11,5:12,6:13}
# (jour, heure de passage, station)
STOPS = [
 (1,"14h05","NB"),(1,"15h20","CO"),(1,"15h47","HK"),(1,"16h19","SA"),
 (2,"09h01","EL"),(2,"09h55","LL"),(2,"11h33","LL"),(2,"12h49","CO"),(2,"15h03","HK"),
 (3,"09h35","GR"),(3,"12h22","GR"),(3,"13h29","GR"),(3,"15h50","AM"),(3,"16h14","AM"),
 (4,"09h18","AM"),(4,"09h31","PA"),(4,"10h36","HT"),(4,"12h38","HT"),(4,"13h04","HT"),(4,"14h03","DO"),(4,"15h13","KE"),(4,"15h33","KE"),(4,"16h07","KE"),
 (5,"09h20","KE"),(5,"09h35","KE"),(5,"09h48","KE"),(5,"10h21","RO"),(5,"12h20","SE"),
 (5,"12h39","BU"),(5,"15h25","LO"),(5,"16h17","BR"),
 (6,"09h50","AP"),(6,"11h55","WA"),(6,"13h11","EG"),
]
# HOURLY[(jour,"HHhMM")] = dict(txt=..., t=°C, rf=RealFeel °C, pop=%)  — à remplir à J-3
HOURLY = {}

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
