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
import sys

__author__ = ''


###########################
# Translation class
###########################


class IGoogle2Opml(object):
  """Performs the translation of an iGoogle GadgetTabML file into OPML."""

  def __init__(self, doc):
    """Constructs a translator.

    Args:
      doc: The iGoogleGadgetTabML file as a string
    """
    self.doc = doc
    
  def Translate(self):
    """Performs the translation process.

    Returns:
    """
    pass

if __name__ == '__main__':
  if len(sys.argv) > 1:
    in_file = open(sys.argv[1])
    in_file_doc = in_file.read()
    translator = IGoogle2Opml(in_file_doc)
    print translator.Translate()
    in_file.close()
  else:
    print "Usage: %s [file_to_transform]" % sys.argv[0]
