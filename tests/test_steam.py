import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from retrofy import steam

class Assertions(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,15,15,0,tzinfo=dt.timezone.utc)
        self.callback='http://127.0.0.1:12345/secret/callback'
        self.params={'openid.ns':steam.NS,'openid.mode':'id_res','openid.op_endpoint':steam.OPENID,
            'openid.claimed_id':'https://steamcommunity.com/openid/id/76561198000000000',
            'openid.identity':'https://steamcommunity.com/openid/id/76561198000000000',
            'openid.return_to':self.callback,'openid.response_nonce':'2026-10-15T15:00:00Zunique',
            'openid.assoc_handle':'test','openid.signed':'op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle','openid.sig':'test'}
    def test_identity_shape(self):
        self.assertEqual(steam.identity_fields(self.params,self.callback,self.now),'76561198000000000')
        for key,value in [('openid.op_endpoint','https://evil.invalid/'),('openid.return_to',self.callback+'x'),
            ('openid.identity','https://steamcommunity.com/openid/id/76561198000000001'),
            ('openid.claimed_id','https://steamcommunity.com.evil.invalid/openid/id/76561198000000000'),
            ('openid.signed','identity'),('openid.response_nonce','2026-10-15T14:00:00Zold'),('openid.mode','cancel')]:
            with self.subTest(key=key),self.assertRaises(steam.SteamError):
                steam.identity_fields(dict(self.params,**{key:value}),self.callback,self.now)
    def test_signature_is_mandatory(self):
        # Mocks prove verifier behavior, not a real successful Steam sign-in.
        with patch.object(steam,'identity_fields',return_value='76561198000000000'),patch.object(steam,'valve',return_value='ns:'+steam.NS+'\nis_valid:false\n'):
            with self.assertRaises(steam.SteamError): steam.verify_identity(self.params,self.callback)
        with patch.object(steam,'identity_fields',return_value='76561198000000000'),patch.object(steam,'valve',return_value='ns:'+steam.NS+'\nis_valid:true\n') as remote:
            self.assertEqual(steam.verify_identity(self.params,self.callback),'76561198000000000')
            self.assertIn(b'check_authentication',remote.call_args[0][1])
    def test_only_valve_can_receive_requests(self):
        for url in ['https://evil.invalid','https://api.steampowered.com.evil.invalid/','http://steamcommunity.com/openid/login']:
            with self.assertRaises(steam.SteamError): steam.valve(url)

class Library(unittest.TestCase):
    def test_private_is_not_empty(self):
        for response in [{}, {'response':{}},[],{'response':{'game_count':1,'games':[]}}]:
            with self.assertRaises(steam.SteamError):steam.normalize_library(response,'76561198000000000')
        self.assertEqual(steam.normalize_library({'response':{'game_count':0}},'76561198000000000')['games'],[])
    def test_no_compatibility_or_rights_inferred(self):
        d={'response':{'game_count':1,'games':[dict(appid=413150,name='Stardew Valley',playtime_forever=15)]}}
        result=steam.normalize_library(d,'76561198000000000')
        self.assertEqual(result['games'][0]['compatibility'],'unassessed')
        self.assertFalse(result['files_accessed']);self.assertFalse(result['adaptation_rights_verified'])
        d['response']['games']*=2;d['response']['game_count']=2
        with self.assertRaises(steam.SteamError):steam.normalize_library(d,'76561198000000000')
    def test_key_not_saved_and_invalid_key_never_sent(self):
        with patch.object(steam,'valve') as remote:
            with self.assertRaises(steam.SteamError):steam.fetch_library('76561198000000000','bad')
            remote.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'account.json';steam.private_json(p,{'steamid':'76561198000000000'})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):steam.private_json(p,{})
            self.assertEqual(json.loads(p.read_text())['steamid'],'76561198000000000')

class LocalHTTP(unittest.TestCase):
    def setUp(self):
        import io
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.session=steam.LinkSession(Path(self.tmp.name)/'new')
        self.session.base='http://127.0.0.1:12345'
        self.handler=steam.handler_for(self.session).__new__(steam.handler_for(self.session))
        self.handler.path=self.session.root+'/sync'
        self.handler.headers={'Host':'127.0.0.1:12345','Origin':self.session.base,'Content-Type':'application/x-www-form-urlencoded'}
        self.status=[];self.handler.send=lambda status,*args,**kwargs:self.status.append(status)
        self.handler.rfile=io.BytesIO()
    def test_rejects_remote_host_and_cross_origin(self):
        self.handler.headers['Host']='evil.invalid';self.handler.do_POST();self.assertEqual(self.status[-1],403)
        self.handler.headers['Host']='127.0.0.1:12345';self.handler.headers['Origin']='https://evil.invalid'
        self.handler.do_POST();self.assertEqual(self.status[-1],403)
    def test_csrf_prevents_api_request(self):
        import io
        body=b'csrf=wrong&key=123';self.handler.rfile=io.BytesIO(body);self.handler.headers['Content-Length']=str(len(body))
        self.session.account='76561198000000000'
        with patch.object(steam,'fetch_library') as fetch:
            self.handler.do_POST();fetch.assert_not_called()
        self.assertFalse(self.session.output.exists());self.assertIn('Invalid form token',self.session.message)
    def test_verified_account_saved_without_assertion(self):
        self.handler.path=self.session.root+'/callback?openid.response_nonce=test'
        with patch.object(steam,'verify_identity',return_value='76561198000000000'):
            self.handler.do_GET()
        self.assertEqual(self.session.account,'76561198000000000')
        saved=json.loads((self.session.output/'account.json').read_text())
        self.assertEqual(set(saved),{'schema','steamid','verified_by'})
        with patch.object(steam,'verify_identity') as verify:
            self.handler.do_GET();verify.assert_not_called()
    def test_session_expires(self):
        self.session.created-=1801;self.handler.path=self.session.root
        self.handler.do_GET();self.assertEqual(self.status[-1],403)
