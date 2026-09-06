"""Unsupported facts are deferred; input changes invalidate cached work."""
import json
import argparse
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import config, db, stages, run, browser, result_cache


class QualityContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=config.uzyj_katalogu_danych(pathlib.Path(self.temp.name))
        self.conn=db.connect();self.rid=db.start_run(self.conn,'quality')
    def tearDown(self):
        self.conn.close();config.przywroc_katalog_danych(self.old);self.temp.cleanup()
    def audit(self,data):
        with patch.object(stages.llm,'call',return_value=json.dumps(data)):
            return stages.zweryfikuj(self.conn,self.rid,'Text','Context')
    def test_nonnumeric_fact_requires_support(self):
        result=self.audit({'claims':[{'claim':'Resale is permitted','status':'unverified'}]})
        self.assertFalse(result['safe_to_post']);self.assertEqual(len(result['zarzuty']),1)
    def test_invalid_schema_and_no_source_do_not_pass(self):
        for value in ({},{'claims':None},{'claims':[{'claim':'x','status':'confirmed'}]}):
            self.assertFalse(self.audit(value)['safe_to_post'])
    def test_check_failure_is_distinct_from_confirmation(self):
        with patch.object(stages.llm,'call',side_effect=RuntimeError('offline failure')):
            result=stages.zweryfikuj(self.conn,self.rid,'Text')
        self.assertTrue(result['nie_sprawdzone']);self.assertFalse(result['safe_to_post'])
    def test_supported_fact_and_pure_opinion_pass(self):
        self.assertTrue(self.audit({'claims':[]})['safe_to_post'])
        self.assertTrue(self.audit({'claims':[{'claim':'x','status':'confirmed','url':'https://example.org/source'}]})['safe_to_post'])
    def test_repair_cannot_replace_one_bad_fact_with_another(self):
        original={'zarzuty':[{'claim':'old wrong fact','status':'refuted'}]}
        replacement={'zarzuty':[{'claim':'new wrong fact','status':'refuted'}], 'safe_to_post':False}
        stages._NAPRAW_ZUZYTE.clear()
        with patch.object(stages.llm,'call',return_value=json.dumps({'text':'A changed draft with a different factual error.'})), \
             patch.object(stages,'zweryfikuj',return_value=replacement):
            self.assertIsNone(stages.napraw_obalone(self.conn,self.rid,'Original text',original,
                kontekst='context',min_slow=1,max_slow=50,etap='naprawa',zapora=lambda x:''))
        records=list((pathlib.Path(self.temp.name)/'repair-attempts').glob('*.json'))
        self.assertEqual(len(records),1)
        saved=json.loads(records[0].read_text(encoding='utf-8'))['value']
        self.assertFalse(saved['eligible'])
        self.assertEqual(saved['candidate'],'A changed draft with a different factual error.')
        self.assertEqual(saved['audit'],replacement)
    def test_article_with_failed_audit_is_not_ready(self):
        draft={'title':'Title','body':'Body'}
        with patch.object(stages,'zweryfikuj',return_value={'safe_to_post':False,'nie_sprawdzone':True}), \
             patch.object(stages,'napraw_obalone') as repair:
            _,audit=stages.przygotuj_artykul_do_publikacji(self.conn,self.rid,draft,{}, {})
        self.assertFalse(audit['safe_to_post']);repair.assert_not_called()
    def test_repair_receives_every_challenged_claim(self):
        audit={'zarzuty':[{'claim':f'Challenged fact {i}','status':'unverified'} for i in range(8)]}
        stages._NAPRAW_ZUZYTE.clear()
        with patch.object(stages.llm,'call',return_value=json.dumps({'text':'A corrected draft.'})) as call, \
             patch.object(stages,'zweryfikuj',return_value={'safe_to_post':True,'zarzuty':[]}):
            result=stages.napraw_obalone(self.conn,self.rid,'Original draft',audit,
                kontekst='context',min_slow=1,max_slow=30,etap='naprawa',zapora=lambda text:'')
        self.assertIsNotNone(result)
        prompt=call.call_args.args[2]
        for i in range(8): self.assertIn(f'Challenged fact {i}',prompt)
    def test_review_requires_exact_coverage(self):
        valid={'index':1,'class':'FACT','supported':True}
        for decisions in ([valid], [valid,valid], [valid,None],
                          [valid,{'index':2,'class':'FACT','supported':'yes'}]):
            with self.subTest(decisions=decisions),patch.object(stages.llm,'call',
                    return_value=json.dumps({'sentences':decisions})):
                with self.assertRaises(ValueError):
                    stages.review(self.conn,self.rid,{}, {'body':'First claim. Second claim.'})
    def test_review_reconstructs_text_and_checks_inference_premise(self):
        decisions=[{'index':2,'class':'INFERENCE','supported':False,'why':'premise missing'},
                   {'index':1,'class':'FACT','supported':True}]
        with patch.object(stages.llm,'call',return_value=json.dumps({'sentences':decisions})):
            result=stages.review(self.conn,self.rid,{}, {'body':'First claim. Second claim.'})
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['unsupported_facts'][0]['text'],'Second claim.')
        self.assertEqual(result['sentences'][1]['text'],'First claim.')
    def test_cache_tracks_inputs_and_reuses_identical_input(self):
        count=[]
        def producer(topic):
            # Side effects excluded from the closure; they are not cache inputs.
            return lambda: {'topic':topic}
        with patch.object(run,'CACHE_DIR',pathlib.Path(self.temp.name)/'cache'):
            a=run.cached('scout',producer('A'),False)
            b=run.cached('scout',producer('B'),True)
            self.assertEqual(a,{'topic':'A'});self.assertEqual(b,{'topic':'B'})
            files=list((pathlib.Path(self.temp.name)/'cache').glob('*.json'))
            self.assertEqual(len(files),2)
            self.assertEqual(run.cached('scout',producer('B'),True),b)
    def test_expired_or_corrupt_cache_is_not_used(self):
        path=pathlib.Path(self.temp.name)/'cache.json'
        path.write_text('{broken',encoding='utf-8');self.assertIsNone(result_cache.read(path,100))
        path.write_text(json.dumps({'at':0,'value':'old'}),encoding='utf-8');self.assertIsNone(result_cache.read(path,100))
    def test_cache_enable_flag_does_not_invalidate_saved_inputs(self):
        args=argparse.Namespace(topics=3,use_cache=False,stop_after='scout',wyslij=False)
        def produce():
            return {'topics':args.topics}
        with patch.object(run,'CACHE_DIR',pathlib.Path(self.temp.name)/'cache'):
            first=run.cached('scout',produce,False)
            args.use_cache=True;args.stop_after=None;args.wyslij=True
            with patch.object(result_cache,'write') as write:
                self.assertEqual(run.cached('scout',produce,True),first)
                write.assert_not_called()


class Page:
    def __init__(self,context): self.context=context
    def goto(self,*a,**k): pass
    def evaluate(self,*a): return self.context.user
    def close(self): pass


class Context:
    def __init__(self,handle): self.user={'id':42,'handle':handle};self.cookie='session-a';self.reads=0
    def cookies(self,*a): return [{'name':browser.SESSION_COOKIE,'domain':'.substack.com','value':self.cookie}]
    def new_page(self): self.reads+=1;return Page(self)


class AccountContract(unittest.TestCase):
    def setUp(self): browser._POTWIERDZENIE_KONTA=None
    def test_public_profile_cannot_authenticate_wrong_session(self):
        context=Context('someone-else')
        with patch.object(browser,'api_json',return_value={'id':42,'handle':browser.PROFIL_HANDLE}):
            with self.assertRaises(browser.NieToKonto): browser.wymagaj_wlasciwego_konta(Page(context))
    def test_session_change_invalidates_cached_identity(self):
        context=Context(browser.PROFIL_HANDLE)
        with patch.object(browser,'api_json',return_value={'id':42,'handle':browser.PROFIL_HANDLE}):
            browser.wymagaj_wlasciwego_konta(Page(context));browser.wymagaj_wlasciwego_konta(Page(context))
            self.assertEqual(context.reads,1)
            context.cookie='session-b';context.user={'id':13,'handle':'different'}
            with self.assertRaises(browser.NieToKonto): browser.wymagaj_wlasciwego_konta(Page(context))
    def test_unknown_identity_is_not_permission(self):
        context=Context(browser.PROFIL_HANDLE);context.user=None
        with self.assertRaises(browser.KontoNiepotwierdzone): browser.wymagaj_wlasciwego_konta(Page(context))
    def test_stable_ids_must_match(self):
        context=Context(browser.PROFIL_HANDLE)
        with patch.object(browser,'api_json',return_value={'id':43,'handle':browser.PROFIL_HANDLE}):
            with self.assertRaises(browser.NieToKonto): browser.wymagaj_wlasciwego_konta(Page(context))


if __name__=='__main__': unittest.main()
