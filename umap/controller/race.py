import re
import time
from datetime import datetime

from app import mongo
from controller import load, fmt, convert, extract_table


def collect(_rid):
    # Get Result html
    result_url = "https://racev3.netkeiba.com/race/result.html?race_id={RID}&rf=race_list"
    page = race_page_load(_rid, result_url, "ResultTableWrap")
    
    # Get Entry html
    entry_url = "https://racev3.netkeiba.com/race/shutuba.html?race_id={rid}&rf=race_submenu"
    if page is None:
        page = race_page_load(_rid, entry_url, "tablesorter")

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


def race_page_load(_rid, _url, _selector):
    # Validate Race ID
    if re.match(r"^\d{12}$", _rid):
        url = _url.replace("{RID}", _rid)
        page = load(url, _selector)
    else:
        page = None

    return page


def upsert_race(_page):
    """取得したレース出走情報のHTMLから辞書を作成
    netkeiba.comのレースページから情報をパースしてdict形式で返すファンクション
    """
    # RACE ID
    race = {"_id": parse_nk_rid(_page)}
    # Parse Elements
    elms = parse_nk_title(_page)
    elms.update(parse_nk_rd1(_page))
    elms.update(parse_nk_rd2(_page))
    # RACE DATE
    dttm = elms["date"] + " " + elms["time"]
    race["date"] = datetime.strptime(dttm, "%Y年%m月%d日 %H:%M")
    # RACE DATE (String)
    race["date_str"] = datetime.strftime(race["date"], "%Y-%m-%d")
    # Set Elements
    target = ["round", "title", "grade", "place", "track", "distance", "weather", "going", "count"]
    for s in target:
        race[s] = elms[s]
    # MAX PRIZE
    race["max_prize"] = elms["prize"][0]
    # ENTRY
    race["entry"] = collect_results(_page)
    # Upsert race
    mongo.db.races.update({"_id": race["_id"]}, race, upsert=True)

    return race


def collect_results(_page):
    # Get Place Odds
    odds = collect_odds(parse_nk_rid(_page))
    # Get Prize List
    prize = parse_nk_rd2(_page)["prize"]
    # Parse Race Info
    selector = "table#All_Result_Table > tbody > tr"
    table = extract_table(_page, selector)

    # Parse Result Table
    results = []
    for line in table:
        # RESULTS
        result = parse_nk_result(line)
        # PLACE ODDS
        if odds is not None:
            result.update(odds[result["horse_name"]])
        # PRIZE
        if result["rank"] <= len(prize) and result["rank"] != 0:
            result["prize"] = prize[result["rank"]-1]
        else:
            result["prize"] = 0
        # ADD ENTRY
        results.append(result)
    
    return results


def collect_odds(_rid):
    # Get Result html
    odds_url = "https://racev3.netkeiba.com/odds/index.html?type=b1&race_id={RID}&rf=shutuba_submenu"
    page = race_page_load(_rid, odds_url, "Odds")

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
    title["date"] = fmt(t, r"\d{4}年\d{1,2}月\d{1,2}日")
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
    result["jockey_id"] = fmt(td[6].a.get("href"), r"\d+")
    # JOCKEY NAME
    result["jockey_name"] = fmt(td[6].text, r"[ぁ-んァ-ンー一-龥Ａ-Ｚ]+")
    # TIME
    min = fmt(td[7].text, r"(\d{1}):\d{1,2}\.\d{1}", "float") * 60
    sec = fmt(td[7].text, r"\d{1}:(\d{1,2}\.\d{1})", "float")
    result["time"] = min + sec
    # TRAINER ID
    result["trainer_id"] = fmt(td[13].a.get("href"), r"\d+")
    # TRAINER NAME
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
