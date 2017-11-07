#!/usr/bin/python
#-*-coding:utf-8-*-
import requests
import os
from bs4 import BeautifulSoup
import logging
from peewee import *
import datetime

db = SqliteDatabase('mm.db')

class Beauty(Model):
    title = CharField()
    path = CharField()
    cover = IntegerField()
    parent = IntegerField()
    update_at = DateTimeField()

    class Meta:
        database = db # This model uses the "people.db" database.
        db_table = 'girls_girl'


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename='./99mm.log', level=logging.INFO, format=FORMAT)
logger = logging.getLogger('crawlmm')

site = '99mm'
url = 'http://m.99mm.me/'
local_path = os.getenv('HOME', '/tmp')+'/static/'+site+'/'

class SoupX():
    def __init__(self, url, charset):
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': url}
        r = requests.get(url, headers=headers)

        r.encoding = charset
        html = r.text
        html = html.replace('<span>', '').replace('</span>', '').replace('<br/>', '')
        self.soup = BeautifulSoup(html, 'html.parser')

    def get(self):
        return self.soup

def get_local_filename(link, folder):
    local_filename = '-'.join(link.split('/')[-2:])
    f = folder+'/'+local_filename
    return f

def downloadImageFile(imgUrl, folder):
    #check if folder exist
    absolute_path = local_path+folder
    if not os.path.isdir(absolute_path):
        os.makedirs(absolute_path)
    local_filename = get_local_filename(imgUrl, folder) 
    fullpath = local_path+local_filename
    if os.path.isfile(fullpath):
        return local_filename
    logger.info("Download Image File=%s" % local_filename)
    r = requests.get(imgUrl, stream=True) # here we need to set stream = True parameter  
    with open(fullpath, 'wb') as f:  
        for chunk in r.iter_content(chunk_size=1024):  
            if chunk: # filter out keep-alive new chunks  
                f.write(chunk)  
                f.flush()  
        f.close()  
    return local_filename  

def get_all_images(uri, myl, myalias, folder):
    soup = SoupX(uri, 'utf-8').get()
    for link in soup.find_all("div", id="picbox"):
        img = link.img['src']
        alias = get_local_filename(img, folder)
        downloadImageFile(img, folder)
        myl.append(img)
        myalias.append(alias)
        next = link.a['href']
        if 'url' in next:
            next_url = uri.split('?')[0]+'?'+next.split('?')[1]
            get_all_images(next_url, myl, myalias, folder)
        else:
            return myl, myalias

def spider_web(page=1):
    soup = SoupX(url+'home/%d.html' %page, 'utf-8').get()
    stores = []
    for link in soup.find_all("ul", class_="piclist"):
        destpages = link.find_all("a")
        destpages = [d['href'] for d in destpages][0::2]
        
        imgs = link.find_all("img")
        for idx, img in enumerate(imgs):
            next = url+destpages[idx if idx < len(destpages) else 0]
            all_images = []
            all_alias = []  # local filename sets
            folder = img['alt']
            get_all_images(next, all_images, all_alias, folder)
            # download cover image
            cover_url = img['data-img']
            cover_local_file = downloadImageFile(cover_url, folder)
            info = {'title': img['alt'], 'cover': cover_local_file,
                    'locals': all_alias, 'source': site, 'update_at': datetime.datetime.now()}
            stores.append(info)
        return stores

def save_sqlitedb(stores):
    for idx, info in enumerate(stores):
        defaults = {'title': info['title'], 'update_at': info['update_at'], 'cover': 1, 'parent': 0}
        c, created = Beauty.get_or_create(path=site+'/'+info['cover'], defaults=defaults)
        for _index, a in enumerate(info['locals']):
            defaults = {'title': info['title']+str(_index+1), 'update_at': info['update_at'], 'cover': 0, 'parent': c.id}
            b, created = Beauty.get_or_create(path=site+'/'+a, defaults=defaults)

def start_spider(page=1):
    stores = spider_web(page)
    save_sqlitedb(stores)
    
if __name__ == '__main__':
    db.create_tables([Beauty], True)

    for i in range(1,2):
        start_spider(i)
    db.close()

