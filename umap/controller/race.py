import re
import time
from datetime import datetime

from app import mongo
from controller import load, fmt, to_course, to_place


def collect(_rid):
    # Get Result html
    result_url = "https://racev3.netkeiba.com/race/result.html?race_id={RID}&rf=race_list"
    page = race_collector(_rid, result_url, "ResultTableWrap")
    
    # Get Entry html
    entry_url = "https://racev3.netkeiba.com/race/shutuba.html?race_id={rid}&rf=race_submenu"
    if page is None:
        race_collector(_rid, entry_url, "tablesorter")

    # Parse race info
    if page is not None:
        race = parse_nk_race(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + url}


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


def race_collector(_rid, _url, _selector):
    # Validate Race Id
    if re.match(r"^\d{12}$", _rid):
        url = _url.replace("{RID}", _rid)
        page = load(url, _selector)
    else:
        page = None

    return page


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
    title = _page.title.text
    race["title"] = fmt(title, r"([^\x01-\x7E]+)")
    # GRADE
    race["grade"] = fmt(title, r"(G\d{1})")
    # TRACK
    rd01 = _page.select_one("div.RaceData01").text
    race["track"] = to_course(fmt(rd01, r"芝|ダ|障"))
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
    race["place"] = to_place(race["_id"][4:6])
    # HEAD COUNT
    rd02 = _page.select("div.RaceData02 > span")
    race["count"] = fmt(rd02[7].text, r"([0-9]+)頭", "int")
    # MAX PRIZE
    race["max_prize"] = fmt(rd02[8].text, r"\d+", "int") * 10000
    # ENTRY
    race["entry"] = parse_nk_result(_page)
    # UPSERT RACE
    mongo.db.races.update({"_id": race["_id"]}, race, upsert=True)

    return race


def parse_nk_result(_page):
    results = []

    # Get Place Odds
    rid = fmt(_page.select_one("ul.fc > li.Active > a").get("href"), r"(\d+)")
    odds = parse_nk_odds(rid)

    # Get Prize List
    rd02 = _page.select("div.RaceData02 > span")
    pz_list = [fmt(pz, r"\d+", "int") * 10000 for pz in rd02[8].text.split(",")]

    for line in _page.select("table#All_Result_Table > tbody > tr"):
        result = {}
        td = line.select("td")
        # RANK
        result["rank"] = fmt(td[0].text, r"\d+", "int")
        # HORSE NUMBER
        result["horse_number"] = fmt(td[2].text, r"\d+", "int")
        # BRACKET
        result["bracket"] = fmt(td[1].text, r"\d+", "int")
        # HORSE ID
        result["horse_id"] = fmt(td[3].a.get("href"), r"\d+")
        # HORSE NAME
        result["horse_name"] = fmt(td[3].text, r"[^\x01-\x7E]+")
        # SEX
        result["sex"] = fmt(td[4].text, r"[牡牝騸セ]")
        # AGE
        result["age"] = fmt(td[4].text, r"\d{1,2}", "int")
        # BURDEN
        result["burden"] = fmt(td[5].text, r"\d{1,2}\.\d{1}", "float")
        # JOCKEY ID
        result["jockey_id"] = fmt(td[6].a.get("href"), r"\d+")
        # JOCKEY NAME
        result["jockey_name"] = fmt(td[6].text, r"[^\x01-\x7E]+")
        # TIME
        min = fmt(td[7].text, r"(\d{1}):\d{1,2}\.\d{1}", "float") * 60
        sec = fmt(td[7].text, r"\d{1}:(\d{1,2}\.\d{1})", "float")
        result["time"] = min + sec
        # TRAINER ID
        result["trainer_id"] = fmt(td[13].a.get("href"), r"\d+")
        # TRAINER NAME
        result["trainer_name"] = fmt(td[13].a.text, r"[^\x01-\x7E]+")
        # WEIGHT
        result["weight"] = fmt(td[14].text, r"(\d+)\(?[+-]?\d*\)?", "int")
        # WEIGHT DIFF
        result["weight_diff"] = fmt(td[14].text, r"\d+\(([+-]?\d+)\)", "int")
        # WIN ODDS
        result["win_odds"] = fmt(td[10].text, r"\d{1,3}\.\d{1}", "float")
        # PLACE ODDS
        if odds is not None:
            result.update(odds[result["horse_name"]])
        # PRIZE
        if result["rank"] <= len(pz_list) and result["rank"] != 0:
            result["prize"] = pz_list[result["rank"]-1]
        else:
            result["prize"] = 0

        results.append(result)
    
    return results


def parse_nk_odds(_rid):
    odds = {}

   # Get html
    base_url = "https://racev3.netkeiba.com/odds/index.html?type=b1&race_id={rid}&rf=shutuba_submenu"
    odds_page = load(base_url.replace("{rid}", _rid), "Odds")

    # Parse race info
    if odds_page is not None:
        odds_table = odds_page.select("div#odds_fuku_block > table > tbody > tr")
    else:
        return None

    if len(odds_table) > 1:
        for fuku in odds_table[1:]:
            rate = {}
            # Odds
            horse = fmt(fuku.select_one("td.Horse_Name").text, r"[^\x01-\x7E]+")
            rate["place_odds_min"] = fmt(fuku.select_one("td.Odds").text, r"(\d+.\d{1}) - \d+.\d{1}", "float")
            rate["place_odds_max"] = fmt(fuku.select_one("td.Odds").text, r"\d+.\d{1} - (\d+.\d{1})", "float")
            odds[horse] = rate
    else:
        return None

    return odds


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
