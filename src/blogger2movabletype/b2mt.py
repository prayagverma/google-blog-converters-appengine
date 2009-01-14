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

import gdata
from gdata import atom
import iso8601
import movabletype

__author__ = 'JJ Lueck (jlueck@gmail.com)'


###########################
# Constants
###########################

BLOGGER_NS = 'http://www.blogger.com/atom/ns#'
KIND_SCHEME = 'http://schemas.google.com/g/2005#kind'

###########################
# Translation class
###########################


class Blogger2MovableType(object):
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

    # Keep a map of posts so that we can write out one post with all of
    # its comments
    posts_map = {}
    mt = movabletype.MovableTypeExport()
    
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

          comment = movabletype.MovableTypeComment()
          comment.author = entry.author[0].name.text
          comment.email = author_email
          comment.url = author_url
          comment.date = self._ConvertDate(entry.published.text)
          comment.body = self._ConvertContent(entry.content.text)
          post_item.comments.append(comment)

      elif entry_kind.endswith("#post"):
        # This entry will be a post
        post_item = self._ConvertPostEntry(entry)
        posts_map[self._ParsePostId(entry.id.text)] = post_item
        mt.posts.append(post_item)

    return mt.ToString()

  def _ConvertPostEntry(self, entry):
    """Converts the contents of an Atom entry into a WXR post Item element."""

    # A post may have an empty title, in which case the text element is None.
    title = ''
    if entry.title.text:
      title = entry.title.text

    # Check here to see if the entry points to a draft or regular post
    status = 'Publish'
    if entry.control and entry.control.draft:
      status = 'Draft'

    # Create the actual item element
    post_item = movabletype.MovableTypePost()
    post_item.title = title
    post_item.date = self._ConvertDate(entry.published.text),
    post_item.author = entry.author[0].name.text,
    post_item.body = self._ConvertContent(entry.content.text),
    post_item.status = status

    # Convert the categories which specify labels into wordpress labels
    for category in entry.category:
      if category.scheme == BLOGGER_NS:
        post_item.categories.append(category.term)
        
        # How does one specify the primary category for a post
        post_item.primary_category = category.term

    return post_item

  def _ConvertContent(self, text):
    """Converts the text into plain-text
    
    If no text is provided, the empty string is returned.
    """
    if not text:
      return ''

    # First unescape all XML tags as they'll be escaped by the XML emitter
    content = unescape(text)
    return str(content)

  def _ConvertDate(self, date):
    """Translates to a wordpress date element's time/date format."""
    date_tuple = iso8601.parse_date(date)
    return date_tuple.strftime('%m/%d/%Y %I:%M:%S %p')

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

if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print 'Usage: %s <blogger_export_file>' % os.path.basename(sys.argv[0])
    print
    print ' Outputs the converted MovableType export file to standard out.'
    sys.exit(-1)

  wp_xml_file = open(sys.argv[1])
  wp_xml_doc = wp_xml_file.read()
  translator = Blogger2MovableType(wp_xml_doc)
  print translator.Translate()
  wp_xml_file.close()
