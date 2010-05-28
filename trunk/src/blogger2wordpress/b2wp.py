#!/usr/bin/env python

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

import os.path
import logging
import re
import sys
import time
from xml.sax.saxutils import unescape

import BeautifulSoup
import gdata
from gdata import atom
import iso8601
import wordpress

__author__ = 'JJ Lueck (jlueck@gmail.com)'


###########################
# Constants
###########################

BLOGGER_URL = 'http://www.blogger.com/'
BLOGGER_NS = 'http://www.blogger.com/atom/ns#'
KIND_SCHEME = 'http://schemas.google.com/g/2005#kind'

YOUTUBE_RE = re.compile('http://www.youtube.com/v/([^&]+)&?.*')
YOUTUBE_FMT = r'[youtube=http://www.youtube.com/watch?v=\1]'
GOOGLEVIDEO_RE = re.compile('(http://video.google.com/googleplayer.swf.*)')
GOOGLEVIDEO_FMT = r'[googlevideo=\1]'
DAILYMOTION_RE = re.compile('http://www.dailymotion.com/swf/(.*)')
DAILYMOTION_FMT = r'[dailymotion id=\1]'


###########################
# Translation class
###########################


class Blogger2Wordpress(object):
  """Performs the translation of a Blogger export document to WordPress WXR."""

  def __init__(self, doc):
    """Constructs a translator for a Blogger export file.

    Args:
      doc: The WXR file as a string
    """

    # Ensure UTF8 chars get through correctly by ensuring we have a
    # compliant UTF8 input doc.
    self.doc = doc.decode('utf-8', 'replace').encode('utf-8')

    # Read the incoming document as a GData Atom feed.
    self.feed = atom.FeedFromString(self.doc)
    self.next_id = 1

  def Translate(self):
    """Performs the actual translation to WordPress WXR export format.

    Returns:
      A WordPress WXR export document as a string, or None on error.
    """
    # Create the top-level document and the channel associated with it.
    channel = wordpress.Channel(
        title = self.feed.title.text,
        link = self.feed.GetAlternateLink().href,
        base_blog_url = self.feed.GetAlternateLink().href,
        pubDate = self._ConvertPubDate(self.feed.updated.text))
    posts_map = {}

    for entry in self.feed.entry:

      # Grab the information about the entry kind
      entry_kind = ""
      for category in entry.category:
        if category.scheme == KIND_SCHEME:
          entry_kind = category.term

      if entry_kind.endswith("#comment"):
        # This entry will be a comment, grab the post that it goes to
        in_reply_to = entry.FindExtensions('in-reply-to')
        post_item = None
        # Check to see that the comment has a corresponding post entry
        if in_reply_to:
          post_id = self._ParsePostId(in_reply_to[0].attributes['ref'])
          post_item = posts_map.get(post_id, None)

        # Found the post for the comment, add the commment to it
        if post_item:
          # The author email may not be included in the file
          author_email = ''
          if entry.author[0].email:
            author_email = entry.author[0].email.text

          # Same for the the author's url
          author_url = ''
          if entry.author[0].uri:
            author_url = entry.author[0].uri.text

          post_item.comments.append(wordpress.Comment(
              comment_id = self._GetNextId(),
              author = entry.author[0].name.text,
              author_email = author_email,
              author_url = author_url,
              date = self._ConvertDate(entry.published.text),
              content = self._ConvertContent(entry.content.text)))

      elif entry_kind.endswith('#post'):
        # This entry will be a post
        post_item = self._ConvertEntry(entry, False)
        posts_map[self._ParsePostId(entry.id.text)] = post_item
        channel.items.append(post_item)

      elif entry_kind.endswith('#page'):
        # This entry will be a static page
        page_item = self._ConvertEntry(entry, True)
        posts_map[self._ParsePageId(entry.id.text)] = page_item
        channel.items.append(page_item)

    wxr = wordpress.WordPressWxr(channel=channel)
    return wxr.WriteXml()

  def _ConvertEntry(self, entry, is_page):
    """Converts the contents of an Atom entry into a WXR post Item element."""

    # A post may have an empty title, in which case the text element is None.
    title = ''
    if entry.title.text:
      title = entry.title.text

    # Check here to see if the entry points to a draft or regular post
    status = 'publish'
    if entry.control and entry.control.draft:
      status = 'draft'

    # If no link is present in the Blogger entry, just link
    if entry.GetAlternateLink():
      link = entry.GetAlternateLink().href
    else:
      link = BLOGGER_URL

    # Declare whether this is a post of a page
    post_type = 'post'
    if is_page:
      post_type = 'page'

    blogger_blog = ''
    blogger_permalink = ''
    if entry.GetAlternateLink():
      blogger_path_full = entry.GetAlternateLink().href.replace('http://', '')
      blogger_blog = blogger_path_full.split('/')[0]
      blogger_permalink = blogger_path_full[len(blogger_blog):]

    # Create the actual item element
    post_item = wordpress.Item(
        title = title,
        link = link,
        pubDate = self._ConvertPubDate(entry.published.text),
        creator = entry.author[0].name.text,
        content = self._ConvertContent(entry.content.text),
        post_id = self._GetNextId(),
        post_date = self._ConvertDate(entry.published.text),
        status = status,
        post_type = post_type,
        blogger_blog = blogger_blog,
        blogger_permalink = blogger_permalink,
        blogger_author = entry.author[0].name.text)

    # Convert the categories which specify labels into wordpress labels
    for category in entry.category:
      if category.scheme == BLOGGER_NS:
        post_item.labels.append(category.term)

    return post_item

  def _ConvertContent(self, text):
    """Unescapes the post/comment text body and replaces video content.

    All <object> and <embed> tags in the post that relate to video must be
    changed into the WordPress tags for embedding video,
    e.g. [youtube=http://www.youtube.com/...]

    If no text is provided, the empty string is returned.
    """
    if not text:
      return ''

    # First unescape all XML tags as they'll be escaped by the XML emitter
    content = unescape(text)

    # Use an HTML parser on the body to look for video content
    content_tree = BeautifulSoup.BeautifulSoup(content)

    # Find the object tag
    objs = content_tree.findAll('object')
    for obj_tag in objs:
      # Find the param tag within which contains the URL to the movie
      param_tag = obj_tag.find('param', { 'name': 'movie' })
      if not param_tag:
        continue

      # Get the video URL
      video = param_tag.attrMap.get('value', None)
      if not video:
        continue

      # Convert the video URL if necessary
      video = YOUTUBE_RE.subn(YOUTUBE_FMT, video)[0]
      video = GOOGLEVIDEO_RE.subn(GOOGLEVIDEO_FMT, video)[0]
      video = DAILYMOTION_RE.subn(DAILYMOTION_FMT, video)[0]

      # Replace the portion of the contents with the video
      obj_tag.replaceWith(video)

    return str(content_tree)

  def _ConvertPubDate(self, date):
    """Translates to a pubDate element's time/date format."""
    date_tuple = iso8601.parse_date(date)
    return date_tuple.strftime('%a, %d %b %Y %H:%M:%S %z')

  def _ConvertDate(self, date):
    """Translates to a wordpress date element's time/date format."""
    date_tuple = iso8601.parse_date(date)
    return date_tuple.strftime('%Y-%m-%d %H:%M:%S')

  def _GetNextId(self):
    """Returns the next identifier to use in the export document as a string."""
    next_id = self.next_id;
    self.next_id += 1
    return str(next_id)

  def _ParsePostId(self, text):
    """Extracts the post identifier from a Blogger entry ID."""
    matcher = re.compile('post-(\d+)')
    matches = matcher.search(text)
    return matches.group(1)

  def _ParsePageId(self, text):
    """Extracts the page identifier from a Blogger entry ID."""
    matcher = re.compile('page-(\d+)')
    matches = matcher.search(text)
    return matches.group(1)

if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print 'Usage: %s <blogger_export_file>' % os.path.basename(sys.argv[0])
    print
    print ' Outputs the converted WordPress export file to standard out.'
    sys.exit(-1)

  wp_xml_file = open(sys.argv[1])
  wp_xml_doc = wp_xml_file.read()
  translator = Blogger2Wordpress(wp_xml_doc)
  print translator.Translate()
  wp_xml_file.close()
