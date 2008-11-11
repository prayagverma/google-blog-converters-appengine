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
    # Write the contents of the feed to a file
    #  import xml.dom.minidom
    #  output_dom = xml.dom.minidom.parseString(str(feed))
    #  outfile.write(output_dom.toprettyxml(encoding="utf-8"))
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
  # Deprecated methods
  ###################################

  def _Translate(self, doc, outfile):
    """Performs the actual translation to a Blogger export format.

    Args:
      doc: The input WXR file as a string
      outfile: The output file that should receive the translated document
    Returns:
      A Blogger export Atom document as a string, or None on error.
    """
    # Decompose the XML into a feed object
    self.feed = BeautifulSoup.RobustXMLParser(doc)

    # Search for one channel element, if it's not found, we don't have
    # a valid WXR wordpress document.
    channel = self.feed.find('channel')
    if not channel:
      raise 'NoChannelFoundException'

    # Set the title of the blog
    feed = gdata.GDataFeed(atom.Title('html',
                                      text=self.Find(self.feed, 'title')))

    # Iterate through the posts/comments and add entries to the feed
    for entry in self.GetEntries():
      feed.entry.append(entry)

    # Write the contents of the feed to a file
    #  import xml.dom.minidom
    #  output_dom = xml.dom.minidom.parseString(str(feed))
    #  outfile.write(output_dom.toprettyxml(encoding="utf-8"))
    outfile.write(str(feed))


  def GetEntries(self):
    """Iterator that extract posts and comments from the wordpress document.

    Yields:
      Atom entries that should be added to the top-level Atom feed object.
    """

    for post in self.feed('item'):
      if self.Find(post, 'wp:post_type') == 'post':

        # Do not duplicate categories and ignore the 'Uncategorized' label
        categories = set([c.string for c in post('category')])
        categories.discard('Uncategorized')

        # Output the post
        yield self.TranslatePost(post, categories)

        # Output the comments for the post
        for comment in post('wp:comment'):
          # Only include approved comments
          approved = self.Find(comment, 'wp:comment_approved')
          if approved == '1':
            entry = self.TranslateComment(post, comment)
            if entry:
              yield entry

  def TranslatePost(self, post, categories):
    """Converts a post from a WXR file to a post in Blogger Atom format.

    Args:
      post: The XML element from the WXR document containing one post
      categories:  A list of strings which are the categories assigned to the
                   post.
      is_draft:  Whether the post is marked as a draft
    Returns:
      An Atom entry containing the same information only in Blogger Atom format.
    """
    entry = gdata.GDataEntry()
    entry.id = atom.Id('post-' + self.Find(post, 'wp:post_id'))

    entry.published = atom.Published(self.GetPostPublishedDate(post))

    entry.category.extend([atom.Category(c, CATEGORY_NS) for c in categories])
    entry.category.append(atom.Category(scheme=CATEGORY_KIND, term=POST_KIND))

    entry.title = atom.Title('html', self.Find(post, 'title'))

    content = self.TranslateContent(self.Find(post, 'content:encoded'))
    entry.content = atom.Content('html', text=content)

    entry.author.append(
        atom.Author(atom.Name(text=self.Find(post, 'dc:creator'))))
    entry.link.append(atom.Link(href=self.Find(post, 'link'),
                                rel='self',
                                link_type=ATOM_TYPE))

    if self.Find(post, 'wp:status') == 'draft':
      entry.control = atom.Control(atom.Draft('yes'))
    return entry

  def TranslateComment(self, post, comment):
    """Converts a comment from a WXR file to a comment in Blogger Atom format.

    Args:
      post: The XML element from the WXR document containing one post
      comment:  The XML element from the WXR document containing a comment for
                the post.
    Returns:
      An Atom entry containing the same information only in Blogger Atom format.
    """

    entry = gdata.GDataEntry()

    post_id = 'post-%s' % self.Find(post, 'wp:post_id')
    entry.id = atom.Id('%s.comment-%s' %
                       (post_id, self.Find(comment, 'wp:comment_id')))

    author_name = self.Find(comment, 'wp:comment_author')
    author_email = self.Find(comment, 'wp:comment_author_email')
    author_uri = self.Find(comment, 'wp:comment_author_url')
    author = atom.Author(atom.Name(text=author_name))
    if author_email:
      author.email = atom.Email(text=author_email)
    if author_uri and author_uri != 'http://':
      author.uri = atom.Uri(text=author_uri)
    entry.author.append(author)

    content = self.TranslateContent(self.Find(comment, 'wp:comment_content'))
    # Blogger doesn't really like comments that are empty
    if not content:
      return None

    entry.content = atom.Content('html', text=content)
    entry.published = atom.Published(self.GetCommentPublishedDate(comment))
    entry.category.append(atom.Category(scheme=CATEGORY_KIND,
                                        term=COMMENT_KIND))
    entry.extension_elements.append(InReplyTo(post_id))
    entry.link.append(atom.Link(href=self.Find(post, 'link'),
                                rel='self',
                                link_type=ATOM_TYPE))
    return entry

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

  def _WordpressDateToTime(self, wp_date):
    """Converts the text of a Wordpress time/date string to a time struct."""
    return time.strptime(wp_date, '%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
  wp_xml_file = open(sys.argv[1])
  wp_xml_doc = wp_xml_file.read()
  translator = Wordpress2Blogger()
  translator.Translate(wp_xml_doc, sys.stdout)
  wp_xml_file.close()
