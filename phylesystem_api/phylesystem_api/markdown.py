from . import markdown
import re
import bleach
from bleach.sanitizer import Cleaner

# Define a consistent cleaner to sanitize user input. We need a few
# tags and attributes that are common in our markdown but missing from the
# default Bleach whitelist.
#
# N.B. HTML comments are stripped by default. Non-allowed tags will appear
# "naked" in output, so we can identify any bad actors.
allowed_curation_comment_tags = ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre', 'code']  # any others?
ot_markdown_tags = list(set( bleach.sanitizer.ALLOWED_TAGS + allowed_curation_comment_tags))
# allow hyperlinks with target="_blank"
ot_markdown_attributes = {}
ot_markdown_attributes.update(bleach.sanitizer.ALLOWED_ATTRIBUTES)
ot_markdown_attributes['a'].append('target')
ot_cleaner = Cleaner(tags=ot_markdown_tags, attributes=ot_markdown_attributes)

def _markdown_to_html(markdown_src='', open_links_in_new_window=False):
    extensions = ['mdx_linkify', ]
    html = markdown.markdown(markdown_src, extensions=extensions, )
    # NB - This is clumsy, but seems impossible to do with a second extension
    # like `markdown-link-attr-modifier`
    if open_links_in_new_window:
        html = re.sub(r' href=',
                      r' target="_blank" href=',
                      html)
    # scrub HTML output with bleach
    html = ot_cleaner.clean(html)
    return html
