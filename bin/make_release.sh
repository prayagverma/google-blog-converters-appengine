#!/bin/sh

# FILE:     make_release.sh
# PURPOSE:  Shell script for creating a downloadable version of the
#           entire project.
#
# USAGE:    make_release <version_tag>
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
DOWNLOAD_NAME=google-blog-converters-$1
echo "Copying download contents"
rm -rf /tmp/${DOWNLOAD_NAME}
mkdir /tmp/${DOWNLOAD_NAME}
cp -rv ${PROJ_DIR}/* /tmp/${DOWNLOAD_NAME}
echo "Deleting Subversion and Pythong cruft"
find /tmp/${DOWNLOAD_NAME} -name "*.pyc" -o -name ".svn" | xargs rm -rf
find /tmp/${DOWNLOAD_NAME} -type l | xargs rm -rf 
echo "Creating the archive"
DOWNLOAD_DIR=`pwd`
cd /tmp 
tar cvfz ${DOWNLOAD_DIR}/${DOWNLOAD_NAME}.tar.gz ${DOWNLOAD_NAME}
rm -rf /tmp/${DOWNLOAD_NAME}

