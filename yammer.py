import re
import random
from collections import deque
import sys
from time import sleep
import logging

import mechanize
from BeautifulSoup import *
import twitter

import summarize

try:
   from twitter_credentials import (kConsumerKey, kConsumerSecret,
    kAccessTokenKey, kAccessTokenSecret)
except ImportError:
   sys.exit("You must create twitter_credentials.py " +
    "with four constants: kConsumerKey, kConsumerSecret, " +
    "kAccessTokenKey, kAccessTokenSecret")

kMaxPara = 3
kLinkQueueSize = 12
kSeenUrlQueueSize = 64
kSeenSummaryQueueSize = 22

kMechanizeTimeout = 5.0 # seconds

kSendTweets = True

kSleepRange = (6 * 60, 6 * 60 * 60) # 6 mins - 6 hours

# These are known to provide uninteresting content.
kCrapDomains = frozenset(('google.com', 'adobe.com', 'amazon.com',
 'microsoft.com', 'youtube.com', 'twitter.com', 'paypal.com'))

kExcessWhitespace = re.compile('\s{2,}')

kPostLimit = 140

logging.basicConfig(filename='yammer.log', level=logging.DEBUG)

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

def GroomPost(post):
   post = re.sub(kExcessWhitespace, ' ', post).strip()
   return post[:kPostLimit]

def BadSummary(summary):
   if not summary:
      return True
   lowerSummary = summary.lower()

   return u"copyright" in lowerSummary or u"\xa9" in lowerSummary

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
   twitterApi = twitter.Api(kConsumerKey, kConsumerSecret,
    kAccessTokenKey, kAccessTokenSecret)

   mech = mechanize.Browser()
   mech.set_handle_robots(False)
   mech.addheaders = [('User-Agent',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1')]

   """
   Generally,
   Start with a few known creepy link warehouses in the link queue.
   while there are queued links:
      pop a link
      crawl it
      enqueue a random selection of links pointed to by that page
      tweet a groomed selection of text from that page

   There are a few mechanisms to reduce the amount of crap and avoid redundant
   crawls, etc.
   """

   linkQueue = deque([
    "http://www.ishouldbeworking.com/creepy.htm",
    "http://secretcrypt.com/newcrypt/bizarre/linkspage.html",
    "http://www.truthjuice.co.uk/?page_id=5942",
    "http://www.creepylinks.com/sites.html"
    ], kLinkQueueSize)

   seenUrls = deque([], kSeenUrlQueueSize)
   seenSummaries = deque([], kSeenSummaryQueueSize)

   def DecentLookingLink(link):
      absUrl = link.absolute_url

      return (
       not link.url.startswith('#')
       and absUrl.startswith('http')
       and absUrl not in seenUrls
       and all(shitDomain not in absUrl for shitDomain in kCrapDomains)
      )

   while len(linkQueue) > 0:
      nextUrl = linkQueue.pop()

      if nextUrl in seenUrls:
         continue
      seenUrls.appendleft(nextUrl)

      logging.debug("Processing URL: %s", nextUrl)

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

      summary = GroomPost(GetSummary(soup))

      if BadSummary(summary) or summary in seenSummaries:
         continue

      seenSummaries.appendleft(summary)

      try:
         links = filter(DecentLookingLink, mech.links())

         random.shuffle(links)

         for link in links[:2]:
            linkQueue.appendleft(link.absolute_url)

         logging.debug("Link queue size: %d", len(linkQueue))
      except:
         logging.exception("Exception while processing links.")

      logging.debug('Summary: ' + summary)

      if kSendTweets:
         try:
            response = twitterApi.PostUpdate(summary)
            logging.debug(response)
         except twitter.TwitterError, ex:
            if "duplicate" in ex.message:
               continue
            logging.exception("Twitter issue.")

         sleepSeconds = random.randrange(*kSleepRange)
         logging.info("Sleeping for %d seconds.", sleepSeconds)
         sleep(sleepSeconds)

   logging.debug("Link queue exhausted.")
