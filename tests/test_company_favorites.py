import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import config,contacts
class CompanyFavoritesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=patch.object(config,'CONFIG_PATH',Path(self.tmp.name)/'config.json');p.start();self.addCleanup(p.stop)
 def test_favorite_applies_to_all_company_domains_and_survives_reload(self):
  contacts.link_companies(['one.example.com','two.example.com'],'Acme')
  contacts.set_favorite('one.example.com',True)
  self.assertEqual(config.read_config()['favorite_companies'],['company:acme'])
  self.assertEqual(contacts.favorite_key('two.example.com','ACME'),'company:acme')
  contacts.set_favorite('two.example.com',False)
  self.assertEqual(config.read_config()['favorite_companies'],[])
 def test_domain_favorites_do_not_overwrite_company_links(self):
  contacts.link_company('example.com','Acme')
  contacts.set_favorite('unlinked.example.com',True)
  self.assertEqual(config.read_config()['domain_companies'],{'example.com':'Acme'})
  self.assertEqual(config.read_config()['favorite_companies'],['domain:unlinked.example.com'])
  with self.assertRaises(ValueError):contacts.set_favorite('example.com','yes')
