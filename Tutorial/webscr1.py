from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
from lxml import etree
import requests

url = r"https://www.gumtree.com/search?search_category=all&q=dishwasher"

with urlopen(url) as page:
    pageHtml = page.read()

pageSoup = bs(pageHtml, "html.parser")
pageSoupLxml = bs(pageHtml, "lxml")

#containers = pageSoupLxml.find_all('div', {"class":'listing-content'})
fullListCont = pageSoupLxml.find_all(
    'div', {"id":"srp-results"})
containers = fullListCont[0].find_all('li')
cont = containers[0]
item_title = cont.find('h2',{"class":"listing-title"}).text.strip()
item_price = cont.find(
    "div",{"class":"listing-price-posted-container"}).find(
        "strong",{"class":"h3-responsive"}).text.strip()

print(cont.h2.text)
print(cont.find_all('span'))
