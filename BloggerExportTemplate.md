Here is an example of a Blogger export file with one post and one comment to that post.  Additional posts/comments are added as new `<entry>` elements to the top-level `<feed>` element.  If you do not require comments, just create a list of blog post entries.  All variable elements are in UPPERCASE and are defined below the example:

```
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:thr="http://purl.org/syndication/thread/1.0">
  <id>new-blog-import</id>
  <published>TIMESTAMP</published>
  <title type="text">TITLE</title>
  <link rel="http://schemas.google.com/g/2005#feed" type="application/atom+xml" href="ORIGINAL_URL"/>
  <link rel="self" type="application/atom+xml" href="ORIGINAL_URL"/>
  <author>
    <name>AUTHOR_NAME</name>
  </author>
  <generator version="7.00" uri="http://www.blogger.com">Blogger</generator>

  <-- A blog post entry -->
  <entry>
    <id>tag:blogger.com,1999:blog-0.post-POST_IDENTIFIER</id>
    <category scheme="http://schemas.google.com/g/2005#kind" 
              term="http://schemas.google.com/blogger/2008/kind#post"/>
    <published>TIMESTAMP</published>
    <title type="text">POST_TITLE</title>
    <content type="html">POST_CONTENT</content>
    <author>
      <name>AUTHOR_NAME</name>
    </author>
  </entry>

  <-- A comment to the blog post entry -->
  <entry>
    <id>tag:blogger.com,1999:blog-0.post-POST_IDENTIFIER.comment-COMMENT_IDENTIFIER</id>
    <category scheme="http://schemas.google.com/g/2005#kind" 
              term="http://schemas.google.com/blogger/2008/kind#comment"/>
    <thr:in-reply-to href="http://blogName.blogspot.com/2007/04/first-post.html" 
                     ref="tag:blogger.com,1999:blog-0.post-postID" 
                     type="text/html"/>
    <published>TIMESTAMP</published>
    <title type="text">COMMENT_TITLE</title>
    <content type="html">COMMENT_TEXT</content>
    <author>
      <name>COMMENT_AUTHOR_NAME</name>
    </author>
  </entry>
</feed>
```

**Variables**
  * TIMESTAMP - The date of the blog, post, or comment, in the form `2008-10-26T18:00:00.000Z` (docs [here](http://www.atomenabled.org/developers/syndication/atom-format-spec.php#date.constructs))
  * POST\_IDENTIFIER - A unique identifier for this new post
  * POST\_TITLE - The title of the post
  * POST\_TEXT - The actual text of the post
  * AUTHOR\_NAME - The name of the author for this post
  * COMMENT\_IDENTIFIER - A unique identifier for this comment to the post
  * COMMENT\_TITLE - The title to the post, or the comment if there is no title.
  * COMMENT\_TEXT - The actual text of the comment
  * COMMENT\_AUTHOR\_NAME - The author of the comment

There is more information on Atom format that this export file is based on in the documentation for the [Blogger GData API](http://code.google.com/apis/blogger/docs/2.0/reference.html#LinkCommentsToPosts).