import re
import time
from datetime import datetime

from app import mongo
from controller import load, fmt, convert, extract_table


def collect(_rid):
    # Get Result html
    url = "https://racev3.netkeiba.com/race/result.html?race_id=" + _rid + "&rf=race_list"
    page = load(url, "ResultTableWrap")
    
    # Get Entry html
    if page is None:
        url = "https://racev3.netkeiba.com/race/shutuba.html?race_id=" + _rid + "&rf=race_submenu"
        page = load(url, "tablesorter")

    # Parse race info
    if page is not None:
        race = upsert_race(page)
    else:
        return {"status": "ERROR", "message": "There is no page: " + _rid}

    return {"status": "SUCCESS", "message": _rid}


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


def upsert_race(_page):
    """ 取得したレース情報をデータベースに書き込むファンクション
    """
    # RACE ID
    race = {"_id": parse_nk_rid(_page)}
    # ROUND, TITLE, GRADE, PLACE, DATE_STR
    race.update(parse_nk_title(_page))
    # TRACK, DISTANCE, WEATHER, GOING, TIME 
    race.update(parse_nk_rd1(_page))
    # COUNT, PRIZE
    race.update(parse_nk_rd2(_page))
    # RACE DATE
    dttm = race["date_str"] + " " + race["time"]
    race["date"] = datetime.strptime(dttm, "%Y-%m-%d %H:%M")
    # MAX PRIZE
    race["max_prize"] = race["prize"][0]
    # ENTRY
    race["entry"] = collect_results(_page)
    # DELETE KEY
    del race["prize"], race["time"]
    # Upsert race
    mongo.db.races.update({"_id": race["_id"]}, race, upsert=True)

    return race


def collect_results(_page):
    """ 取得した出走情報をリスト型で纏めて返すファンクション
    """
    # RACE ID
    rid = parse_nk_rid(_page)
    # ODDS
    odds = collect_odds(rid)
    # PARENTS
    parents = collect_parents(rid)
    # PRIZE
    prize = parse_nk_rd2(_page)["prize"]
    # RESULT TABLE
    selector = "table#All_Result_Table > tbody > tr"
    table = extract_table(_page, selector)

    # RESULT TABLE
    results = []
    for line in table:
        # RESULTS
        result = parse_nk_result(line)
        # PLACE ODDS
        if result["horse_name"] in odds:
            result.update(odds[result["horse_name"]])
        # PRIZE
        if result["rank"] <= len(prize) and result["rank"] != 0:
            result["prize"] = prize[result["rank"] - 1]
        else:
            result["prize"] = 0
        # PARENTS
        if result["horse_name"] in parents:
            result.update(parents[result["horse_name"]])
        # ADD ENTRY
        results.append(result)
    
    return results


def collect_odds(_rid):
    # Get Result html
    url = "https://racev3.netkeiba.com/odds/index.html?type=b1&race_id=" + _rid + "&rf=shutuba_submenu"
    page = load(url, "Odds")

    # Parse Race Info
    selector = "div#odds_fuku_block > table > tbody > tr"
    table = extract_table(page, selector)

    # Parse Odds
    odds = {}
    for fuku in table[1:]:
        # HORSE NAME
        horse = fmt(fuku.select_one("td.Horse_Name").text, r"[^\x01-\x7E]+")
        # PLACE RATE
        rate = fuku.select_one("td.Odds").text
        min_odds = fmt(rate, r"(\d+.\d{1}) - \d+.\d{1}", "float")
        max_odds = fmt(rate, r"\d+.\d{1} - (\d+.\d{1})", "float")
        odds[horse] = {"place_odds_min": min_odds, "place_odds_max": max_odds}

    return odds


def collect_parents(_rid):
    # Get Result html
    url = "https://racev3.netkeiba.com/race/shutuba_past.html?race_id=" + _rid + "&rf=shutuba_submenu"
    page = load(url, "Shutuba_Past5_Table")

    # Parse Race Info
    selector = "div.Shutuba_HorseList > table > tbody > tr"
    table = extract_table(page, selector)

    # Parse Odds
    parents = {}
    for line in table[1:]:
        # HORSE NAME
        horse = fmt(line.select_one("div.Horse02").text, r"[^\x01-\x7E]+")
        # PARENT NAME
        father = fmt(line.select_one("div.Horse01").text, r".+")
        mother = fmt(line.select_one("div.Horse03").text, r".+")
        parents[horse] = {"father_name": father, "mother_name": mother}

    return parents


def parse_nk_rid(_page):
    """ Get Race ID by header tags in NetKeiba Page
    """
    # RACE ID
    url = _page.find("link", {"rel": "canonical"})["href"]
    rid = fmt(url, r"(\d{12})")
    return rid


def parse_nk_title(_page):
    """ Get Race Title by header tags in NetKeiba Page
    """
    t = _page.title.text
    # TITLE
    title = {"title": fmt(t, r"([^\x01-\x7E]+)")}
    # GRADE
    title["grade"] = fmt(t, r"\((J?G\d{1})\)")
    # DATE
    dt = fmt(t, r"\d{4}年\d{1,2}月\d{1,2}日", "date")
    title["date_str"] = dt.strftime("%Y-%m-%d")
    # PLACE
    title["place"] = fmt(t, r" ([一-龥]+)\d{1,2}R")
    # ROUND
    title["round"] = fmt(t, r"(\d{1,2})R", "int")
    return title


def parse_nk_rd1(_page):
    """ Get Race Data by Race Overview in NetKeiba Page
    """
    t01 = _page.select_one("div.RaceData01")
    if t01 is not None:
        # TRACK
        track = fmt(t01.text, r"芝|ダ|障")
        abbr = {"芝": "芝", "ダ": "ダート", "障": "障害"}
        rd = {"track": convert(track, abbr)}

        # DISTANCE
        rd["distance"] = fmt(t01.text, r"\d{4}", "int")

        # WHATHER
        rd["weather"] = fmt(t01.text, r"晴|曇|小雨|雨|小雪|雪")

        # GOING
        going = fmt(t01.text, r"良|稍|稍重|重|不良|不")
        abbr = {"稍": "稍重", "不": "不良"}
        rd["going"] = convert(going, abbr)

        # TIME
        tm = fmt(t01.text, r"\d{2}:\d{2}")
        rd["time"] = tm if tm != "" else "0:00"

    return rd


def parse_nk_rd2(_page):
    """ Get Race Data by Race Overview in NetKeiba Page
    """
    rd = {}
    t02 = _page.select("div.RaceData02 > span")
    # HEAD COUNT
    rd["count"] = fmt(t02[7].text, r"([0-9]+)頭", "int")

    # PRIZE
    prize = []
    for pz in t02[8].text.split(","):
        prize.append(fmt(pz, r"\d+", "int") * 10000)
    rd["prize"] = prize

    return rd


def parse_nk_result(_line):
    """ Parse Race Result from line of result table
    """
    td = _line.find_all("td")
    result = {}
    # RANK
    result["rank"] = fmt(td[0].text, r"\d+", "int")
    # HORSE NUMBER
    result["horse_number"] = fmt(td[2].text, r"\d+", "int")
    # BRACKET
    result["bracket"] = fmt(td[1].text, r"\d+", "int")
    # HORSE ID
    if td[3].a is not None:
        result["horse_id"] = fmt(td[3].a.get("href"), r"\d+")
    # HORSE NAME
    result["horse_name"] = fmt(td[3].text, r"[^\x01-\x7E]+")
    # SEX
    sex = fmt(td[4].text, r"[牡牝騸セ]")
    abbr = {"セ": "騸"}
    result["sex"] = convert(sex, abbr)
    # AGE
    result["age"] = fmt(td[4].text, r"\d{1,2}", "int")
    # BURDEN
    result["burden"] = fmt(td[5].text, r"\d{1,2}\.\d{1}", "float")
    # JOCKEY ID
    if td[6].a is not None:
        result["jockey_id"] = fmt(td[6].a.get("href"), r"\d+")
    # JOCKEY NAME
    result["jockey_name"] = fmt(td[6].text, r"[ぁ-んァ-ンー一-龥Ａ-Ｚ]+")
    # TIME
    min = fmt(td[7].text, r"(\d{1}):\d{1,2}\.\d{1}", "float") * 60
    sec = fmt(td[7].text, r"\d{1}:(\d{1,2}\.\d{1})", "float")
    result["time"] = min + sec
    # TRAINER ID
    if td[13].a is not None:
        result["trainer_id"] = fmt(td[13].a.get("href"), r"\d+")
    # TRAINER NAME
    if td[13].a is not None:
        result["trainer_name"] = fmt(td[13].a.text, r"[ぁ-んァ-ンー一-龥]+")
    # WEIGHT
    result["weight"] = fmt(td[14].text, r"(\d+)\(?[+-]?\d*\)?", "int")
    # WEIGHT DIFF
    result["weight_diff"] = fmt(td[14].text, r"\d+\(([+-]?\d+)\)", "int")
    # WIN ODDS
    result["win_odds"] = fmt(td[10].text, r"\d{1,3}\.\d{1}", "float")

    return result


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
