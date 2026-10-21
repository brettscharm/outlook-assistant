import json,unittest
from unittest.mock import Mock,patch
from outlook_plugin import mcp_server as m
class MCPTests(unittest.TestCase):
 def setUp(self):self.engine=Mock()
 def request(self,method,params=None):return m.dispatch({'jsonrpc':'2.0','id':7,'method':method,'params':params or {}},self.engine)
 def test_initialize_notifications_and_tools(self):
  result=self.request('initialize',{'protocolVersion':'2025-06-18'})['result']
  self.assertEqual(result['protocolVersion'],'2025-06-18')
  self.assertIsNone(m.dispatch({'jsonrpc':'2.0','method':'notifications/initialized'},self.engine))
  tools=self.request('tools/list')['result']['tools']
  self.assertFalse(next(t for t in tools if t['name']=='create_task')['annotations']['readOnlyHint'])
  self.assertTrue(next(t for t in tools if t['name']=='search_mail')['annotations']['readOnlyHint'])
 def test_limits_unknown_tools_and_parameters(self):
  for args in [{'limit':0},{'limit':101},{'limit':True},{'offset':-1},{'query':[]},{'secret':True}]:
   self.assertTrue(self.request('tools/call',{'name':'search_mail','arguments':args})['result']['isError'])
  self.assertTrue(self.request('tools/call',{'name':'send_email'})['result']['isError'])
 def test_task_pagination_and_completed_filter(self):
  with patch('outlook_plugin.tasks.load_tasks',return_value={'my_tasks':[{'id':'1'},{'id':'2','completed':True}],'others_tasks':[]}):
   result=m.handle_tool_call(self.engine,'list_tasks',{})
   self.assertEqual(result['total'],1)
   self.assertEqual(m.handle_tool_call(self.engine,'list_tasks',{'include_completed':True,'offset':1})['items'][0]['id'],'2')
 def test_mail_uses_filtered_engine_and_missing_body_is_error(self):
  self.engine.get_emails.return_value=[{'id':str(i)} for i in range(4)]
  result=m.handle_tool_call(self.engine,'search_mail',{'limit':2,'offset':1,'query':'renewal'})
  self.assertEqual(result['next_offset'],3)
  self.engine.get_emails.assert_called_once_with(folder='all',limit=4,search_term='renewal')
  self.engine.get_email_details.return_value=None
  self.assertTrue(self.request('tools/call',{'name':'read_email','arguments':{'message_id':'blocked'}})['result']['isError'])
 def test_calendar_uses_current_cache(self):
  with patch('outlook_plugin.calendar_cache.snapshot',return_value={'events':[{'id':'a'}],'checked':1}) as snapshot:
   data=m.handle_tool_call(self.engine,'list_calendar',{'days':7})
   snapshot.assert_called_once_with(days=7)
   self.assertIn('not a free/busy',data['coverage'])
 def test_connection_has_no_credentials(self):
  config=m.connection_info()['config']['mcpServers']['outlook-assistant']
  self.assertEqual(set(config),{'command','args'})
