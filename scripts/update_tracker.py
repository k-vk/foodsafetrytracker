import csv, json, os, re, hashlib
from datetime import datetime, timezone
from pathlib import Path
import feedparser, requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
CSV_PATH = DATA / "food_safety_incidents.csv"
JSON_PATH = PUBLIC / "food_safety_incidents.json"
REVIEW_PATH = DATA / "review_queue.csv"

QUERIES = [
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
CATEGORIES = {
    "Pest infestation":["cockroach","rodent","rat","pest","insect"],
    "Expired food":["expired","expiry","past date"],
    "Spoiled / stale food":["spoiled","stale","rotten"],
    "Microbial / fungal contamination":["microbial","bacterial","fungal","mould","mold"],
    "Adulteration":["adulterated","adulteration"],
    "Chemical contamination":["chemical contamination","toxic chemical"],
    "Foreign matter":["foreign object","foreign matter","insect in food"],
    "Unsafe additives / colours":["synthetic colour","synthetic color","unsafe colour","unsafe color","colouring agent"],
    "Labelling / date-marking":["label","labelling","labeling","date marking"],
    "Temperature control":["temperature","cold chain","refrigerat"],
    "Cross-contamination / segregation":["cross contamination","cross-contamination","segregation"],
    "Water / ice safety":["water quality","unsafe water","ice"],
    "Poor hygiene / sanitation":["hygiene","sanitation","unclean","dirty"],
    "Waste / drainage":["waste","drainage","sewage"],
    "Equipment / premises":["equipment","premises","kitchen"],
    "Food-handler hygiene":["food handler","food-handler","gloves","hairnet"],
    "Medical / training records":["medical certificate","training record"],
    "Licensing / registration":["license","licence","registration"],
    "Storage / packaging":["storage","packaging"]
}
POSITIVE = {
    "Inspection passed":["passed inspection","inspection passed","compliant inspection"],
    "Corrective action completed":["corrective action completed","compliance achieved","rectified"],
    "Licence restored / suspension revoked":["licence restored","license restored","suspension revoked"]
}
ACTIONS = ["seized","seizure","destroyed","disposed","notice issued","notice served",
           "licence suspended","license suspended","closed","closure","penalty","fine",
           "prosecution","sample collected","samples collected","inspection","raided","raid"]

FIELDS = ["incident_id","restaurant_name","location","city","state","date_reported","date_inspection",
          "authority","finding","finding_categories","action_taken","samples_collected","closure_status",
          "verification_status","source_name","source_type","source_url","evidence_excerpt","last_updated"]

def clean(s): return re.sub(r"\s+"," ",(s or "")).strip()
def categories(text):
    t=text.lower()
    found=[k for k, terms in CATEGORIES.items() if any(x in t for x in terms)]
    found += [k for k, terms in POSITIVE.items() if any(x in t for x in terms)]
    return list(dict.fromkeys(found))
def actions(text):
    t=text.lower()
    return [x for x in ACTIONS if x in t]
def article(url):
    try:
        r=requests.get(url,timeout=20,headers={"User-Agent":"FoodSafetyTracker/1.0"})
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        for x in soup(["script","style","noscript"]): x.decompose()
        return clean(soup.get_text(" "))
    except Exception:
        return ""
def source_type(url):
    u=url.lower()
    if ".gov.in" in u or "fssai.gov.in" in u or "fssai.in" in u: return "Official"
    if any(d in u for d in ["thehindu.com","indianexpress.com","hindustantimes.com","timesofindia.indiatimes.com","deccanchronicle.com"]): return "News"
    return "Other"

def make_id(url, date, name):
    return "FS-"+hashlib.sha1((url+"|"+date+"|"+name).encode()).hexdigest()[:10].upper()

def load_csv(path):
    if not path.exists(): return []
    with open(path,encoding="utf-8") as f: return list(csv.DictReader(f))

rows=load_csv(CSV_PATH)
review=load_csv(REVIEW_PATH)
existing={(r.get("source_url",""),r.get("date_reported","")) for r in rows}

for q in QUERIES:
    feed=feedparser.parse("https://news.google.com/rss/search?q="+requests.utils.quote(q)+"&hl=en-IN&gl=IN&ceid=IN:en")
    for e in feed.entries[:15]:
        url=e.get("link","")
        title=clean(e.get("title",""))
        pub=e.get("published","")
        text=article(url)
        combined=title+" "+text
        cats=categories(combined); acts=actions(combined)
        st=source_type(url)
        if not text or not cats:
            continue
        name=clean(title.split(" - ")[0])
        date=(e.get("published_parsed") and datetime(*e.published_parsed[:6]).date().isoformat()) or datetime.now().date().isoformat()
        evidence=clean(text[:700])
        verified = "Official source" if st=="Official" else ("News report — corroboration recommended")
        row={
            "incident_id":make_id(url,date,name),"restaurant_name":name,"location":"","city":"","state":"",
            "date_reported":date,"date_inspection":"","authority":"","finding":title,
            "finding_categories":"; ".join(cats),"action_taken":"; ".join(acts),
            "samples_collected":"","closure_status":"","verification_status":verified,
            "source_name":e.get("source",{}).get("title","Google News source"),
            "source_type":st,"source_url":url,"evidence_excerpt":evidence,
            "last_updated":datetime.now().date().isoformat()
        }
        key=(url,date)
        if key in existing: continue
        # Conservative publication rule: official OR explicit action + finding.
        if st=="Official" or (acts and cats):
            rows.append(row); existing.add(key)
        else:
            review.append(row)

# Remove seed rows from public dataset once real collection starts.
rows=[r for r in rows if r.get("verification_status")!="Seed / not for publication"]

with open(CSV_PATH,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
with open(REVIEW_PATH,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(review)
PUBLIC.mkdir(exist_ok=True)
JSON_PATH.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Published {len(rows)} records; review queue {len(review)}.")
