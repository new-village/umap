import re
import time
from datetime import datetime
from controller import int_fmt, load_page, str_fmt, to_course_full, to_place_name, vault


def collect(_rid):
    # Get html
    base_url = "https://racev3.netkeiba.com/race/shutuba.html?race_id={rid}&rf=race_list"
    if re.match(r"^\d{12}$", _rid):
        url = base_url.replace("{rid}", _rid)
        page = load_page(url, ".ShutubaTable")
    else:
        return {"status": "ERROR", "message": "Invalid URL parameter: " + _rid}

    # Parse race info
    if page is not None:
        race = parse_nk_race(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    if "_id" in race:
        print(race)
        # db = vault()
        # db.races.update({"_id": race["_id"]}, race, upsert=True)
    else:
        return {"status": "ERROR", "message": "There is no id in page: " + race}

    return {"status": "SUCCESS", "message": "Start race collection process for " + _rid}


def bulk_collect(_year, _month):
    url = "https://keiba.yahoo.co.jp/schedule/list/" + _year + "/?month=" + _month
    page = load_page(url, ".layoutCol2M")

    # Parse race info
    if page is not None:
        race_id = parse_spn_rid(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    if len(race_id) != 0:
        for rid in race_id:
            collect(rid)
            time.sleep(5)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    return {"status": "SUCCESS", "message": "Start bulk collection process"}


def parse_nk_race(_page):
    """取得したレース出走情報のHTMLから辞書を作成
    netkeiba.comのレースページから情報をパースしてjson形式で返すファンクション
    """
    race = {}

    # RACE ID
    row = list(_page.find("ul.fc > li.Active > a", first=True).links)[0]
    race["_id"] = str_fmt(row, r"\d+")
    # ROUND
    row = _page.find("span.RaceNum", first=True).text
    race["round"] = int_fmt(row, r"(\d{1,2})R")
    # TITLE
    race["title"] = _page.find("div.RaceName", first=True).text
    # GRADE
    row = _page.find("title", first=True).text
    race["grade"] = str_fmt(row, r"(G\d{1})")
    # TRACK
    row = _page.find("div.RaceData01", first=True).text
    abbr_track = str_fmt(row, r"芝|ダ|障")
    race["track"] = to_course_full(abbr_track)
    # DISTANCE
    row = _page.find("div.RaceData01", first=True).text
    race["distance"] = int_fmt(row, r"\d{4}")
    # WEATHER
    row = _page.find("div.RaceData01", first=True).text
    race["weather"] = str_fmt(row, r"晴|曇|小雨|雨|小雪|雪")
    # GOING
    row = _page.find("div.RaceData01", first=True).text
    race["going"] = str_fmt(row, r"良|稍重|重|不良")
    # RACE DATE
    row = _page.find("title", first=True).text
    dt = str_fmt(row, r"\d{4}年\d{1,2}月\d{1,2}日")
    row = _page.find("div.RaceData01", first=True).text
    tm = str_fmt(row, r"\d{2}:\d{2}")
    if tm == "":
        tm = "0:00"
    race["date"] = datetime.strptime(dt + " " + tm, "%Y年%m月%d日 %H:%M")
    # PLACE NAME
    place_code = race["_id"][4:6]
    race["place"] = to_place_name(place_code)
    # HEAD COUNT
    count = _page.find("div.RaceData02 > span")[7].text
    race["count"] = int_fmt(count, r"([0-9]+)頭")
    # MAX PRIZE
    prize = _page.find("div.RaceData02 > span")[8].text
    race["max_prize"] = int_fmt(prize, r"\d+")
    # ENTRY
    urls = [list(horse.links)[0] for horse in _page.find("td.Horse_Info")]
    horses = [{"horse_id": str_fmt(url, r"\d+")} for url in urls]
    race["entry"] = horses

    return race


def parse_spn_rid(_page):
    holds = []
    for td in _page.find("table.scheLs > tbody > tr > td"):
        links = str_fmt(str(td.links), r"/race/list/(\d+)/")
        holds.append(links)

    # Delete Blank Element
    holds = ["20" + hold for hold in holds if hold]

    # Generate race id from holds
    rid = []
    for hold in holds:
        rid.extend([hold + str(i + 1).zfill(2) for i in range(12)])

    return rid
