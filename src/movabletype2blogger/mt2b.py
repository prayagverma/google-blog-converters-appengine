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

import os.path
import logging
import re
import sys
import time
from xml.sax.saxutils import escape

import gdata
from gdata import atom

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
# Translation class
###########################

class MovableType2Blogger(object):
  """Performs the translation of MovableType text export to Blogger
     export format.
  """

  def __init__(self):
    self.next_id = 1
  
  def Translate(self, infile, outfile):
    """Performs the actual translation to a Blogger export format.

    Args:
      infile: The input MovableType export file
      outfile: The output file that should receive the translated document
    """
    # Create the top-level feed object
    feed = BloggerGDataFeed()

    # Fill in the feed object with the boilerplate metadata
    feed.generator = atom.Generator(text='Blogger')
    feed.title = atom.Title(text='MovableType blog')
    feed.link.append(
        atom.Link(href=DUMMY_URI, rel='self', link_type=ATOM_TYPE))
    feed.link.append(
        atom.Link(href=DUMMY_URI, rel='alternate', link_type=HTML_TYPE))

    # Calculate the last updated time by inspecting all of the posts
    last_updated = 0

    # These three variables keep the state as we parse the file
    post_entry = None    # The current post atom.Entry to populate
    comment_entry = None # The current comment atom.Entry to populate
    last_entry = None    # The previous post atom.Entry if exists
    tag_name = None      # The current name of multi-line values
    tag_contents = ''    # The contents of multi-line values

    # Loop through the text lines looking for key/value pairs
    for line in infile:

      # Remove whitespace
      line = line.strip()

      # Check for the post ending token
      if line == '-' * 8 and tag_name != 'BODY':
        if post_entry:
          # Add the post to our feed
          feed.entry.insert(0, post_entry)
          last_entry = post_entry

        # Reset the state variables
        post_entry = None
        comment_entry = None
        tag_name = None
        tag_contents = ''
        continue

      # Check for the tag ending separator
      elif line == '-' * 5:
        # Get the contents of the body and set the entry contents
        if tag_name == 'BODY':
          post_entry.content = atom.Content(
              content_type='html', text=self._TranslateContents(tag_contents))

        # This is the start of the COMMENT section.  Create a new entry for
        # the comment and add a link to the original post.
        elif tag_name == 'COMMENT':
          comment_entry.content = atom.Content(
              content_type='html', text=self._TranslateContents(tag_contents))
          comment_entry.title = atom.Title(
            text=self._Encode(self._CreateSnippet(tag_contents)))
          comment_entry.extension_elements.append(InReplyTo(post_entry.id.text))
          feed.entry.append(comment_entry)
          comment_entry = None

        # Get the contents of the extended body and append it to the
        # entry contents
        elif tag_name == 'EXTENDED BODY':
          if post_entry:
            post_entry.content.text += '<br/>' + self._TranslateContents(tag_contents)
          elif last_entry and last_entry.content:
            last_entry.content.text += '<br/>' + self._TranslateContents(tag_contents)

        # Convert any keywords (comma separated values) into Blogger labels
        elif tag_name == 'KEYWORDS':
          for keyword in tag_contents.split(','):
            keyword = keyword.strip()
            if keyword != '':
              post_entry.category.append(
                  atom.Category(scheme=CATEGORY_NS, term=keyword))

        # Reset the current tag and its contents
        tag_name = None
        tag_contents = ''
        continue

      # Split the line into key/value pairs
      elems = line.split(':')
      key = elems[0]
      value = ''
      if len(elems) > 1:
        value = ':'.join(elems[1:]).strip()

      # The author key indicates the start of a post as well as the author of
      # the post entry or comment
      if key == 'AUTHOR':
        # Create a new entry 
        entry = gdata.GDataEntry()
        entry.link.append(
            atom.Link(href=DUMMY_URI, rel='self', link_type=ATOM_TYPE))
        entry.link.append(
            atom.Link(href=DUMMY_URI, rel='alternate', link_type=HTML_TYPE))
        entry.id = atom.Id('post-' + self._GetNextId())
        # Add the author's name
        author_name = self._Encode(value)
        if not author_name:
          author_name = 'Anonymous'
        entry.author = atom.Author(atom.Name(text=author_name))

        # Add the appropriate kind, either a post or a comment
        if tag_name == 'COMMENT':
          entry.category.append(
              atom.Category(scheme=CATEGORY_KIND, term=COMMENT_KIND))
          comment_entry = entry
        else:
          entry.category.append(
              atom.Category(scheme=CATEGORY_KIND, term=POST_KIND))
          post_entry = entry

      # The title only applies to new posts
      elif key == 'TITLE' and tag_name != 'PING':
        post_entry.title = atom.Title(text=self._Encode(value))

      # If the status is a draft, mark it as so in the entry.  If the status
      # is 'Published' there's nothing to do here
      elif key == 'STATUS':
        if value == 'Draft':
          post_entry.control = atom.Control(atom.Draft('yes'))

      # Turn categories into labels
      elif key == 'CATEGORY':
        if value != '':
          post_entry.category.append(
              atom.Category(scheme=CATEGORY_NS, term=value))

      # Convert the date and specify it as the published/updated time
      elif key == 'DATE' and tag_name != 'PING':
        time_val = self._FromMtTime(value)
        entry = post_entry
        if tag_name == 'COMMENT':
          entry = comment_entry
        entry.published = atom.Published(self._ToBlogTime(time_val))
        entry.updated = atom.Updated(self._ToBlogTime(time_val))

        # Check to see if this was the last post published (so far)
        seconds = time.mktime(time_val)
        last_updated = max(seconds, last_updated)

      # Convert all tags into Blogger labels
      elif key == 'TAGS':
        for keyword in value.split(','):
          keyword = keyword.strip()
          if keyword != '':
            post_entry.category.append(
                atom.Category(scheme=CATEGORY_NS, term=keyword))

      # Update the author's email if it is present and not empty
      elif tag_name == 'COMMENT' and key == 'EMAIL' and len(value) > 0:
        comment_entry.author.email = atom.Email(text=value)

      # Update the author's URI if it is present and not empty
      elif tag_name == 'COMMENT' and key == 'URL' and len(value) > 0:
        comment_entry.author.uri = atom.Uri(text=value)

      # If any of these keys are used, they contain information beyond this key
      # on following lines
      elif key in ('COMMENT', 'BODY', 'EXTENDED BODY', 'EXCERPT', 'KEYWORDS', 'PING'):
        tag_name = key

      # These lines can be safely ignored
      elif key in ('BASENAME', 'ALLOW COMMENTS', 'CONVERT BREAKS', 
                   'ALLOW PINGS', 'PRIMARY CATEGORY', 'IP', 'URL', 'EMAIL'):
        continue

      # If the line is empty and we're processing the body, add an HTML line
      # break
      elif tag_name == 'BODY' and len(line) == 0:
        tag_contents += '<br/>'

      # This would be a line of content beyond a key/value pair
      elif len(key) != 0:
        tag_contents += line + '\n'


    # Update the feed with the last updated time
    feed.updated = atom.Updated(self._ToBlogTime(time.gmtime(last_updated)))

    # Serialize the feed object
    outfile.write(str(feed))

  def _GetNextId(self):
    """Returns the next entry identifier as a string."""
    ret = self.next_id
    self.next_id += 1
    return str(self.next_id)

  def _CreateSnippet(self, content):
    """Creates a snippet of content.  The maximum size being 53 characters,
    50 characters of data followed by elipses.
    """
    content = re.sub('</?[^>/]+/?>', '', content)
    if len(content) < 50:
      return content
    return content[0:49] + '...'

  def _TranslateContents(self, content):
    content = content.replace('\n', '<br/>')
    return self._Encode(content)

  def _Encode(self, content):
    return unicode(content, errors='ignore')

  def _FromMtTime(self, mt_time):
    return time.strptime(mt_time, "%m/%d/%Y %I:%M:%S %p")

  def _ToBlogTime(self, time_tuple):
    """Converts a time struct to a Blogger time/date string."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time_tuple)

if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print 'Usage: %s <movabletype_export_file>' % os.path.basename(sys.argv[0])
    print
    print ' Outputs the converted Blogger export file to standard out.'
    sys.exit(-1)
    
  mt_file = open(sys.argv[1])
  translator = MovableType2Blogger()
  translator.Translate(mt_file, sys.stdout)
  mt_file.close()

    
