"""
Food Safety Tracker daily ingestion.

Principles:
- Prefer primary government evidence.
- News can discover an incident, but is not automatically treated as adjudicated fact.
- Every published record carries source type + verification status.
- Uncertain extractions go to data/review_queue.csv rather than the public incident table.
- Positive/compliance records are supported alongside enforcement records.
"""

import csv, hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import feedparser, requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/food_safety_incidents.csv"
QUEUE=ROOT/"data/review_queue.csv"
PUBLIC=ROOT/"public"
PUBLIC.mkdir(exist_ok=True)

FIELDS=[
"incident_id","restaurant_name","location","city","state",
"date_reported","date_inspection","authority","finding",
"finding_categories","action_taken","samples_collected",
"closure_status","verification_status","source_name",
"source_type","source_url","evidence_excerpt","last_updated"
]

KEYWORDS=[
"food safety","food-safety","fssai","food safety department",
"restaurant raid","restaurant inspection","licence suspended",
"license suspended","food licence","food license","adulterated",
"adulteration","expired food","cockroaches","rodent","food sample",
"inspection passed","compliant inspection","licence restored",
"license restored","improvement notice","show cause notice"
]

QUERIES=[
'"food safety" restaurant India FSSAI',
'restaurant inspection FSSAI India',
'restaurant raid FSSAI India',
'"food safety department" restaurant India',
'"licence suspended" restaurant FSSAI India',
'"license suspended" restaurant FSSAI India',
'adulterated restaurant India food safety',
'"inspection passed" restaurant India food safety',
'"licence restored" restaurant FSSAI India'
]

def norm(s): return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()

def load(path, fields):
    if not path.exists(): return []
    with path.open(newline="",encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def save(path, rows, fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})

def article(url):
    try:
        r=requests.get(url,headers={"User-Agent":"FoodSafetyTracker/1.0"},timeout=20)
        r.raise_for_status()
        s=BeautifulSoup(r.text,"html.parser")
        for x in s(["script","style","noscript","svg"]): x.decompose()
        return " ".join(s.stripped_strings)[:120000]
    except Exception:
        return ""

def source_type(title,url,text):
    u=(url or "").lower()
    if any(x in u for x in [".gov.in","fssai.gov.in","fssai.in"]): return "Official"
    if any(x in u for x in ["timesofindia","indianexpress","hindustantimes","reuters","thehindu","indiatoday","telegraphindia"]): return "News"
    return "Other"

def categories(t):
    t=t.lower(); out=[]
    rules={
      "Pest infestation":["cockroach","rodent","rats","mice","pest infestation"],
      "Expired food":["expired food","expired products","past expiry"],
      "Spoiled / stale food":["rotten","spoiled","stale","worm-infested","foul smell"],
      "Microbial / fungal contamination":["fungal contamination","mould","mold","microbial contamination"],
      "Adulteration":["adulterated","adulteration","fake ghee","substitution"],
      "Unsafe additives / colours":["synthetic colour","synthetic color","unauthorised colour","unauthorized colour"],
      "Foreign matter":["foreign matter","foreign material"],
      "Labelling / date-marking":["labelling","labeling","mislabelled","mislabeled","date marking"],
      "Temperature control":["temperature","cold storage","hot food","thawing"],
      "Cross-contamination / segregation":["cross-contamination","segregation","vegetarian and non-vegetarian"],
      "Poor hygiene / sanitation":["unhygienic","poor hygiene","filthy","greasy","dirty kitchen"],
      "Waste / drainage":["drainage","waste","stagnant water","open dustbin"],
      "Food-handler hygiene":["food handlers","food-handler","personal hygiene"],
      "Medical / training records":["medical fitness","training records","health records"],
      "Licensing / registration":["without fssai","without licence","without license","unlicensed"],
      "Storage / packaging":["storage","packaging","refrigerator","freezer"],
      "Inspection passed":["passed inspection","compliant inspection","found compliant"]
    }
    for k,ws in rules.items():
        if any(w in t for w in ws): out.append(k)
    return "; ".join(dict.fromkeys(out))

def actions(t):
    t=t.lower(); out=[]
    if "licence suspended" in t or "license suspended" in t: out.append("Licence suspended")
    if any(x in t for x in ["closed","shut down","ordered to shut","operations stopped"]): out.append("Closure / stop order")
    if "show-cause notice" in t or "show cause notice" in t: out.append("Show-cause notice")
    if "improvement notice" in t: out.append("Improvement notice")
    if "licence restored" in t or "license restored" in t: out.append("Licence restored")
    if "sample" in t and "collect" in t: out.append("Samples collected")
    return "; ".join(dict.fromkeys(out))

def extract_name(title,text):
    pats=[
      r"(?:restaurant|hotel|cafe|café|dhaba|eatery)\s+([A-Z][A-Za-z0-9&'(). -]{2,80})",
      r"([A-Z][A-Za-z0-9&'(). -]{2,80})\s+(?:restaurant|hotel|cafe|café|dhaba|eatery)"
    ]
    for p in pats:
        m=re.search(p,title+" "+text[:6000],re.I)
        if m: return m.group(1).strip(" .,-")
    return ""

def evidence(text):
    # Short excerpt around a strong enforcement phrase.
    for phrase in ["licence suspended","license suspended","closed","expired food","cockroach","adulterated","inspection passed","compliant"]:
        m=re.search(phrase,text,re.I)
        if m:
            a=max(0,m.start()-180); b=min(len(text),m.end()+420)
            return text[a:b]
    return text[:500]

def main():
    rows=load(DATA,FIELDS)
    queue=load(QUEUE,FIELDS)
    existing={(norm(r.get("restaurant_name")),r.get("date_reported","")) for r in rows+queue}

    candidates=[]
    for q in QUERIES:
        feed=feedparser.parse(
            "https://news.google.com/rss/search?q="+quote(q)+"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        candidates.extend(feed.entries[:30])

    added=0; queued=0
    for e in candidates:
        url=e.get("link","")
        if not url: continue
        text=article(url)
        blob=e.get("title","")+" "+text
        low=blob.lower()
        if not any(k in low for k in KEYWORDS): continue

        try:
            dt=dateparser.parse(e.get("published",e.get("updated",""))).date().isoformat()
        except Exception:
            dt=datetime.now(timezone.utc).date().isoformat()

        rn=extract_name(e.get("title",""),text)
        if not rn: continue

        st=source_type(e.get("title",""),url,text)
        cats=categories(blob)
        act=actions(blob)

        # Conservative publication rule:
        # primary official source OR explicit enforcement terms with identifiable establishment.
        publish = st=="Official" or bool(act and cats)
        verification = "Official source" if st=="Official" else "Reported by news; not independently verified"

        digest=hashlib.sha1((url+dt).encode()).hexdigest()[:10]
        row={
          "incident_id":f"FS-AUTO-{datetime.now().year}-{digest}",
          "restaurant_name":rn,"location":"","city":"","state":"",
          "date_reported":dt,"date_inspection":"","authority":"",
          "finding":e.get("title","")+" — "+evidence(text),
          "finding_categories":cats,"action_taken":act,
          "samples_collected":"Yes" if re.search(r"samples?\s+(?:were\s+)?collected",low) else "Unknown",
          "closure_status":"Closed/Stopped" if re.search(r"closed|shut down|operations stopped",low) else "Unknown",
          "verification_status":verification,
          "source_name":e.get("source",{}).get("title","News source"),
          "source_type":st,"source_url":url,
          "evidence_excerpt":evidence(text),
          "last_updated":datetime.now(timezone.utc).isoformat()
        }

        key=(norm(rn),dt)
        if key in existing: continue

        if publish:
            rows.append(row); added+=1
        else:
            queue.append(row); queued+=1
        existing.add(key)

    save(DATA,rows,FIELDS)
    save(QUEUE,queue,FIELDS)
    (PUBLIC/"food_safety_incidents.json").write_text(
        json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Published: {added}; Review queue: {queued}; Total published: {len(rows)}")

if __name__=="__main__":
    main()
