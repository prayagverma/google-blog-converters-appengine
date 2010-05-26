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

import logging
from xml.etree import ElementTree

__author__ = 'JJ Lueck (jlueck@gmail.com)'

###########################
# Constants
###########################

CONTENT_NS_TAG = 'content'
CONTENT_NS = 'http://purl.org/rss/1.0/modules/content/'
WFW_NS_TAG = 'wfw'
WFW_NS = 'http://wellformedweb.org/CommentAPI/'
DC_NS_TAG = 'dc'
DC_NS = 'http://purl.org/dc/elements/1.1/'
WORDPRESS_NS_TAG = 'wp'
WORDPRESS_NS = 'http://wordpress.org/export/1.0/'
XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'

###########################
# ElementTree modifications
###########################

# This section provides the massive hacks that are necessary to allow
# ElementTree to work correctly with some strange non-standard XML
# requirements that the WordPress parser requires for its export format.

# Define a new node for the ElementTree which is an XML CDATA entity.  It
# is a requirement of the WordPress parser that the content nodes for posts
# and comments be written as CDATA sections.  I've attempted to replace these
# with just XML-escaped data, but the data stays escaped after being imported
# instead of being unescaped by the parser.
def CDataSection(text=''):
  element = ElementTree.Element(CDataSection)
  element.text = text
  return element

# Store a copy of the default (protected) write method for ElementTree
element_tree_write = ElementTree.ElementTree._write

# Create a new default write method that knows about CDATA sections
def write_cdata(obj, file, node, encoding, namespaces):
  """An extension to the ElementTree write function for emitting CDATA sections.

  This method will check to see if a CDATA section is defined, and output its
  value.  If the node being written is not a CDATA section, it falls back to
  the original implementation.
  """
  if node.tag is CDataSection:
    file.write('<![CDATA[%s]]>' % node.text)
  else:
    element_tree_write(obj, file, node, encoding, namespaces)

# Replace the default with our new method
ElementTree.ElementTree._write = write_cdata

# Turn off any encoding of non-UTF to UTF upon output.  All data comes in as
# UTF-8 and will stay that way when given to ElementTree objects.
def no_encode(text, encoding):
  return text

# Replace the default encode method with a dummy method that does no escaping
ElementTree._encode = no_encode

# Finally, the resulting XML MUST be indented for the parser to read everything
# properly.  This method modifies a given ElementTree with whitespace that the
# emitter will use to indent the output.
def indent(elem, level=0):
  i = "\n" + level*"  "
  if len(elem):
    if not elem.text or not elem.text.strip():
      if elem[0].tag is not CDataSection:
        elem.text = i + "  "
    for sub_elem in elem:
      indent(sub_elem, level+1)
    if not elem.tail or not elem.tail.strip():
      elem.tail = i
  else:
    if level and (not elem.tail or not elem.tail.strip()):
      elem.tail = i
  return elem

############################
# Wordpress XML objects
############################


class WordPressObject(object):
  """Top-level class for all WordPress serialization objects.

  Provides an "interface" for the _ToElementTree method which all objects
  should implement, and provides helper methods for adding child objects
  to this object's ElementTree output.
  """

  def _ToElementTree(self):
    """Converts this object into an ElementTree structure.

    This structure is easy to output as XML.
    """
    pass

  def _SubElement(self, parent, tag, text=''):
    """Creates a sub-tree to part of an ElementTree.

    Args:
      parent:  The part of the tree that will receive a child element.
      tag:  The name of the tag on the child element
      text:  Optional text contained in the child element.
    Returns:
      The child element.
    """
    sub = ElementTree.SubElement(parent, tag)
    sub.text = text
    return sub


class WordPressWxr(WordPressObject):
  """The top-level element in a WordPress WXR export document."""

  def __init__(self, version='2.0', channel=None):
    self.version = 'version'
    self.channel = channel

  def WriteXml(self):
    """Returns the serialized XML for this WordPress WXR document."""
    return XML_HEADER + ElementTree.tostring(indent(self._ToElementTree()))

  def _ToElementTree(self):
    root = ElementTree.Element('rss')
    # Write out the namespaces used in the document.
    root.set('version', self.version)
    root.set('xmlns:%s' % CONTENT_NS_TAG, CONTENT_NS)
    root.set('xmlns:%s' % WFW_NS_TAG, WFW_NS)
    root.set('xmlns:%s' % DC_NS_TAG, DC_NS)
    root.set('xmlns:%s' % WORDPRESS_NS_TAG, WORDPRESS_NS)

    if self.channel:
      root.append(self.channel._ToElementTree())
    return root

class Channel(WordPressObject):
  """Each WXR file has one Channel element containing all posts and metadata."""

  def __init__(self, title='', link='', description='', pubDate='',
               generator='http://blogger2wordpress.appspot.com',
               language='en', base_site_url='http://wordpress.com',
               base_blog_url='http://wordpress.com'):
    self.title = title
    self.link = link
    self.description = description
    self.pubDate = pubDate
    self.generator = generator
    self.language = language
    self.base_site_url = base_site_url
    self.base_blog_url = base_blog_url
    self.categories = []
    self.tags = []
    self.items = []

  def _ToElementTree(self):
    # Write out the metadata
    root = ElementTree.Element('channel')
    self._SubElement(root, 'title', self.title)
    self._SubElement(root, 'link', self.link)
    self._SubElement(root, 'pubDate', self.pubDate)
    self._SubElement(root, 'generator', self.generator)
    self._SubElement(root, 'language', self.language)
    self._SubElement(root, '%s:wxr_version' % WORDPRESS_NS_TAG, '1.0')
    self._SubElement(root, '%s:base_site_url' % WORDPRESS_NS_TAG,
                     self.base_site_url)
    self._SubElement(root, '%s:base_blog_url' % WORDPRESS_NS_TAG,
                     self.base_blog_url)

    # Write out the categories assigned to the blog
    for category in self.categories:
      cat_elem = ElementTree.Element('%s:category' % WORDPRESS_NS_TAG)
      self._SubElmement(cat_elem, '%s:category_name' % WORDPRESS_NS_TAG,
                        category)
      self._SubElmement(cat_elem, '%s:category_nicename' % WORDPRESS_NS_TAG,
                        category)
      self._SubElmement(cat_elem, '%s:category_parent' % WORDPRESS_NS_TAG)
      root.append(cat_elem)

    # Write out the tags assigned to the blog.
    for tag in self.tags:
      tag_elem = ElementTree.Element('%s:tag' % WORDPRESS_NS_TAG)
      self._SubElement(tag_elem, '%s:tag_name' % WORDPRESS_NS_TAG, tag)
      self._SubElement(tag_elem, '%s:tag_slug' % WORDPRESS_NS_TAG,
                       tag.replace(' ', '-'))
      root.append(tag_elem)

    # Write out all posts as item elements
    for item in self.items:
      root.append(item._ToElementTree())

    return root


class Item(WordPressObject):
  """Contains one WordPress blog post.

  Can contain metadata about the post, such as category, tags, and status of the
  post, as well as any comments assigned to the post.
  """

  def __init__(self, title='', link='', pubDate='', creator='', guid='',
               description='', content='', post_id='', post_date='',
               comment_status='open', ping_status='open', status='publish',
               post_parent='0', menu_order='0', post_type='post',
               post_password='', blogger_blog='', blogger_author='',
               blogger_permalink=''):
    self.title = title
    self.link = link
    self.pubDate = pubDate
    self.creator = creator
    self.guid = guid
    self.description = description
    self.content = content
    self.post_id = post_id
    self.post_date = post_date
    self.comment_status = comment_status
    self.ping_status = ping_status
    self.status = status
    self.post_parent = post_parent
    self.menu_order = menu_order
    self.post_type = post_type
    self.post_password = post_password
    self.labels = []
    self.comments = []
    self.blogger_blog = blogger_blog
    self.blogger_permalink = blogger_permalink
    self.blogger_author = blogger_author

  def _ToElementTree(self):
    root = ElementTree.Element('item')
    self._SubElement(root, 'title', self.title)
    self._SubElement(root, 'link', self.link)
    self._SubElement(root, 'pubDate', self.pubDate)
    self._SubElement(root, '%s:creator' % DC_NS_TAG, self.creator)
    guid = self._SubElement(root, 'guid', self.guid)
    guid.set('isPermaLink', 'false')
    self._SubElement(root, 'description', self.description)
    self._SubElement(root, '%s:post_id' % WORDPRESS_NS_TAG, self.post_id)
    self._SubElement(root, '%s:post_date' % WORDPRESS_NS_TAG, self.post_date)
    self._SubElement(root, '%s:post_date_gmt' % WORDPRESS_NS_TAG,
                     self.post_date)
    self._SubElement(root, '%s:comment_status' % WORDPRESS_NS_TAG,
                     self.comment_status)
    self._SubElement(root, '%s:ping_status' % WORDPRESS_NS_TAG,
                     self.ping_status)
    self._SubElement(root, '%s:post_name' % WORDPRESS_NS_TAG,
                     self.title.replace(' ', '-'))
    self._SubElement(root, '%s:status' % WORDPRESS_NS_TAG, self.status)
    self._SubElement(root, '%s:post_parent' % WORDPRESS_NS_TAG,
                     self.post_parent)
    self._SubElement(root, '%s:menu_order' % WORDPRESS_NS_TAG,
                     self.menu_order)
    self._SubElement(root, '%s:post_type' % WORDPRESS_NS_TAG,
                     self.post_type)
    self._SubElement(root, '%s:post_password' % WORDPRESS_NS_TAG,
                     self.post_password)

    content = self._SubElement(root, '%s:encoded' % CONTENT_NS_TAG, '')
    content.append(CDataSection(self.content))

    # A label assigned to a post is written out as a "tag" and not a "category."
    for label in self.labels:
      label_elem = self._SubElement(root, 'category', label)
      label_elem.set('domain', 'tag')

    if self.blogger_blog:
      post_meta_elem = ElementTree.Element('%s:postmeta' % WORDPRESS_NS_TAG)
      self._SubElement(post_meta_elem, '%s:meta_key' % WORDPRESS_NS_TAG,
                       'blogger_blog')
      self._SubElement(post_meta_elem, '%s:meta_value' % WORDPRESS_NS_TAG,
                       self.blogger_blog)
      root.append(post_meta_elem)

    if self.blogger_permalink:
      post_meta_elem = ElementTree.Element('%s:postmeta' % WORDPRESS_NS_TAG)
      self._SubElement(post_meta_elem, '%s:meta_key' % WORDPRESS_NS_TAG,
                       'blogger_permalink')
      self._SubElement(post_meta_elem, '%s:meta_value' % WORDPRESS_NS_TAG,
                       self.blogger_permalink)
      root.append(post_meta_elem)

    if self.blogger_author:
      post_meta_elem = ElementTree.Element('%s:postmeta' % WORDPRESS_NS_TAG)
      self._SubElement(post_meta_elem, '%s:meta_key' % WORDPRESS_NS_TAG,
                       'blogger_author')
      self._SubElement(post_meta_elem, '%s:meta_value' % WORDPRESS_NS_TAG,
                       self.blogger_author)
      root.append(post_meta_elem)

    for comment in self.comments:
      root.append(comment._ToElementTree())

    return root


class Comment(WordPressObject):
  """One comment to a blog post.

  Comments are contained within Item elements.
  """

  def __init__(self, comment_id='', author='', author_email='', author_url='',
               author_IP='', date='', content='', approved='1', comment_type='',
               parent='0', user_id=''):
    self.comment_id = comment_id
    self.author = author
    self.author_email = author_email
    self.author_url = author_url
    self.author_IP = author_IP
    self.date = date
    self.content = content
    self.approved = approved
    self.comment_type = comment_type
    self.parent = parent
    self.user_id = user_id

  def _ToElementTree(self):
    root = ElementTree.Element('%s:comment' % WORDPRESS_NS_TAG)
    self._SubElement(root, '%s:comment_id' % WORDPRESS_NS_TAG, self.comment_id)
    self._SubElement(root, '%s:comment_author' % WORDPRESS_NS_TAG, self.author)
    self._SubElement(root, '%s:comment_author_email' % WORDPRESS_NS_TAG,
                     self.author_email)
    self._SubElement(root, '%s:comment_author_url' % WORDPRESS_NS_TAG,
                     self.author_url)
    self._SubElement(root, '%s:comment_author_IP' % WORDPRESS_NS_TAG,
                     self.author_IP)
    self._SubElement(root, '%s:comment_date' % WORDPRESS_NS_TAG, self.date)
    self._SubElement(root, '%s:comment_date_gmt' % WORDPRESS_NS_TAG, self.date)
    self._SubElement(root, '%s:comment_approved' % WORDPRESS_NS_TAG,
                     self.approved)
    self._SubElement(root, '%s:comment_type' % WORDPRESS_NS_TAG,
                     self.comment_type)
    self._SubElement(root, '%s:comment_parent' % WORDPRESS_NS_TAG,
                     self.parent)
    self._SubElement(root, '%s:user_id' % WORDPRESS_NS_TAG,
                     self.user_id)

    content = self._SubElement(root, '%s:comment_content' % WORDPRESS_NS_TAG, '')
    content.append(CDataSection(self.content))

    return root


if __name__ == '__main__':
  wxr = WordPressWxr()
  wxr.channel = Channel()
  wxr.channel.items.append(Item())
  wxr.channel.items[0].comments.append(Comment())
  print wxr.WriteXml()
