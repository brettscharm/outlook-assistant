"""Guard common navigation and form regressions without a browser dependency."""
import unittest
from pathlib import Path
from html.parser import HTMLParser

class Page(HTMLParser):
    def __init__(self,source):
        super().__init__();self.ids=[];self.links=[];self.views=[];self.scripts=[];self.feed(source)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if 'aria-controls' in a:self.links.extend(a['aria-controls'].split())
        if 'data-view' in a:self.views.append(a['data-view'])
        if tag=='script' and 'src' in a:self.scripts.append(a['src'])

class UIStructureTests(unittest.TestCase):
    def test_navigation_targets_exist_and_ids_are_unique(self):
        root=Path(__file__).resolve().parents[1]/'outlook_plugin/static'
        page=Page((root/'index.html').read_text())
        self.assertEqual(len(page.ids),len(set(page.ids)))
        for target in page.views+page.links:self.assertIn(target,page.ids)
        for script in page.scripts:self.assertTrue((root/script.rsplit('/',1)[-1].split('?')[0]).is_file(),script)
