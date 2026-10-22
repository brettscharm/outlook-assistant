import unittest
from outlook_plugin.task_owners import resolve_owner,full_name

class OwnerTests(unittest.TestCase):
 def test_header_name_and_address(self):
  message={'sender':'"Smith, Jane" <jane@example.com>','to':[{'name':'Brett Scharmett','address':'brett@ibm.com'}]}
  self.assertEqual(resolve_owner('Jane',message),'Jane Smith <jane@example.com>')
  self.assertEqual(resolve_owner('Brett Scharmett',message),'Brett Scharmett <brett@ibm.com>')
 def test_ambiguous_first_names_not_matched(self):
  message={'sender':'Jane Smith <jane@example.com>','cc':[{'name':'Jane Jones','address':'jones@example.com'}]}
  self.assertEqual(resolve_owner('Jane',message),'Jane')
 def test_unknown_name_not_invented(self):
  self.assertEqual(resolve_owner('Sam',{'sender':'Pat <pat@example.com>'}),'Sam')
  self.assertEqual(full_name('Smith, Jane'),'Jane Smith')
