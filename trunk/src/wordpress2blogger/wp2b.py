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
import xml.sax

import gdata
from gdata import atom

__author__ = 'JJ Lueck (jlueck@google.com)'

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

WP_YOUTUBE_RE = re.compile('\[youtube=http://www.youtube.com/watch\?v=([^\]]+)\]')
EMBED_YOUTUBE_FMT = \
  r"""<object height="350" width="425">
      <param name="movie" value="http://www.youtube.com/v/\1">
      <param name="wmode" value="transparent">
      <embed src="http://www.youtube.com/v/\1;rel=0" type="application/x-shockwave-flash" wmode="transparent" height="350" width="425">
      </object>"""

WP_GOOGLEVIDEO_RE = \
  re.compile('\[googlevideo=(http://video.google.com/googleplayer.swf\?docid=[^\]]+)\]', re.I)
EMBED_GOOGLEVIDEO_FMT = \
  r"""<object type="application/x-shockwave-flash" data="\1" height="326" width="400">
      <param name="allowScriptAccess" value="never">
      <param name="movie" value="\1">
      <param name="quality" value="best">
      <param name="bgcolor" value="#ffffff">
      <param name="scale" value="noScale">
      <param name="wmode" value="window"></object>"""

WP_DAILYMOTION_RE = re.compile('\[dailymotion id=([^\]]+)\]')
EMBED_DAILYMOTION_FMT = \
  r"""<object height="254" width="425">
      <param name="movie" value="http://www.dailymotion.com/swf/\1">
      <param name="allowfullscreen" value="true">
      <embed src="http://www.dailymotion.com/swf/\1" type="application/x-shockwave-flash" allowfullscreen="true" height="334" width="425">
      </object>"""

NORMALIZE_BREAKS_RE = re.compile('(<br\s*/?>\r?|\r|)\n')

###########################
# Helper Atom class
###########################


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


class Wordpress2Blogger(xml.sax.handler.ContentHandler):
  """Performs the translation of wordpress export to Blogger export format."""

  def __init__(self):
    """Constructs a translator for a wordpress WXR file."""
    pass

  def Translate(self, doc, outfile):
    """Performs the actual translation to a Blogger export format.

    Args:
      doc: The input WXR file as a string
      outfile: The output file that should receive the translated document
    Returns:
      A Blogger export Atom document as a string, or None on error.
    """
    # Create the top-level feed object
    self.feed = gdata.GDataFeed()
    self.feed.generator = atom.Generator(text='Blogger')
    self.elem_stack = []
    self.contents = ''
    self.outfile = outfile
    self.current_post = None
    self.categories = set()
    self.comments = []
    xml.sax.parseString(doc, self)

  def GetParentElem(self):
    if self.elem_stack:
      return self.elem_stack[0]
    return None

  ###################################
  # ContentHandler methods
  ###################################

  def startElement(self, name, attrs):
    self.elem_stack.insert(0, name)
    handler = getattr(self, 'start%s' % name.split(':')[-1].title(), None)
    if handler:
      handler()

  def endElement(self, name):
    self.elem_stack.pop(0)

    handler = getattr(self, 'end%s' % name.split(':')[-1].title(), None)
    if handler:
      handler(self.contents.strip())

    del self.contents
    self.contents = ''

  def characters(self, content):
    self.contents += content

  def endDocument(self):
    # Write the contents of the feed
    self.outfile.write(str(self.feed))

  ###################################
  # WordPress element handlers
  ###################################

  def endTitle(self, content):
    parent = self.GetParentElem()
    if parent == 'channel':
      self.feed.title = atom.Title('html', text=content)
    elif parent == 'item' and self.current_post:
      self.current_post.title = atom.Title('html', content)

  def endPubdate(self, content):
    if not self.current_post:
      self.feed.published = atom.Published(
          self._ToBlogTime(self._WordpressPubDateToTime(content)))
      self.feed.updated = atom.Updated(
          self._ToBlogTime(self._WordpressPubDateToTime(content)))

  def startItem(self):
    self.current_post = gdata.GDataEntry()

  def endItem(self, _):
    if self.current_post:
      # Add the categories that we've collected
      self.current_post.category.extend(
          [atom.Category(c, CATEGORY_NS) for c in self.categories])
      # Add the category specifying this as a post
      self.current_post.category.append(atom.Category(scheme=CATEGORY_KIND,
                                                      term=POST_KIND))
      # Check to see if we need to fill in the published time
      if not self.current_post.published:
        blogger_time = self._ToBlogTime(time.gmtime(time.time()))
        self.current_post.published = atom.Published(blogger_time)
      self.feed.entry.append(self.current_post)
      # Add the comments for this post
      for comment in self.comments:
        self.feed.entry.append(comment)

    # Clear the state of the handler to take the next item
    self.categories = set()
    self.current_post = None
    self.comments = []

  def endLink(self, content):
    if self.current_post:
      self.current_post.link.append(atom.Link(href=content, rel='self',
                                              link_type=ATOM_TYPE))
      self.current_post.link.append(atom.Link(href=content, rel='alternate',
                                              link_type=HTML_TYPE))
    else:
      self.feed.link.append(atom.Link(href=content, rel='self',
                                              link_type=ATOM_TYPE))
      self.feed.link.append(atom.Link(href=content, rel='alternate',
                                              link_type=HTML_TYPE))

  def endCreator(self, content):
    if self.current_post:
      self.current_post.author.append(atom.Author(atom.Name(text=content)))

  def endCategory(self, content):
    # Skip over the default uncategorized category
    if content != 'Uncategorized':
      self.categories.add(content)

  def endPost_Type(self, content):
    if content != 'post':
      self.current_post = None

  def endPost_Id(self, content):
    if self.current_post:
      self.current_post.id = atom.Id('post-' + content)

  def endEncoded(self, content):
    if self.current_post:
      content = self.TranslateContent(content)
      self.current_post.content = atom.Content('html', text=content)

  def endPost_Date(self, content):
    if (self.current_post and not self.current_post.published and
        content[:4] != '0000'):
      blogger_time = self._ToBlogTime(self._WordpressDateToTime(content))
      self.current_post.published = atom.Published(blogger_time)

  def endPost_Date_Gmt(self, content):
    self.endPost_Date(content)

  def endStatus(self, content):
    if self.current_post and content == 'draft':
      self.current_post.control = atom.Control(atom.Draft('yes'))

  def startComment(self):
    if not self.current_post:
      return

    # Create the comment entry
    self.comments.insert(0, gdata.GDataEntry())
    # Specify the entry as a comment
    self.comments[0].category.append(atom.Category(scheme=CATEGORY_KIND,
                                                   term=COMMENT_KIND))
    # Point the comment to the post that it is a comment for
    post_id = self.current_post.id.text
    self.comments[0].extension_elements.append(InReplyTo(post_id))
    # Make a link to the comment, which actually points to the original post
    self.comments[0].link.append(self.current_post.link[0])

  def endComment_Id(self, content):
    if self.comments:
      post_id = self.current_post.id.text
      self.comments[0].id = atom.Id('%s.comment-%s' % (post_id, content))

  def endComment_Author(self, content):
    if self.comments:
      self.comments[0].author.append(atom.Author(atom.Name(text=content)))

  def endComment_Author_Email(self, content):
    if self.comments and self.comments[0].author:
      self.comments[0].author[0].email = atom.Email(text=content)

  def endComment_Author_Url(self, content):
    if (self.comments and self.comments[0].author and
        content and content != 'http://'):
      self.comments[0].author[0].uri = atom.Uri(text=content)

  def endComment_Content(self, content):
    if self.comments:
      content = self.TranslateContent(content)
      if content:
        self.comments[0].content = atom.Content('html', text=content)

  def endComment_Date(self, content):
    if (self.comments and not self.comments[0].published and
        content[:4] != '0000'):
      blogger_time = self._ToBlogTime(self._WordpressDateToTime(content))
      self.comments[0].published = atom.Published(blogger_time)

  def endComment_Date_Gmt(self, content):
    self.endComment_Date(content)


  ###################################
  # Helper methods
  ###################################

  def TranslateContent(self, content):
    """Translates the content from Wordpress pseudo-HTML to HTML for Blogger.

    Currently transforms the tags for videos and converts line breaks to
    HTML <br/> tags.

    Args:
      content: The content of a post or comment.
    Returns:
      The transformed content suitable for Blogger.
    """
    if not content:
      return ''

    # This is a bit of a mystery, but sometime the wordpress export is littered
    # with these two unicode characters that are supposed to be whitespace.
    # This removes them (until a known reason for their appearance is uncovered).
    if content.find(u"\u00AC\u2020"):
      content = content.replace(u"\u00AC\u2020", '')

    # Substitute video targets to their HTML equivalent
    content = WP_YOUTUBE_RE.subn(EMBED_YOUTUBE_FMT, content)[0]
    content = WP_GOOGLEVIDEO_RE.subn(EMBED_GOOGLEVIDEO_FMT, content)[0]
    content = WP_DAILYMOTION_RE.subn(EMBED_DAILYMOTION_FMT, content)[0]
    # Then change newlines not preceeded by a <br/> tag to a <br/> tag.
    content = NORMALIZE_BREAKS_RE.subn('<br/>', content)[0]
    return content

  def GetPostPublishedDate(self, post):
    """Performs a best-effort search for the post date.

    Wordpress sometimes outputs dates with no time (e.g. 0000-00-00 00:00:00)
    so this method takes the approach of looking in multiple places for
    a date that's non-zero.  If none can be found, the published date is set
    for the beginning of the Unix epoch (for lack of something better).

    Args:
      post: A WXR element containing a post.
    Returns:
      The string containing the post's publish time.
    """
    return self._GetPublishTime(post,
                                ['wp:post_date_gmt', 'wp:post_date'])

  def GetCommentPublishedDate(self, comment):
    """Performs a best-effort search for the comment publish date.

    Args:
      comment: A WXR element containing a comment.
    Returns:
      The string containing the comment's publish time.
    """
    return self._GetPublishTime(comment,
                                ['wp:comment_date_gmt', 'wp:comment_date'])

  def Find(self, elem, name):
    """Finds a text child node of WXR document with the given element name.

    Args:
      elem:  The parent WXR element.
      name:  The name of the child element to find.
    Returns:
      The text of the child element, if found, otherwise the empty string.
    """
    result = elem.find(name)
    if not result:
      return ''
    return result.string

  def _GetPublishTime(self, element, time_child_list):
    """Helper method that searches multiple elements for a date/time string.

    Args:
      element: The parent WXR element from which to search for the date
      time_child_list:  A list of strings for child elements to examine for the
                        date/time.
    Returns:
      The string containing the date and time, if found.  Otherwise,
      the date of the beginning of the Unix epoch.
    """
    published_time = None
    for time_child in time_child_list:
      published_time = self.Find(element, time_child)
      if published_time[0:4] == '0000':
        published_time = None
        break
    if not published_time:
      # Set the blog time to the date of this translation.  This will at least
      # get the posts to bubble to the top of the blogger import queue and
      # should be noticable by the user.
      return self._ToBlogTime(time.gmtime(time.time()))
    return self._ToBlogTime(self._WordpressDateToTime(published_time))

  def _ToBlogTime(self, time_tuple):
    """Converts a time struct to a Blogger time/date string."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time_tuple)

  def _WordpressPubDateToTime(self, wp_date):
    """Converts the text of a Wordpress time/date string to a time struct."""
    return time.strptime(wp_date[:-6], '%a, %d %b %Y %H:%M:%S')

  def _WordpressDateToTime(self, wp_date):
    """Converts the text of a Wordpress time/date string to a time struct."""
    return time.strptime(wp_date, '%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print 'Usage: %s <wordpress_export_file>' % os.path.basename(sys.argv[0])
    print
    print ' Outputs the converted Blogger export file to standard out.'
    sys.exit(-1)
    
  wp_xml_file = open(sys.argv[1])
  wp_xml_doc = wp_xml_file.read()
  translator = Wordpress2Blogger()
  translator.Translate(wp_xml_doc, sys.stdout)
  wp_xml_file.close()
