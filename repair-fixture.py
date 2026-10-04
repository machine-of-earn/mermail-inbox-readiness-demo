#!/usr/bin/env python3
"""Network-free MCP fixture. Sends are recorded, never delivered or approval-filtered."""
import json,sys,os
from pathlib import Path
base=Path(os.environ['READINESS_FIXTURE_DIR'])
A={'public_id':'mbx-a','email':'new@fixture.invalid','status':'active'}
B={'public_id':'mbx-b','email':'ops@fixture.invalid','status':'active'}
names=['list_workspaces','get_workspace','get_api_credit_usage','get_email_usage','get_workspace_storage','list_mailboxes','get_mailbox','get_mailbox_storage','list_email_domains','list_folders','list_custom_labels','list_task_triagers','send_email','list_emails','get_email']
props={'workspaceId':{'type':'string'},'mailboxId':{'type':'string'},'emailId':{'type':'string'},'query':{'type':'object'},'body':{'type':'object'},'idempotencyKey':{'type':'string'}}
def call(name,args):
 state=json.loads((base/'state.json').read_text()); boxes=[B] if state['changed'] else [A,B]
 rows=[json.loads(x) for x in (base/'calls.jsonl').read_text().splitlines()] if (base/'calls.jsonl').exists() else []
 sends=[x for x in rows if x['name']=='send_email']
 if name=='list_workspaces':out={'workspaces':[{'public_id':'wsp-fixture','name':'Local fixture'}]}
 elif name=='get_workspace':out={'public_id':'wsp-fixture','name':'Local fixture','plan':'free'}
 elif name=='get_api_credit_usage':out={'credits_remaining':100,'credits_used':0}
 elif name=='get_email_usage':out={'emails_sent':len(sends),'emails_received':len(sends),'monthly_limit':200}
 elif name in ['get_workspace_storage','get_mailbox_storage']:out={'used_bytes':0,'limit_bytes':1048576}
 elif name=='list_mailboxes':out={'mailboxes':boxes}
 elif name=='get_mailbox':out=next((x for x in boxes if x['public_id']==args.get('mailboxId')),{'error':'mailbox_unavailable'})
 elif name=='list_email_domains':out={'domains':[]}
 elif name=='list_folders':out={'folders':[{'name':x} for x in ['Inbox','Sent','Drafts']]}
 elif name=='list_custom_labels':out={'labels':[]}
 elif name=='list_task_triagers':out={'triagers':[]}
 elif name=='send_email':out={'email_id':'fixture-message-'+str(len(sends)+1),'status':'queued','fixture_only':True}
 elif name=='list_emails':out={'emails':[{'email_id':'fixture-message-'+str(i+1),'subject':x['arguments'].get('body',{}).get('subject'),'received_at':'2026-10-04T22:00:00Z'} for i,x in enumerate(sends)],'fixture_only':True}
 elif name=='get_email':out={'email_id':args.get('emailId'),'sender_authentication':{'status':'unknown'},'scan_status':'clean','received_at':'2026-10-04T22:00:00Z','fixture_only':True}
 else:out={'error':'unknown_tool'}
 with (base/'calls.jsonl').open('a') as f:f.write(json.dumps({'phase':state['phase'],'name':name,'arguments':args,'result':out})+'\n')
 return out
for line in sys.stdin:
 m=json.loads(line);rid=m.get('id');method=m.get('method')
 if rid is None:continue
 if method=='initialize':out={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'local-readiness-fixture','version':'1'}}
 elif method=='tools/list':out={'tools':[{'name':n,'description':'Local fixture: '+n,'inputSchema':{'type':'object','properties':props}} for n in names]}
 elif method=='tools/call':
  p=m['params'];res=call(p['name'],p.get('arguments',{}));out={'content':[{'type':'text','text':json.dumps(res)}],'isError':bool(res.get('error'))}
 else:out={}
 print(json.dumps({'jsonrpc':'2.0','id':rid,'result':out}),flush=True)
