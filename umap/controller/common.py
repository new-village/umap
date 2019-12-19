import re
import pymongo
from requests_html import HTMLSession

session = HTMLSession()


def load_page(_url, _check_class):
    try:
        page = session.get(_url).html
        if len(page.find(_check_class)) == 0:
            page = None
    except Exception:
        page = None

    return page


def int_fmt(_target, _reg):
    val = check_format(_target, _reg)
    val = int(re.sub(",", "", val)) if val is not None else 0

    return val


def float_fmt(_target, _reg):
    val = check_format(_target, _reg)
    val = float(re.sub(",", "", val)) if val is not None else 0

    return val


def str_fmt(_target, _reg):
    val = check_format(_target, _reg)
    val = str(val) if val is not None else ""

    return val


def check_format(_target, _reg):
    # check target variables
    fmt = re.compile(_reg)
    if _target is not None and fmt.search(_target):
        val = fmt.findall(_target)[0]
    else:
        val = None

    return val


def to_place_name(place_id):
    master = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京",
              "08": "京都", "09": "阪神", "10": "小倉"}
    place_name = master[place_id]
    return place_name


def to_course_full(abbr):
    master = {"ダ": "ダート", "障": "障害", "芝": "芝"}
    course_full = master[abbr] if abbr != '' else 0
    return course_full


def vault():
    """ Connect Vault Database on local MongoDB
    """
    client = pymongo.MongoClient("localhost", 27017)
    return client.vault