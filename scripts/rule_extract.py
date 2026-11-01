"""Rule-based extraction of establishment records from a news article (no AI).

Indian food-safety reports usually name establishments in a list after a trigger phrase:
  "The establishments whose licences were suspended include Hotel X at Tolichowki, Y Restaurant at
   Santosh Nagar ... and Z at Rethibowli."
  "... took action against M/s A, M/s B Pvt Ltd (Brand) and M/s C."
  "A, B and C in Kamareddy district; and D and E in Nizamabad district."
This module finds those list sentences, splits them into establishments, attaches the area or district,
the action that sentence describes, and any sentence elsewhere in the article that gives findings for
that establishment. City and state come from a place list; the authority from known agency names.

It returns the same fields as the AI extractor, and extract_records.py applies the same checks to both.
Rules miss establishments that are named in free prose, and can mistake an area for a name; records it
produces are labelled as rule-based extractions.
"""
import re
from datetime import date, timedelta

# ---- places: city or district -> state ------------------------------------------------------------
_PLACES = {  # multi-word names use "_" ; words that are also common names or dishes are left out (Anand, Udupi, Puri, Mandi...)
    "Telangana": "Hyderabad Secunderabad Cyberabad Warangal Hanamkonda Karimnagar Nizamabad Kamareddy Medak Sangareddy Siddipet "
                 "Nalgonda Suryapet Khammam Mahabubnagar Mahbubnagar Adilabad Mancherial Jagtial Peddapalli Ramagundam "
                 "Yadadri_Bhuvanagiri Bhongir Vikarabad Wanaparthy Nagarkurnool Jogulamba_Gadwal Kothagudem Jangaon "
                 "Mahabubabad Narayanpet Rajanna_Sircilla Medchal Rangareddy Ranga_Reddy Choutuppal Narketpally "
                 "Nakrekal Miryalaguda Kodad",
    "Andhra Pradesh": "Visakhapatnam Vizag Vijayawada Guntur Nellore Kurnool Tirupati Kakinada Rajahmundry Rajamahendravaram "
                      "Anantapur Anantapuramu Kadapa Eluru Ongole Srikakulam Vizianagaram Machilipatnam Chittoor Amaravati Tenali",
    "Maharashtra": "Mumbai Thane Navi_Mumbai Pune Pimpri_Chinchwad Nagpur Nashik Aurangabad Chhatrapati_Sambhajinagar Sambhajinagar "
                   "Solapur Kolhapur Sangli Satara Ahmednagar Ahilyanagar Jalgaon Dhule Nandurbar Akola Amravati Latur Nanded Parbhani "
                   "Hingoli Beed Osmanabad Dharashiv Jalna Buldhana Washim Yavatmal Wardha Chandrapur Gadchiroli Gondia "
                   "Bhandara Ratnagiri Sindhudurg Raigad Palghar Dombivli Vasai Virar Bhiwandi Ulhasnagar Panvel "
                   "Baramati Shirur Indapur Daund Lonavala Mira_Bhayandar",
    "Karnataka": "Bengaluru Bangalore Mysuru Mysore Mangaluru Mangalore Hubballi Hubli Dharwad Belagavi Belgaum Kalaburagi "
                 "Gulbarga Ballari Bellary Shivamogga Shimoga Tumakuru Tumkur Davanagere Mandya Bidar Vijayapura "
                 "Raichur Chitradurga Kolar Chikkamagaluru Devanahalli",
    "Tamil Nadu": "Chennai Coimbatore Madurai Tiruchirappalli Trichy Salem Tirunelveli Tiruppur Erode Vellore Thoothukudi "
                  "Tuticorin Thanjavur Dindigul Kanchipuram Cuddalore Nagercoil Kanniyakumari Karur Hosur Namakkal Peravurani",
    "Kerala": "Thiruvananthapuram Trivandrum Kochi Ernakulam Kozhikode Calicut Thrissur Kollam Kannur Alappuzha Palakkad "
              "Malappuram Kottayam Kasaragod Pathanamthitta Idukki Wayanad",
    "West Bengal": "Kolkata Calcutta Howrah Salt_Lake Bidhannagar New_Town Durgapur Asansol Siliguri Kharagpur "
                   "Bardhaman Burdwan Haldia Malda",
    "Delhi": "Delhi New_Delhi Aerocity Dwarka Rohini Raghubir_Nagar Chandni_Chowk Connaught_Place",
    "Uttar Pradesh": "Lucknow Kanpur Noida Greater_Noida Ghaziabad Agra Varanasi Prayagraj Allahabad Meerut Bareilly Aligarh "
                     "Moradabad Gorakhpur Jhansi Mathura Amroha Saharanpur Firozabad Ayodhya Muzaffarnagar Shahjahanpur",
    "Gujarat": "Ahmedabad Surat Vadodara Baroda Rajkot Gandhinagar Bhavnagar Jamnagar Junagadh Bharuch Navsari Morbi",
    "Punjab": "Ludhiana Amritsar Jalandhar Patiala Bathinda Mohali Pathankot Hoshiarpur Ferozepur Samana Chheharta",
    "Haryana": "Gurugram Gurgaon Faridabad Panipat Ambala Karnal Rohtak Hisar Sonipat Panchkula Yamunanagar",
    "Rajasthan": "Jaipur Jodhpur Udaipur Ajmer Bikaner Alwar Bhilwara Sikar",
    "Madhya Pradesh": "Bhopal Indore Gwalior Jabalpur Ujjain Rewa Satna",
    "Bihar": "Patna Bhagalpur Muzaffarpur Darbhanga Purnia",
    "Odisha": "Bhubaneswar Cuttack Rourkela Berhampur Sambalpur Balasore",
    "Uttarakhand": "Dehradun Haridwar Rishikesh Haldwani Roorkee Nainital Mussoorie",
    "Himachal Pradesh": "Shimla Dharamshala Solan Sirmaur Kullu Manali",
    "Jammu and Kashmir": "Srinagar Jammu Anantnag Baramulla Ganderbal",
    "Goa": "Panaji Margao Mapusa",
    "Assam": "Guwahati Dibrugarh Silchar Jorhat",
    "Chhattisgarh": "Raipur Bhilai Durg Korba",
    "Jharkhand": "Ranchi Jamshedpur Dhanbad Bokaro",
    "Chandigarh": "Chandigarh",
}
PLACE_STATE = {p.replace("_", " ").lower(): st for st, names in _PLACES.items() for p in names.split()}
_PLACE_RE = re.compile(r"\b(" + "|".join(sorted((re.escape(p) for p in PLACE_STATE), key=len, reverse=True)) + r")\b", re.I)
# Localities inside big cities: never an establishment name, never a city.
AREAS = set(a.lower() for a in """Gachibowli Madhapur Kondapur Hitech_City HITEC_City Banjara_Hills Jubilee_Hills Ameerpet Kukatpally
Charminar Tolichowki Begumpet Somajiguda Masab_Tank Mehdipatnam Dilsukhnagar Malakpet Abids Koti Nampally Kothapet Uppal
Miyapur Manikonda Raidurg Hafeezpet Chikkadpally Vengal_Rao_Nagar Santosh_Nagar Shahalibanda Nayapul Gudimalkapur Rethibowli
Bazarghat Safilguda Begum_Bazar Gopanpally LB_Nagar Kompally Bachupally Andheri Bandra Borivali Parel Lower_Parel Colaba Dadar
Malad Kandivali Powai Vile_Parle Santacruz Kurla Goregaon Juhu Worli Chembur Ghatkopar Mulund Bhandup Marol Kalina Girgaon
Charni_Road Marine_Lines Fort Churchgate Byculla Matunga Sion Dharavi Mahim Khar Kalbadevi Shivajinagar Kothrud Hadapsar
Viman_Nagar Koregaon_Park Baner Wakad Hinjewadi Indiranagar Koramangala Whitefield Jayanagar""".split()
            for a in [a.replace("_", " ")])
_CANON = {"bangalore": "Bengaluru", "mysore": "Mysuru", "mangalore": "Mangaluru", "calcutta": "Kolkata", "gurgaon": "Gurugram",
          "baroda": "Vadodara", "trivandrum": "Thiruvananthapuram", "calicut": "Kozhikode", "vizag": "Visakhapatnam",
          "trichy": "Tiruchirappalli", "aurangabad": "Chhatrapati Sambhajinagar", "sambhajinagar": "Chhatrapati Sambhajinagar",
          "mahbubnagar": "Mahabubnagar", "hubli": "Hubballi", "belgaum": "Belagavi", "gulbarga": "Kalaburagi", "shimoga": "Shivamogga",
          "tumkur": "Tumakuru", "bellary": "Ballari", "tuticorin": "Thoothukudi", "allahabad": "Prayagraj", "cyberabad": "Hyderabad",
          "bidhannagar": "Salt Lake", "burdwan": "Bardhaman", "ranga reddy": "Rangareddy"}

def place_of(s):
    """(city, state) for the first known place in s, else ("", "")."""
    m = _PLACE_RE.search(s or "")
    if not m: return "", ""
    key = m.group(1).lower()
    city = _CANON.get(key, " ".join(w.capitalize() for w in m.group(1).split()))
    return city, PLACE_STATE[key]

def is_area(s):
    s = re.sub(r"\s+", " ", (s or "").strip().lower())
    return s in AREAS or bool(AREA_SUFFIX.search(s.split()[-1] if s else ""))

# ---- vocabulary -----------------------------------------------------------------------------------
EST_WORDS = set("""restaurant restaurants hotel hotels dhaba cafe café cafeteria bakery bakers sweets sweet mart mess kitchen bar
biryani caterer caterers catering dairy foods food bhavan bhawan darshini canteen juice court grill lounge tiffins tiffin kabab
kebab kababs pizza momos patisserie confectionery confectioners hospitality lodge inn plaza store stores palace resorts resort
grand family house centre center corner point dosa idli chai tea bhojanalay hotelier pvt ltd llp enterprises traders outlet
outlets express delight paradise treat spice spices mandi bistro diner eatery eateries pub brewery club kitchens chinese
veg biriyani shawarma pastry cakes chicken mutton fish meat mart dhabha udupi udipi annapurna""".split())
AREA_SUFFIX = re.compile(r"(nagar|colony|road|marg|pet|peth|pally|palli|guda|bagh|gunj|ganj|chowk|bazar|bazaar|pura|puram|"
                         r"halli|wadi|wada|abad|kunta|basti|lane|street|circle|cross|layout|sector|phase|east|west|north|south|city|hills|tank|"
                         r"gardens|park|chowrasta|bowli|gate)$", re.I)
NOT_NAME = re.compile(r"\b(food safety|officer|officers|department|authority|commissioner|commissionerate|corporation|police|"
                      r"team|teams|district|government|minister|ministry|municipal|licen[cs]e|licen[cs]es|fssai|tg safe|fda|"
                      r"administration|inspection|inspections|notice|notices|samples?|violations?|establishments?|act|"
                      r"regulations?|standards|section|schedule|zone|zones|division|state|india|press note|statement|"
                      r"enforcement|drive|campaign|operations?)\b", re.I)
SMALL = {"and", "of", "the", "by", "&", "at", "on", "for", "de", "da", "di", "e", "n", "-", "'s"}

ACTION_RULES = [  # (pattern, action label), checked in order against the text before a list
    (r"show[- ]?cause", "Show-cause notice issued"),
    (r"improvement notice", "Improvement notice issued"),
    (r"cancel", "Licence cancelled"),
    (r"suspend", "FSSAI licence suspended"),
    (r"\bseal", "Premises sealed"),
    (r"stop (business )?operations|ordered to (shut|close)|shut down|closed down|closure", "Ordered to stop operations"),
    (r"\bfined\b|\bfines? of\b|penalt", "Penalty imposed"),  # not "Fine Dine"
    (r"seiz|destroy", "Food seized / destroyed"),
    (r"action against|took action|legal action|prosecution", "Action taken (details not itemised)"),
]
ARTICLE_ACTION = re.compile(r"suspend|cancel|show[- ]?cause|improvement notice|seal|shut|closed|stop (business )?operations|"
                            r"seiz|destroy|penalt|\bfined\b|prosecut|action against|took action", re.I)
# A list sentence must be about food businesses; this filters page furniture such as "Bennett, Coleman & Co. Ltd".
FOOD_CONTEXT = re.compile(r"licen[cs]e|establishment|eater|restaurant|outlet|hotel|shop|notice|fssai|food|dhaba|bakery|"
                          r"caterer|canteen|kitchen", re.I)
# "and" inside a name: "Golconda Hotel and Resorts", "Kitchen and Bar", "Food and Beverages Pvt Ltd"
JOINED = re.compile(r" and (?=(?:Bar|Resorts?|Restaurants?|Beverages|Confectioner(?:y|s)|Bakery|Bakers|Sweets|Caterers|Lounge|"
                    r"Grill|Kitchen|Cafe|Café|Lodge|Hotels?|Foods?|Suites|Spa|Banquets?|Restobar|Brewery|Hospitality)\b"
                    # ...only when that word ends the name ("and Hotel Glamour" is a second establishment)
                    r"(?!\s+(?!(?:Pvt|Ltd|LLP|Private|Limited|Co)\b)[A-Z0-9]))")
CORP = re.compile(r"\b(LLP|Ltd|Limited|Pvt|Private|Group of Hotels|Hospitality|Enterprises|Foodworks|Retails?)\b\.?", re.I)
TRIGGER = re.compile(r"(?:\binclud(?:e|es|ed|ing)\b|\bnamely\b|\blicen[cs]es? of\b|\bissued to\b|\bserved (?:on|to)\b|"
                     r"\baction against\b|\bagainst\b|\bwere\b|\bare\b|:)\s+", re.I)
FINDING = {  # category -> keywords (same names as update_tracker.CATEGORIES)
    "Pest infestation": ["cockroach", "rodent", "rat ", "rats", "rat-", "pest", "insect", "housefl", "flies", "lizard"],
    "Expired food": ["expired", "expiry"],
    "Spoiled / stale food": ["spoiled", "stale", "rotten", "decay"],
    "Microbial / fungal contamination": ["fungal", "fungus", "mould", "mold"],
    "Adulteration": ["adulterat"],
    "Unsafe additives / colours": ["synthetic colour", "artificial colour", "food colour", "banned colour", "colour"],
    "Labelling / date-marking": ["label"],
    "Temperature control": ["temperature", "refrigerat"],
    "Cross-contamination / segregation": ["segregat", "stored together", "raw and cooked", "veg and non-veg"],
    "Water / ice safety": ["water report", "water testing", "water quality"],
    "Poor hygiene / sanitation": ["unhygienic", "hygiene", "unclean", "dirty", "filth", "greasy"],
    "Waste / drainage": ["drain", "sewage", "waste", "stagnat"],
    "Food-handler hygiene": ["hairnet", "apron", "gloves", "food handler"],
    "Medical / training records": ["medical", "health record", "fostac", "training record"],
    "Licensing / registration": ["without a licence", "without licence", "without an fssai", "without fssai", "no licence"],
    "Storage / packaging": ["storage", "stored", "uncovered", "packag"],
}
MONTHS = {m: i for i, m in enumerate("january february march april may june july august september october november december".split(), 1)}
WEEKDAYS = "monday tuesday wednesday thursday friday saturday sunday".split()

# ---- text helpers ---------------------------------------------------------------------------------

def sentences(text):
    """Split into sentences without breaking inside brackets or after abbreviations like Pvt. / M/s. / Mr."""
    text = re.sub(r"\b(Pvt|Ltd|Mr|Mrs|Ms|Dr|Sri|Smt|St|No|Co|Inc|M/s|Nos|Jr|Sr|vs)\.", lambda m: m.group(1) + "․", text)
    out, buf, depth = [], [], 0
    for i, ch in enumerate(text):
        buf.append(ch)
        if ch in "([": depth += 1
        elif ch in ")]": depth = max(0, depth - 1)
        elif ch in ".!?" and depth == 0 and (i + 1 == len(text) or text[i + 1] == " "):
            nxt = text[i + 2:i + 3]
            if not nxt or nxt.isupper() or nxt.isdigit() or nxt in "\"'“‘":
                out.append("".join(buf).strip()); buf = []
    if buf: out.append("".join(buf).strip())
    return [s.replace("․", ".") for s in out if s]

def split_top(s, seps):
    """Split s on any of seps, ignoring separators inside brackets."""
    parts, buf, depth, i = [], "", 0, 0
    while i < len(s):
        ch = s[i]
        if ch in "([": depth += 1
        elif ch in ")]": depth = max(0, depth - 1)
        if depth == 0:
            sep = next((x for x in seps if s.startswith(x, i)), None)
            if sep:
                parts.append(buf); buf = ""; i += len(sep); continue
        buf += ch; i += 1
    parts.append(buf)
    return [p.strip(" ,;.") for p in parts if p.strip(" ,;.")]

def looks_like_name(name, in_list):
    if not name or len(name) < 3 or len(name) > 90: return False
    if not (name[0].isupper() or name[0].isdigit()): return False
    if NOT_NAME.search(name) or is_area(name) or "copyright" in name.lower(): return False
    words = [w for w in re.findall(r"[A-Za-z0-9'’&.-]+", re.sub(r"\(.*?\)", " ", name)) if w.lower() not in SMALL]
    if not words or len(words) > 9: return False
    caps = sum(1 for w in words if w[0].isupper() or w[0].isdigit())
    if caps / len(words) < 0.75: return False
    has_kw = any(w.lower().strip(".") in EST_WORDS for w in words)
    if not has_kw:
        if not in_list or len(words) > 6: return False
        if place_of(name)[0] and len(words) <= 2: return False      # a bare city/district
    return True

def clean_item(item):
    item = re.sub(r"^(?:and|the|also|including|include|includes|such as|namely|of)\s+", "", item.strip(), flags=re.I)
    item = re.sub(r"^M/s\.?\s*", "", item).strip()
    # cut trailing clauses: "X was suspended", "X for operating without ...", "X, among others"
    item = re.split(r"\s+(?:was|were|has|have|had|is|are|for|over|after|with|which|who|among others|following|due)\b", item)[0]
    item = re.sub(r"\s+(?:and|&)$", "", item.strip(" ,;:.\"'“”‘’"))
    return item.strip(" ,;:.\"'“”‘’")

def split_name_area(item):
    """'Hotel X at Tolichowki' -> ('Hotel X', 'Tolichowki', ''); 'Op LLP (Y) at Village in Nalgonda district' ->
    ('Y (Op LLP)', 'Village', 'Nalgonda'). Returns (name, locality, district_or_city)."""
    name, area, district = item, "", ""
    m = re.match(r"^(.*?)\s+(?:at|in|near|on)\s+([A-Z0-9][^()]*?)$", item)
    if m and not any(w.lower() in EST_WORDS for w in m.group(2).split()):  # "Mandi at 36 Arabian Kitchen" is one name
        name, area = m.group(1).strip(), m.group(2).strip()
    dm = re.match(r"^(.*?)\s+in\s+(.+?)$", area)                 # "Peddakaparthy in Nalgonda district"
    if dm: area, district = dm.group(1).strip(), dm.group(2).strip()
    district = re.sub(r"\s+(?:district|mandal|zone)$", "", district, flags=re.I).strip()
    area = re.sub(r"\s+(?:district|mandal|village|zone|area|locality)$", "", area, flags=re.I).strip()
    m = re.match(r"^(.+?)[’'](?:s)?\s+(.+)$", name)              # "Op LLP's Brand" / "Group of Hotels’ Brand"
    if m and CORP.search(m.group(1)): name = f"{m.group(2).strip()} ({m.group(1).strip()})"
    m = re.match(r"^(.+?)\s*\((.+)\)$", name)                     # "Op Pvt Ltd (Brand)" -> "Brand (Op Pvt Ltd)"
    if m and CORP.search(m.group(1)) and not CORP.search(m.group(2)) and not m.group(2).startswith("M/s"):
        name = f"{m.group(2).strip()} ({m.group(1).strip()})"
    return name.strip(), area, district

def action_for(prefix):
    p = prefix.lower()
    best, pos = "", -1
    for pat, label in ACTION_RULES:
        for m in re.finditer(pat, p):
            if m.start() > pos: best, pos = label, m.start()
    return best

def categories_of(s):
    t = s.lower()
    return [c for c, kws in FINDING.items() if any(k in t for k in kws)]

def authority_of(text, state):
    t = text
    if re.search(r"TG SAFE|Telangana Standards Authority", t): return "Telangana Standards Authority for Food and Essential Drugs (TG SAFE)"
    if re.search(r"Food and Drug Administration|\bFDA\b", t) and state == "Maharashtra": return "Food and Drug Administration (FDA), Maharashtra"
    if re.search(r"Kolkata Municipal Corporation|\bKMC\b", t): return "Kolkata Municipal Corporation (KMC)"
    if re.search(r"Greater Hyderabad Municipal Corporation|\bGHMC\b", t): return "Greater Hyderabad Municipal Corporation (GHMC)"
    if re.search(r"Commissionerate of Food Safety", t): return f"Commissionerate of Food Safety, {state}" if state else "Commissionerate of Food Safety"
    if re.search(r"Food Safety and Standards Authority of India|\bFSSAI\b", t) and re.search(r"FSSAI (?:has )?(?:suspend|cancel|issued|served|imposed)", t):
        return "Food Safety and Standards Authority of India (FSSAI)"
    if re.search(r"food safety (?:department|wing|officials|officers)", t, re.I): return f"Food Safety Department, {state}" if state else "Food Safety Department"
    return ""

def inspection_date(text, published):
    """Date the article gives for the inspections, resolved against the publication date; '' if none."""
    try: pub = date.fromisoformat(published)
    except (TypeError, ValueError): return ""
    def mk(mon, day):
        try:
            d = date(pub.year, MONTHS[mon.lower()], int(day))
            if d > pub: d = date(pub.year - 1, d.month, d.day)
            return d.isoformat() if (pub - d).days <= 60 else ""
        except (ValueError, KeyError): return ""
    ctx = [s for s in sentences(text) if re.search(r"inspect|raid|drive|visited|checks?\b", s, re.I)] or [text]
    for s in ctx:
        m = re.search(r"\(\s*(" + "|".join(MONTHS) + r")\s+(\d{1,2})\s*\)", s, re.I) or \
            re.search(r"\bon\s+(?:(?:" + "|".join(WEEKDAYS) + r"),?\s+)?(" + "|".join(MONTHS) + r")\s+(\d{1,2})\b", s, re.I)
        if m: return mk(m.group(1), m.group(2))
        m = re.search(r"\bon\s+(?:(?:" + "|".join(WEEKDAYS) + r"),?\s+)?(\d{1,2})\s+(" + "|".join(MONTHS) + r")\b", s, re.I)
        if m: return mk(m.group(2), m.group(1))
        m = re.search(r"\bon\s+(" + "|".join(WEEKDAYS) + r")\b", s, re.I)
        if m:
            back = (pub.weekday() - WEEKDAYS.index(m.group(1).lower())) % 7
            return (pub - timedelta(days=back)).isoformat()
    return ""

def main_place(text, headline=""):
    """The article's own city: its dateline ("MUMBAI:" / "- HYDERABAD"), else a place in the headline. Never guessed
    from elsewhere in the page, where sidebars and related stories mention other cities."""
    for m in re.finditer(r"\b([A-Z]{4,}(?: [A-Z]{3,})?)\b:?", text[:3000]):
        if m.group(1).lower() in PLACE_STATE: return place_of(m.group(1))
    m = re.search(r"(?:^|\s)([A-Z][a-z]+(?: [A-Z][a-z]+)?):\s", text[:3000])
    if m and place_of(m.group(1))[0]: return place_of(m.group(1))
    return place_of(headline)

# ---- main entry -----------------------------------------------------------------------------------

def _other_place(clause, city, location):
    """True if the clause puts the establishment somewhere else (another branch with the same name)."""
    if location and location.lower() in clause.lower(): return False
    for m in _PLACE_RE.finditer(clause):
        if place_of(m.group(1))[0].lower() != city.lower(): return True
    return False

LOCAL_AUTHORITY = re.compile(r"TG SAFE|Telangana Standards|Food and Drug Administration|\bFDA\b|Municipal Corporation|\bGHMC\b|"
                             r"\bKMC\b|Commissionerate|Food Safety Department|food safety (?:department|wing|officials|officers)", re.I)

def _top_level_count(s, token):
    depth, n = 0, 0
    for i, ch in enumerate(s):
        if ch in "([": depth += 1
        elif ch in ")]": depth = max(0, depth - 1)
        elif depth == 0 and s.startswith(token, i): n += 1
    return n

def extract(text, published, headline=""):
    """Records (dicts with the AI extractor's fields) for establishments the article names in action lists."""
    if not ARTICLE_ACTION.search(text): return []
    sents = sentences(text)
    art_city, art_state = main_place(text, headline)
    insp = inspection_date(text, published)
    found, seen, prev = [], set(), ""
    for s in sents:
        prev_s, prev = prev, s
        if not FOOD_CONTEXT.search(s) or "copyright" in s.lower(): continue
        # "These included A, B and C." takes its action from the sentence before it
        follows_on = re.match(r"(?:These|They|Those|The establishments|The outlets|Among them)\b", s)
        if not ARTICLE_ACTION.search(s) and "M/s" not in s and not follows_on: continue
        # the list starts after the last trigger phrase that is followed by a capitalised word
        starts = [m for m in TRIGGER.finditer(s) if re.match(r"(?:M/s\.?\s*)?[A-Z0-9]", s[m.end():])]
        if not starts: continue
        m = starts[-1] if "M/s" not in s else next((x for x in starts if "M/s" in s[x.end():x.end() + 6]), starts[-1])
        prefix, body = s[:m.start()], s[m.end():]
        action = action_for(prefix) or action_for(s) or (action_for(prev_s) if follows_on else "")
        if not action: continue
        body = re.split(r"\s+(?:were|was|have been|has been)\s+(?:suspended|issued|served|ordered|directed|sealed)|"
                        r",?\s+among others|\.\s*$", body)[0]
        s_city = place_of(prefix)
        groups = split_top(body, ["; and ", ";"])
        for g in groups:
            # a trailing "in X district" applies to every establishment in the group
            gm = re.search(r"\s+in\s+([A-Z][A-Za-z ]+?)\s+district\s*$", g)
            g_area = gm.group(1).strip() if gm else ""
            if gm: g = g[:gm.start()]
            ms = _top_level_count(g, "M/s") >= 2
            items = []  # (item text, locality shared by "A and B in Z")
            g = JOINED.sub(" \uE000 ", g)
            for chunk in (split_top(g, ["M/s"]) if ms else split_top(g, [", and ", ", "])):
                parts = [clean_item(p.replace(" \uE000 ", " and ")) for p in ([chunk] if ms else split_top(chunk, [" and ", " & "]))]
                # "Golconda Hotel and Resorts" split at "and": re-join a lone generic word to the item before it
                joined = []
                for p in parts:
                    words = [w for w in split_name_area(p)[0].split() if w.lower() not in SMALL]
                    if joined and len(words) == 1 and words[0].lower() in EST_WORDS:
                        joined[-1] += " and " + p
                    else:
                        joined.append(p)
                # "Little Village and Vivera Hotel in Nalgonda": the last part's locality covers the whole chunk
                shared = split_name_area(joined[-1])[1:] if joined else ("", "")
                items += [(p, shared) for p in joined]
            for item, shared in items:
                name, area, district = split_name_area(item)
                if not area and not district: area, district = shared
                if not looks_like_name(name, in_list=len(items) > 1 or ms): continue
                # city: from the locality or district given with this establishment, the group's district, the list
                # sentence, or the article's dateline/headline -- otherwise the record is dropped later
                city, state = ("", "")
                for src in (district, area, g_area):
                    if src and place_of(src)[0]:
                        city, state = place_of(src); break
                if not city and s_city[0]: city, state = s_city
                if not city:
                    # FSSAI's own (national) actions name firms anywhere in India; the dateline says nothing about them
                    if authority_of(text, art_state).startswith("Food Safety and Standards Authority of India"): continue
                    if "FSSAI" in prefix and not re.search(r"TG SAFE|FDA|Commission|Department|Corporation|officials", prefix): continue
                    if not LOCAL_AUTHORITY.search(text): continue  # national/unknown actor: the dateline says nothing
                    city, state = art_city, art_state
                    from_dateline = True
                else:
                    from_dateline = False
                if not city: continue
                location = area if area and area.lower() != city.lower() else ""
                key = (name.lower(), city.lower())
                if key in seen: continue
                seen.add(key)
                # findings: another sentence that mentions this establishment and describes what was found
                core = re.sub(r"\(.*?\)", "", name).strip()
                # (only the clause about this establishment, when one sentence covers several)
                own = [c for x in sents if x is not s and core.lower() in x.lower()
                       for c in re.split(r";|, while |, whereas |, and at ", x) if core.lower() in c.lower() and categories_of(c)
                       and not _other_place(c, city, location)]
                finding_src = own[0].strip(" ,") if own else ""
                cats = categories_of(finding_src) if finding_src else []
                finding = finding_src if finding_src else "Findings for this establishment were not itemised in the report."
                quote_src = finding_src or s
                found.append({
                    "restaurant_name": name, "location": location, "city": city, "state": state or "",
                    "date_inspection": insp, "authority": authority_of(text, state or art_state),
                    "finding": finding if len(finding) <= 400 else finding[:397].rsplit(" ", 1)[0] + "…",
                    "finding_categories": cats, "action_taken": action, "closure_status": "Not reported",
                    "evidence_quote": _quote_around(quote_src, core), "_dateline": from_dateline,
                })
    # If the article places its other establishments in named cities and the dateline city is not one of them, the
    # dateline is a news bureau ("HYDERABAD" for a Nalgonda story): drop records that only had the dateline to go on.
    explicit = {r["city"] for r in found if not r["_dateline"]}
    if explicit and art_city not in explicit:
        found = [r for r in found if not r["_dateline"]]
    for r in found: r.pop("_dateline")
    return found

def _quote_around(s, core, limit=40):
    """Up to `limit` words of s around the establishment's name, copied verbatim."""
    words = s.split()
    if len(words) <= limit: return s
    i = s.lower().find(core.lower())
    start_word = len(s[:i].split()) if i >= 0 else 0
    a = max(0, start_word - limit // 3)
    return " ".join(words[a:a + limit])
