import requests
from bs4 import BeautifulSoup

try:
    response = requests.get("http://nmf.int.westgroup.com/switchmap/6500-ios/index.html")
    soup = BeautifulSoup(response.text, 'lxml')
    print([li.a.text.split('.')[0] for li in soup.findAll('li')])
except:
    print("Could not get servers from URL, please check that the site is up and has not been moved")
    exit(1)


