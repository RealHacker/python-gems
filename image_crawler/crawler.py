# This is a asynchronous image crawler written in python
from tornado.httpclient import AsyncHTTPClient
from tornado.queues import Queue
from tornado.locks import Semaphore
from tornado.ioloop import IOLoop
from tornado import gen

import random
import bs4
import urlparse
import PIL.Image
import ConfigParser
import sys
import time
import re

# data structures
links = Queue()
imageurls = Queue()
visited_links = set()
downloaded_images = set()
link_failures = []
download_failures = []
img_counter = 0

class LinkExhaustedError(Exception):
    "Raised when waiting on links times out"
    
class Crawler(object):
    def _init_defaults(self):
        self.start_link = None
        self.link_priority = 2
        self.img_priority = 8
        self.politeness = 2
        self.workers_limit = 10 # allow at most 10 concurrent workers
        self.link_regex = re.compile("^http://.*")
        self.img_regex = re.compile(".*")
        self.fname_digits = 4
        self.min_width = 200
        self.min_height = 200
        self.img_dir = "E:/tmp/"
        
    def __init__(self, start_link=None):
        self._init_defaults()

        # Now load the config file to override defaults
        parser = ConfigParser.ConfigParser()
        parser.read("config.ini")
        if parser.has_option("global", "linkregex"):
            self.link_regex = re.compile(parser.get("global", "linkregex"))
        if parser.has_option("global", "imgregex"):
            self.img_regex = re.compile(parser.get("global", "imgregex"))
        
        if start_link:
            self.start_link = start_link
        if not self.start_link:
            raise SystemExit("No start link is provided, exiting now...")
        links.put(self.start_link)
        self.semaphore = Semaphore(self.workers_limit)
        print self.__dict__

    @gen.coroutine
    def run(self):
        while True:
            try:
                if imageurls.qsize()==0 and links.qsize()==0:
                    yield gen.sleep(0.1*self.politeness)
                elif imageurls.qsize()==0:
                    self.handle_links()
                elif links.qsize()==0:
                    self.handle_imageurls()
                else:
                    choices = [0]*self.link_priority +[1]*self.img_priority
                    choice = random.choice(choices)
                    if choice:
                        self.handle_imageurls()
                    else:
                        self.handle_links()
                yield gen.sleep(0.1*self.politeness)
            except LinkExhaustedError:
                # Now there is no more links to be crawled
                break
            
        links.join()
        
        # handling imageurls if not finished
        while imageurls.qsize():
            self.handle_imageurls()
        imageurls.join()

    @gen.coroutine
    def handle_links(self):
        print "Entering link handler"
        yield self.semaphore.acquire()
        try:
            newlink = yield links.get()
        except gen.TimeoutError:
            self.semaphore.release()
            raise LinkExhaustedError()
        print "handling "+newlink
        visited_links.add(newlink)
        
        # use async client to fetch this url
        client = AsyncHTTPClient()
        tries = 3 # Give it 3 chances before putting it in failure
        while tries:
            response = yield client.fetch(newlink)
            if response.code==200:
                break
            tries -= 1
        
        # release the semaphore
        self.semaphore.release()
        if response.code!=200:
            link_failures.append(newlink)            
            raise gen.Return()

        # TODO: replace this with a report api
        print "[VISITED] - %s"%newlink

        # parse url to get the base url
        components = urlparse.urlparse(newlink)
        baseurl = components[0]+"://"+components[1]
        
        # parse the html with bs
        soup = bs4.BeautifulSoup(response.body)
        # extract valid links and put into links
        a_tags = soup.find_all("a")
        for tag in a_tags:
            if "href" not in tag.attrs:
                continue
            href = tag['href']
            if href.startswith("#"):
                continue
            if href.startswith("/"): # relative
                href = baseurl+href
            if not self.link_regex.match(href):
                continue
            if href in visited_links:
                continue
            links.put(href)
            print "NEWLINK:", href
        
        # extract imgs and put into imageurls
        img_tags = soup.find_all("img")
        for tag in img_tags:
            if "src" not in tag.attrs:
                continue
            src = tag['src']
            if src.startswith("/"): # relative
                src = baseurl+src
            if not self.img_regex.match(src):
                continue
            if src in downloaded_images:
                continue
            imageurls.put(src)
            print "NEW IMAGE:", src
                            
        # now the task is done
        links.task_done()

    @gen.coroutine
    def handle_imageurls(self):
        print "Entering image handler"
        yield self.semaphore.acquire()
        imgurl = yield imageurls.get()

        # mark the image as downloaded
        downloaded_images.add(imgurl)
        # use async client to fetch this url
        client = AsyncHTTPClient()
        tries = 3 # Give it 3 chances before putting it in failure
        while tries:
            response = yield client.fetch(imgurl)
            if response.code==200:
                break
            tries -= 1
        # Download is finished, release semaphore
        self.semaphore.release()
        
        if response.code!=200:
            download_failures.append(imgurl)
            print "[FAILURE] - "+imgurl
            raise gen.Return()

        # TODO: replace this with a report api
        print "[DOWNLOADED] - %s"%imgurl
        
        # Read the file content
        img = PIL.Image.open(response.buffer)
        w, h = img.size
        if w <self.min_width or h <self.min_height:
            raise gen.Return()
        
        # find out the image extension, default to jpg
        if "." in imgurl:
            ext = imgurl.split(".")[-1].lower()
            if ext not in ["jpg", "png", "gif"]:
                ext = "jpg"
        elif img.format:
            ext = img.format.lower()
        else:
            ext = "jpg"
            
        # increment the counter
        global img_counter
        img_counter += 1
        fname = str(img_counter).zfill(self.fname_digits)+"."+ext
        fpath = self.img_dir + fname
        # save the image file
        f = open(fpath, "wb")
        f.write(response.body)
        
        # now the task is done
        imageurls.task_done()
        
        
def main():
    # allow user to provide start url from commandline
    if len(sys.argv)>1:
        crawler = Crawler(sys.argv[1])
    else:
        crawler = Crawler()
    
    IOLoop.current().run_sync(crawler.run)

    # TODO: replace with reporting api calls
    print "++++++++++++++++++++++++++++"
    print "%d Links Visited."%len(visited_links)
    print "%d images downloaded"%len(downloaded_images)
    print "Link failures:", link_failures 
    print "Image download failures:", download_failures
    print "++++++++++++++++++++++++++++"
    
if __name__ == "__main__":
    main()

