import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import config
from outlook_plugin.contacts import group_contacts,link_company,normalize_domain

class ContactTests(unittest.TestCase):
    def test_groups_exact_domains_and_deduplicates_senders(self):
        rows=[{'from':{'name':'Ann','address':'ANN@EXAMPLE.COM'}},{'sender':'Ann <ann@example.com>'},{'sender':'Ben <ben@sub.example.com>'},{'sender':'Invalid <not-an-email>'}]
        groups=group_contacts(rows,{'example.com':'Example Co'})
        self.assertEqual(len(groups),2)
        main=next(g for g in groups if g['domain']=='example.com')
        self.assertEqual(main['company'],'Example Co');self.assertEqual(len(main['contacts']),1)
        self.assertEqual(main['contacts'][0]['message_count'],2)
        self.assertEqual(main['contacts'][0]['name'],'Ann')
    def test_links_persist_without_overwriting_key_context_or_other_links(self):
        with tempfile.TemporaryDirectory() as d,patch.object(config,'CONFIG_PATH',Path(d)/'config.json'):
            config.update_config({'bob_api_key':'secret','user_context':{'accounts':'Example Co'}})
            link_company('EXAMPLE.COM',' Example Co ');link_company('example.org','Other')
            cfg=config.read_config();self.assertEqual(cfg['bob_api_key'],'secret');self.assertEqual(cfg['user_context']['accounts'],'Example Co')
            self.assertEqual(cfg['domain_companies']['example.com'],'Example Co')
            link_company('example.com','')
            self.assertEqual(config.read_config()['domain_companies'],{'example.org':'Other'})
            self.assertEqual(config.CONFIG_PATH.stat().st_mode&0o777,0o600)
    def test_reject_invalid_domains_and_company_values(self):
        for domain in ['example..com','https://example.com','a@b.com','-example.com','com']:
            with self.assertRaises(ValueError):normalize_domain(domain)
        self.assertEqual(normalize_domain(' EXAMPLE.COM. '),'example.com')
        with self.assertRaises(ValueError):link_company('example.com','x'*201)
