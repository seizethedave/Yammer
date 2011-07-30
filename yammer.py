import re
import random
from collections import deque

import mechanize
import summarize
from BeautifulSoup import *


def PatchSoupTag():
   """
   Monkeypatch BeautifulSoup Tag to handle spaces better.
   https://code.launchpad.net/~mjumbewu/beautifulsoup/text-white-space-fix/+merge/62629
   """
   def getText(soup, separator=u""):
      if not len(soup.contents):
         return u""
      stopNode = soup._lastRecursiveChild().next
      strings = []
      current = soup.contents[0]
      while current is not stopNode:
         if isinstance(current, NavigableString):
            strings.append(current)
         current = current.next

      result = separator.join(strings)
      return re.sub(r'\s+', ' ', result)

   Tag.getText = getText
   Tag.text = property(getText)


PatchSoupTag()

kMaxPara = 3

kStartConcepts = ('creepy',)

def FlattenSoupTags(paras):
   for p in paras:
      for atom in p:
         if isinstance(atom, NavigableString):
            yield unicode(atom)
         else:
            yield atom.text

def GetSummary(soup):
   paragraphs = soup.findAll('p')[:kMaxPara]
   t = FlattenSoupTags(paragraphs)
   text = u''.join(t)
   summarizer = summarize.SimpleSummarizer()
   summary = summarizer.summarize(text, 1)
   return summary

if '__main__' == __name__:
   mech = mechanize.Browser()
   mech.set_handle_robots(False)
   mech.addheaders = [('User-Agent',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1')]

   linkQueue = deque([], 10)

   startUrl = "http://en.wikipedia.org/wiki/MRSA"

   request = startUrl

   while True:
      try:
         mech.open(request)
         data = mech.response().read()
      except:
         data = None

      if not data:
         request = mech.click_link(linkQueue.pop())
         continue

      print mech.geturl()

      if not mech.viewing_html():
         data = None
         continue

      try:
         soup = BeautifulSoup(data)
      except UnicodeEncodeError:
         data = None
         continue

      print GetSummary(soup)
      links = filter(lambda l: not l.url.startswith('#'), mech.links())

      random.shuffle(links)

      for link in links[:4]:
         linkQueue.appendleft(link)

      print len(linkQueue)

      request = mech.click_link(linkQueue.pop())

