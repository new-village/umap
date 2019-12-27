import re
import time
from datetime import datetime

from app import mongo
from controller import load, fmt, to_course, to_place

def collect(_rid):
    # Get html
    base_url = "https://racev3.netkeiba.com/race/shutuba.html?race_id={rid}&rf=race_list"
    if re.match(r"^\d{12}$", _rid):
        url = base_url.replace("{rid}", _rid)
        page = load(url, "transition-color")
    else:
        return {"status": "ERROR", "message": "Invalid URL parameter: " + _rid}

    # Parse race info
    if page is not None:
        race = parse_nk_race(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    # Insert or Update race info
    if "_id" in race:
        mongo.db.races.update({"_id": race["_id"]}, race, upsert=True)
    else:
        return {"status": "ERROR", "message": "There is no id in page: " + race["_id"]}

    return {"status": "SUCCESS", "message": str(race)}


def bulk_collect(_year, _month):
    url = "https://keiba.yahoo.co.jp/schedule/list/" + _year + "/?month=" + _month
    page = load(url, "layoutCol2M")

    # Parse race info
    if page is not None:
        race_ids = parse_spn_rids(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    if len(race_ids) > 0:
        for rid in race_ids:
            collect(rid)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}

    return {"status": "SUCCESS", "message": "Start bulk collection process"}


def parse_nk_race(_page):
    """取得したレース出走情報のHTMLから辞書を作成
    netkeiba.comのレースページから情報をパースしてdict形式で返すファンクション
    """
    race = {}

    # RACE ID
    tmp = _page.select_one("ul.fc > li.Active > a")
    race["_id"] = fmt(tmp.get("href"), r"(\d+)")
    # ROUND
    race["round"] = fmt(tmp.text, r"\d+", "int")
    # TITLE
    tmp = _page.select_one("div.RaceName")
    race["title"] = fmt(tmp.text, r"[^\x01-\x2f\x3a-\x7E]+")
    # GRADE
    title = _page.title.text
    race["grade"] = fmt(title, r"(G\d{1})")
    # TRACK
    rd01 = _page.select_one("div.RaceData01").text
    race["track"] = to_course_full(fmt(rd01, r"芝|ダ|障"))
    # DISTANCE
    race["distance"] = fmt(rd01, r"\d{4}", "int")
    # WEATHER
    race["weather"] = fmt(rd01, r"晴|曇|小雨|雨|小雪|雪")
    # GOING
    race["going"] = fmt(rd01, r"良|稍重|重|不良")
    # RACE DATE
    dt = fmt(title, r"\d{4}年\d{1,2}月\d{1,2}日")
    tmp = fmt(rd01, r"\d{2}:\d{2}")
    tm = tmp if tmp != "" else "0:00"
    race["date"] = datetime.strptime(dt + " " + tm, "%Y年%m月%d日 %H:%M")
    # PLACE NAME
    race["place"] = to_place_name(race["_id"][4:6])
    # HEAD COUNT
    rd02 = _page.select("div.RaceData02 > span")
    race["count"] = fmt(rd02[7].text, r"([0-9]+)頭", "int")
    # MAX PRIZE
    race["max_prize"] = fmt(rd02[8].text, r"\d+")

    return race


def parse_spn_rids(_page):
    """取得したレース出走情報のHTMLからレースIDの配列を作成
    Yahoo競馬のレースページから情報をパースしてlist形式で返すファンクション
    """
    race_ids = []
    for link in _page.select_one("table.scheLs > tbody").find_all("a"):
        tmp = fmt(link.get("href"), r"/race/list/(\d+)/")
        if tmp != "":
            hold = ["20" + tmp + str(i + 1).zfill(2) for i in range(12)]
            race_ids.extend(hold)

    return race_ids
