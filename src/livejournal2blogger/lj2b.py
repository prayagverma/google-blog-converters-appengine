#!/usr/bin/python2.4

# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import getopt
import logging
import md5
import os
import os.path
import re
import sys
import time
import traceback
import urllib2
import xmlrpclib
import xml.dom.minidom

import gdata
from gdata import atom
try:
  import gaexmlrpclib
  from google.appengine.api import urlfetch
  ON_GAE = True
except ImportError:
  ON_GAE = False


__author__ = 'JJ Lueck (jlueck@gmail.com)'

########################
# Constants
########################

CATEGORY_NS = 'http://www.blogger.com/atom/ns#'
CATEGORY_KIND = 'http://schemas.google.com/g/2005#kind'
POST_KIND = 'http://schemas.google.com/blogger/2008/kind#post'
COMMENT_KIND = 'http://schemas.google.com/blogger/2008/kind#comment'
ATOM_TYPE = 'application/atom+xml'
HTML_TYPE = 'text/html'
ATOM_THREADING_NS = 'http://purl.org/syndication/thread/1.0'
DUMMY_URI = 'http://www.blogger.com/'


###########################
# Helper Atom class
###########################

class BloggerGDataFeed(gdata.GDataFeed):

  def _ToElementTree(self):
    tree = gdata.GDataFeed._ToElementTree(self)
    # Modify the tree such that entries are always the last elements
    # of the top-level feed.  This conforms to the Atom specification
    # and fixes a bug where the Blog title may exist after the entries
    # which causes Blogger to ignore the title.
    for i in reversed(range(len(tree))):
      if tree[i].tag.endswith('entry'):
        break
      subelem = tree[i]
      tree.remove(subelem)
      tree.insert(0, subelem)
    return tree


class InReplyTo(atom.ExtensionElement):
  """Supplies the in-reply-to element from the Atom threading protocol."""

  def __init__(self, ref, href=None):
    """Constructs an InReplyTo element."""
    attrs = {}
    attrs['ref'] = ref
    attrs['type'] = ATOM_TYPE
    if href:
      attrs['href'] = href
    atom.ExtensionElement.__init__(self, 'in-reply-to',
                                   namespace=ATOM_THREADING_NS,
                                   attributes=attrs)

###########################
# Helper UserMap class
###########################

class UserMap(object):

  def __init__(self):
    self.comment2user = {}
    self.max_id = -1

  def Add(self, xml_map):
    self._ReadMap(xml_map)

  def GetUser(self, comment_id):
    return self.comment2user.get(comment_id, None)

  def GetLargestId(self):
    return self.max_id

  def _ReadMap(self, xml_map):
    # One half of the XML document contains a map between user ID and
    # the user's name.  Build a user_map with this mapping
    users = xml_map.getElementsByTagName('usermap')
    user_map = dict([(user.getAttribute('id'),
                      user.getAttribute('user')) for user in users])

    # The other half of the XML document contains a map between the
    # comment ID and comment authors
    comments = xml_map.getElementsByTagName('comment')
    for comment in comments:
      comment_id = comment.getAttribute('id')
      user_id = comment.getAttribute('posterid')
      if user_id:
        self.comment2user[comment_id] = user_map[user_id]
      else:
        self.comment2user[comment_id] = 'Anonymous'
      self.max_id = max(int(comment_id), self.max_id)


###########################
# Helper URL fetching
###########################

class UrlFetcherFactory(object):

  def newUrlFetcher(self):
    if ON_GAE:
      return GaeUrlFetcher()
    else:
      return NativeUrlFetcher()

  def fetch(url, payload, headers={}):
    pass


class GaeUrlFetcher(object):

  def fetch(self, url, payload, headers={}):
    response = urlfetch.fetch(url, payload, 'POST', headers)
    return response.content


class NativeUrlFetcher(object):

  def fetch(self, url, payload, headers={}):
    response = urllib2.urlopen(urllib2.Request(url, payload, headers=headers))
    data = response.read()
    response.close()
    return data


###########################
# Translation class
###########################

class LiveJournal2Blogger(object):
  """Performs the translation of LiveJournal blog to the Blogger
     export format.
  """

  def __init__(self, username, password, server='livejournal.com'):
    self.username = username
    self.password = password
    self.server_name = server
    if ON_GAE:
      self.server = xmlrpclib.ServerProxy('http://%s/interface/xmlrpc' % server,
                                          gaexmlrpclib.GAEXMLRPCTransport())
    else:
      self.server = xmlrpclib.ServerProxy('http://%s/interface/xmlrpc' % server)
    self.url_fetcher = UrlFetcherFactory().newUrlFetcher()

  def Translate(self, outfile):
    """Performs the actual translation to a Blogger export format.

    Args:
      outfile: The output file that should receive the translated document
    """
    # Create the top-level feed object
    feed = BloggerGDataFeed()

    # Fill in the feed object with the boilerplate metadata
    feed.generator = atom.Generator(text='Blogger')
    feed.title = atom.Title(text='LiveJournal blog')
    feed.link.append(
        atom.Link(href=DUMMY_URI, rel='self', link_type=ATOM_TYPE))
    feed.link.append(
        atom.Link(href=DUMMY_URI, rel='alternate', link_type=HTML_TYPE))
    feed.updated = atom.Updated(text=self._ToBlogTime(time.gmtime()))

    # Grab the list of posts
    posts = self._GetPosts()
    feed.entry.extend(posts)

    # Grab the list of comments
    comments = self._GetComments()
    feed.entry.extend(comments)

    # Serialize the feed object
    outfile.write(str(feed))

  def _GetPosts(self):
    sync_time = ''
    posts = []
    num_failures = 0
    max_failures = 5
    while num_failures < max_failures:

      start_time = time.time()
      try:
        # Get the next round of items which contain posts/comments
        challenge, challenge_response = self._GetAuthTokens()
        logging.info('Retrieving auth tokens: %d ms' % ((time.time() - start_time) * 1000))
      except:
        logging.error(traceback.format_exc())
        num_failures += 1
        time.sleep(0.5)
        continue

      start_time = time.time()
      try:
        response = self.server.LJ.XMLRPC.syncitems({
            'username': self.username,
            'ver': 1,
            'lastsync': sync_time,
            'auth_method': 'challenge',
            'auth_challenge': challenge,
            'auth_response': challenge_response})
        logging.info('Sync-ing %d items: %d ms' %
                     (len(response['syncitems']), (time.time() - start_time) * 1000))
      except:
        logging.error('Failure after %d ms' % ((time.time() - start_time) * 1000))
        logging.error(traceback.format_exc())
        num_failures += 1
        time.sleep(0.5)
        continue

      # Break out if we have no more items
      if len(response['syncitems']) == 0:
        break

      # Loop through the items and get the contents
      for item in response['syncitems']:
        item_type, item_id = item['item'].split('-')
        if item_type == 'L':

          while num_failures < max_failures:

            start_time = time.time()
            try:
              # Get the next round of items which contain posts/comments
              challenge, challenge_response = self._GetAuthTokens()
              logging.info('Retrieving auth tokens: %d ms' % ((time.time() - start_time) * 1000))
            except:
              logging.error('Failure after %d ms' % ((time.time() - start_time) * 1000))
              logging.error(traceback.format_exc())
              num_failures += 1
              time.sleep(0.5)
              continue

            start_time = time.time()
            try:
              event = self.server.LJ.XMLRPC.getevents({
                  'username': self.username,
                  'ver': 1,
                  'selecttype': 'one',
                  'itemid': item_id,
                  'auth_method': 'challenge',
                  'auth_challenge': challenge,
                  'auth_response': challenge_response})
              logging.info('Retrieved item %s: %d ms' %
                           (item_id, (time.time() - start_time) * 1000))
              if len(event['events']) > 0:
                posts.append(self._TranslatePost(event['events'][0]))
              break

            except:
              logging.error('Failure after %d ms' % ((time.time() - start_time) * 1000))
              logging.error(traceback.format_exc())
              num_failures += 1
              time.sleep(0.5)
              continue

          if num_failures > max_failures:
            raise 'TooManyFailures'

        sync_time = item['time']

    if num_failures > max_failures:
      raise 'TooManyFailures'

    return posts

  def _TranslatePost(self, lj_event):
    post_entry = gdata.GDataEntry()
    post_entry.id = atom.Id(text='post-%d' % lj_event['itemid'])
    post_entry.link.append(
        atom.Link(href=DUMMY_URI, rel='self', link_type=ATOM_TYPE))
    post_entry.link.append(
        atom.Link(href=lj_event['url'], rel='alternate', link_type=ATOM_TYPE))
    post_entry.author = atom.Author(atom.Name(text=self.username))
    post_entry.category.append(
        atom.Category(scheme=CATEGORY_KIND, term=POST_KIND))
    post_entry.published = atom.Published(
        text=self._ToBlogTime(self._FromLjTime(lj_event['eventtime'])))
    post_entry.updated = atom.Updated(
        text=self._ToBlogTime(self._FromLjTime(lj_event['eventtime'])))

    content = lj_event['event']
    if isinstance(lj_event['event'], xmlrpclib.Binary):
      content = lj_event['event'].data
    post_entry.content = atom.Content(
        content_type='html', text=self._TranslateContent(content))

    subject = lj_event.get('subject', None)
    if not subject:
      subject = self._CreateSnippet(content)
    if not isinstance(subject, basestring):
      subject = str(subject)
    post_entry.title = atom.Title(text=subject)

    # Turn the taglist into individual labels
    taglist = lj_event['props'].get('taglist', None)
    if isinstance(taglist, xmlrpclib.Binary):
      taglist = taglist.data
    elif not isinstance(taglist, basestring):
      taglist = str(taglist)

    if taglist:
      tags = taglist.split(',')
      for tag in tags:
        post_entry.category.append(
            atom.Category(scheme=CATEGORY_NS, term=tag.strip()))
    return post_entry

  def _GetComments(self):
    current_id = 0
    max_id = -1
    user_map = UserMap()
    comments = []

    # First make requests to generate the user map.  This is gathered by requesting for
    # comment metadata and paging through the responses.  For each request for a page of
    # comment metadata, add the results to a running UserMap which provides the mapping
    # from comment identifier to the author's name.
    while True:
      session_key = self._GetSessionToken()
      request_url = ('http://%s/export_comments.bml?get=comment_meta&startid=%d'
                     % (self.server_name, current_id))
      response = self.url_fetcher.fetch(
          request_url, None, headers={'Cookie': 'ljsession=%s' % session_key})
      response_doc = xml.dom.minidom.parseString(response)
      user_map.Add(response_doc)

      current_id = user_map.GetLargestId()
      max_id = int(self._GetText(response_doc.getElementsByTagName('maxid')[0]))
      if max_id >= current_id:
        break

    # Second, loop through the contents of the comments and user our UserMap to fill
    # in the author of the comment.  All of the rest of the data is found in the
    # comment response document.
    current_id = 0
    while True:
      session_key = self._GetSessionToken()
      request_url = ('http://%s/export_comments.bml?get=comment_body&startid=%d'
                     % (self.server_name, current_id))
      response = self.url_fetcher.fetch(
          request_url, None, headers={'Cookie': 'ljsession=%s' % session_key})
      response_doc = xml.dom.minidom.parseString(response)

      for comment in response_doc.getElementsByTagName('comment'):
        # If this has been marked as a deleted comment, do not add it
        if comment.getAttribute('state') != 'D':
            comments.append(self._TranslateComment(comment, user_map))
        current_id = int(comment.getAttribute('id'))

      if current_id >= max_id:
        break

    return comments

  def _TranslateComment(self, xml_comment, user_map):
    comment_id = xml_comment.getAttribute('id')

    comment_entry = gdata.GDataEntry()
    comment_entry.id = atom.Id(text='comment-%s' % comment_id)
    comment_entry.link.append(
        atom.Link(href=DUMMY_URI, rel='self', link_type=ATOM_TYPE))
    comment_entry.link.append(
        atom.Link(href=DUMMY_URI, rel='alternate', link_type=ATOM_TYPE))
    comment_entry.author = atom.Author(
        atom.Name(text=user_map.GetUser(comment_id)))
    comment_entry.category.append(
        atom.Category(scheme=CATEGORY_KIND, term=COMMENT_KIND))

    comment_body = self._TranslateContent(
        self._GetText(xml_comment.getElementsByTagName('body')[0]))
    comment_entry.content = atom.Content(
        content_type='html', text=comment_body)
    comment_entry.published = atom.Published(
        text=self._GetText(xml_comment.getElementsByTagName('date')[0]))
    comment_entry.updated = atom.Updated(
        text=self._GetText(xml_comment.getElementsByTagName('date')[0]))

    subject = xml_comment.getElementsByTagName('subject')
    if subject:
      subject = self._GetText(subject[0])
    else:
      subject = self._CreateSnippet(comment_body)
    comment_entry.title = atom.Title(text=subject)

    comment_entry.extension_elements.append(
        InReplyTo('post-%s' % xml_comment.getAttribute('jitemid')))

    return comment_entry

  def _TranslateContent(self, content):
    if not isinstance(content, basestring):
      content = str(content)
    return content.replace('\r\n', '<br/>')

  def _GetAuthTokens(self):
    """Returns the information necessary to create new requests to the
    LiveJournal server using XML-RPC.  Returns a tuple containing the challege,
    and the successful response to the challenge.
    """
    response = self.server.LJ.XMLRPC.getchallenge()
    challenge = response['challenge']
    return challenge, self._HashChallenge(challenge)

  def _GetSessionToken(self):
    """Returns the information necessary to create new requests to the
    LiveJournal server via HTTP.
    """
    # Use the flat RPC protocol to generate the session information
    request_url = 'http://%s/interface/flat' % self.server_name

    # The first request is used to obtain the challenge token
    response = self.url_fetcher.fetch(request_url, 'mode=getchallenge')
    challenge = self._ResponseToDict(response)['challenge']

    # The second request is to actually generate the session cookie by
    # responding to the challenge
    challenge_response = self._HashChallenge(challenge)
    response = self.url_fetcher.fetch(
        request_url, ('mode=sessiongenerate&auth_method=challenge&'
                      'user=%s&auth_challenge=%s&auth_response=%s' %
                      (self.username, challenge, challenge_response)))
    result = self._ResponseToDict(response)

    if result.get('errmsg', None):
      raise 'Login Unsuccessful'
    return result['ljsession']

  def _ResponseToDict(self, contents):
    """Takes the result of a request to the LiveJournal flat XML-RPC
    protocol and transforms the key/value pairs into a dictionary.
    """
    elems = contents.split('\n')
    # This little bit of Python wizardry turns a list of elements into
    # key value pairs.
    return dict(zip(elems[::2], elems[1::2]))

  def _HashChallenge(self, challenge):
    """Hashes the challege with the password to produce the challenge
    response.
    """
    return md5.new(challenge + md5.new(self.password).hexdigest()).hexdigest()

  def _CreateSnippet(self, content):
    """Creates a snippet of content.  The maximum size being 53 characters,
    50 characters of data followed by elipses.
    """
    content = re.sub('<[^>]+>', '', content)
    if isinstance(content, str):
      content = content.decode('UTF-8', 'ignore')
    if len(content) < 50:
      return content
    return content[:49] + '...'

  def _GetText(self, xml_elem):
    """Assumes the text for the element is the only child of the element."""
    return xml_elem.firstChild.nodeValue

  def _FromLjTime(self, lj_time):
    """Converts the LiveJournal event time to a time/date struct."""
    return time.strptime(lj_time, '%Y-%m-%d %H:%M:%S')

  def _ToBlogTime(self, time_tuple):
    """Converts a time struct to a Blogger time/date string."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time_tuple)


def usage():
  return ('Usage: %s -u <username> -p <password> [-s <server>]\n\n'
          ' Outputs the converted Blogger export file to standard out.' %
          os.path.basename(sys.argv[0]))

if __name__ == '__main__':

  # parse command line options
  try:
    opts, args = getopt.getopt(
        sys.argv[1:], 'u:p:s:', ['username=', 'password=', 'server='])
  except getopt.error, msg:
    print usage()
    sys.exit(2)

  # Store the parsed results
  username = None
  password = None
  server = 'livejournal.com'

  # Process options
  for opt, arg in opts:
    if opt in ['-u', '--username']:
      username = arg
    elif opt in ['-p', '--password']:
      password = arg
    elif opt in ['-s', '--server']:
      server = arg

  if not username or not password:
    print usage()
    sys.exit(-1)

  # Perform the translation
  translator = LiveJournal2Blogger(username, password, server)
  translator.Translate(sys.stdout)
