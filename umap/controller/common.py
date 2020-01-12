import re
import time
from datetime import datetime
from bs4 import BeautifulSoup as bs
from requests import Session, HTTPError

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
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, _selector)))
        page = bs(driver.page_source, "lxml")
        if _selector is not None and not page.select("."+_selector):
            print("ERROR: " + _url)
            page = None
    except Exception:
        page = None
    
    # Close Connection
    driver.close()
    driver.quit()
    time.sleep(6)

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
    elif _type == "date":
        val = datetime.strptime(val, '%Y年%m月%d日')
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


def convert(string, table):
    """ The function convert string using table
        if you set string to '障' and table to {'障': '障害', '芝': '芝'},
        The function retrun '障害'.
    """
    if string in table:
        converted = table[string]
    else:
        converted = string
    return converted


def extract_table(_page, _selector):
    if _page is not None:
        table = _page.select(_selector)
        table = table if table is not None else None
    else:
        table = None
    return table
