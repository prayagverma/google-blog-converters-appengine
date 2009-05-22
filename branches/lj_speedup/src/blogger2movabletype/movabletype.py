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

############################
# Wordpress XML objects
############################


class MovableTypeExport(object):

  def __init__(self):
    # List of MovalbeTypePost
    self.posts = []

  def ToString(self):
    retval = ''
    # Serialize all of the posts
    for post in self.posts:
      retval += post.ToString()
    return retval


class MovableTypePost(object):

  def __init__(self):
    self.author = None
    self.title = None
    self.status = None
    self.allow_comments = 1
    self.convert_breaks = 0
    self.allow_pings = 1
    self.primary_category = ''
    self.categories = []
    self.date = None
    self.body = None
    self.comments = [] 

  def ToString(self):
    retval = ''
    retval += 'AUTHOR: %s\n' % self.author
    retval += 'TITLE: %s\n' % self.title
    retval += 'BASENAME: %s\n' % self.title
    retval += 'STATUS: %s\n' % self.status
    retval += 'ALLOW COMMENTS: %s\n' % self.allow_comments
    retval += 'CONVERT BREAKS: %s\n' % self.convert_breaks
    retval += 'ALLOW PINGS: %s\n' % self.allow_pings
    retval += 'PRIMARY CATEGORY: %s\n' % self.primary_category
    for category in self.categories:
      retval += 'CATEGORY: %s\n' % category
    retval += 'DATE: %s\n' % self.date
    #retval += 'TAGS: \n'
    retval += '-' * 5 + '\n'
    retval += 'BODY:\n%s\n' % self.body
    retval += '-' * 5 + '\n'
    retval += 'EXTENDED BODY:\n\n'
    retval += '-' * 5 + '\n'
    retval += 'EXCERPT:\n\n'
    retval += '-' * 5 + '\n'
    retval += 'KEYWORDS:\n\n'
    for comment in self.comments:
      retval += '-' * 5 + '\n'
      retval += '\nCOMMENT:\n%s\n' % comment.ToString()
      retval += '-' * 5 + '\n'
    retval += '\n\n'
    retval += '-' * 8 + '\n'

    return retval

class MovableTypeComment(object):

  def __init__(self):
    self.author = None
    self.email = ''
    self.ip = ''
    self.url = ''
    self.date = None
    self.body = None

  def ToString(self):
    retval = ''
    retval += 'AUTHOR: %s\n' % self.author 
    retval += 'EMAIL: %s\n' % self.email 
    retval += 'IP: %s\n' % self.ip
    retval += 'URL: %s\n' % self.url
    retval += 'DATE: %s\n' % self.date
    retval += self.body
    return retval
