import re
from bs4 import BeautifulSoup as bs
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def load(_url, _selector=None):
    """ Function of HTML Collection (Supported Javascript）
        _url: Target URL
        _selector: Validation Class
        * If there is no _selector in HTML, Fuction return None Object
    """
    # Launch Chrome in Headless Mode 
    op = ChromeOptions()
    op.add_argument("--headless")
    op.add_argument('--disable-gpu')
    op.add_argument('--blink-settings=imagesEnabled=false')
    driver = Chrome(options=op)

    # Collect Target Page HTML
    try:
        driver.get(_url)
        if _selector is not None:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, _selector)))
        page = bs(driver.page_source, "lxml")
        if not page.select("."+_selector):
            page = None
    except Exception:
        page = None
    finally:
        driver.close()
        driver.quit()

    return page


def fmt(_target, _reg, _type="str"):
    """ Function of Regex Extraction and Type Casting
        _target: Target Value
        _reg: Regex
        _type: Cast Type
    """
    # Extract Target Value
    val = check_format(_target, _reg)

    # Cast Value
    if _type == "int":
        val = int(re.sub(",", "", val)) if val is not None else 0
    elif _type == "float":
        val = float(re.sub(",", "", val)) if val is not None else 0
    else:
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


def to_place(place_id):
    master = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京",
              "08": "京都", "09": "阪神", "10": "小倉"}
    place_name = master[place_id]
    return place_name


def to_course(abbr):
    master = {"ダ": "ダート", "障": "障害", "芝": "芝"}
    course_full = master[abbr] if abbr != '' else 0
    return course_full
