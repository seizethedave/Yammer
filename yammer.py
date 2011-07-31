import re
import random
from collections import deque

import mechanize
import summarize
from BeautifulSoup import *

kMaxPara = 3
kLinkQueueSize = 12
kSeenUrlQueueSize = 64
kSeenSummaryQueueSize = 22

kMechanizeTimeout = 10.0

# These are known to provide uninteresting content.

kShitDomains = frozenset(('google.com', 'adobe.com', 'amazon.com',
 'microsoft.com', 'youtube.com'))

def PatchSoupTag():
   """
   Monkeypatch BeautifulSoup Tag to handle spaces better.
   http://bit.ly/ndELQk
   """
   def getText(tag, separator=u""):
      if not len(tag.contents):
         return u""
      stopNode = tag._lastRecursiveChild().next
      strings = []
      current = tag.contents[0]
      while current is not stopNode:
         if isinstance(current, NavigableString):
            strings.append(current)
         current = current.next

      result = separator.join(strings)
      return re.sub(r'\s+', ' ', result)

   Tag.getText = getText
   Tag.text = property(getText)


PatchSoupTag()



def FlattenSoupTags(paras):
   for p in paras:
      for atom in p:
         if isinstance(atom, NavigableString):
            yield unicode(atom)
         else:
            yield atom.text


def CleanSoup(soup):
   stuffToDelete = ("script", "style", "header", "footer", "nav",
    "h1", "h2", "h3", "h4", "h5", "h6")

   for tag in stuffToDelete:
      for item in soup.findAll(tag):
         item.extract()

def GetSummary(soup):
   paragraphs = soup.findAll('p')
   random.shuffle(paragraphs)
   paragraphs = paragraphs[:kMaxPara]
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

   linkQueue = deque([
    "http://www.ishouldbeworking.com/creepy.htm",
    "http://secretcrypt.com/newcrypt/bizarre/linkspage.html",
    "http://www.parapsychologydegrees.com/",
    "http://www.scaryscreaming.com/ranesreads.html",

    ], kLinkQueueSize)

   seenUrls = deque([], kSeenUrlQueueSize)
   seenSummaries = deque([], kSeenSummaryQueueSize)

   def DecentLookingLink(link):
      absUrl = link.absolute_url

      return (
       not link.url.startswith('#')
       and absUrl.startswith('http')
       and absUrl not in seenUrls
       and all(shitDomain not in absUrl for shitDomain in kShitDomains)
      )

   while len(linkQueue) > 0:
      nextUrl = linkQueue.pop()

      if nextUrl in seenUrls:
         continue
      seenUrls.appendleft(nextUrl)

      print "Processing URL: %s" % nextUrl

      try:
         mech.open(nextUrl, timeout = kMechanizeTimeout)
         data = mech.response().read()
      except:
         continue

      if not data or not mech.viewing_html():
         continue

      try:
         soup = BeautifulSoup(data)
      except UnicodeEncodeError:
         continue

      CleanSoup(soup)

      summary = GetSummary(soup)

      if not summary or summary in seenSummaries:
         continue

      seenSummaries.appendleft(summary)

      print summary

      try:
         links = filter(DecentLookingLink, mech.links())
      except:
         continue

      random.shuffle(links)

      for link in links[:2]:
         linkQueue.appendleft(link.absolute_url)

      print "Link queue size: %d" % len(linkQueue)

   print "Link queue exhausted."
