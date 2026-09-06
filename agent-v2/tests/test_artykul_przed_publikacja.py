"""Both article paths check quality before publishing; deferred text stays saved."""
import ast
import contextlib
from pathlib import Path
import sys
import io
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,'agent-v2')
import artykul_z_puli as article
import stages
import config, db, run, browser

class ArticlePublicationContract(unittest.TestCase):
    def run_case(self, safe):
        calls=[]
        draft={'title':'A title','subtitle':'','body':'A supported sentence. ' * 200}
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys,'argv',['artykul_z_puli.py','--wyslij']))
            for name,value in {'warto_pisac':{'ile_filarow':3,'werdykt':'PISZ'},'write':draft,
                'review':{'sentences':[],'unsupported_facts':[],'summary':'ok'},'ocen_forme':{},
                'poprzednie_teksty':[],'swiezosc_karty':[],'grafika':None,'zapomnij_niewystawiony':None}.items():
                stack.enter_context(patch.object(stages,name,return_value=value))
            stack.enter_context(patch.object(stages,'wstaw_date_zrodel',side_effect=lambda text,card:text))
            stack.enter_context(patch.object(stages,'przygotuj_artykul_do_publikacji',
                side_effect=lambda *a:(calls.append('check') or draft, {'safe_to_post':safe,'nie_sprawdzone':False})))
            saved=stack.enter_context(patch.object(stages,'save',side_effect=lambda *a:(calls.append('save') or Path('draft.md'))))
            publish=stack.enter_context(patch.object(article,'_opublikuj',side_effect=lambda *a:(calls.append('publish') or {'wyslane':True})))
            import gates
            for name in ('deterministic_floors','uwagi_z_formy','artefakty_w_tekscie'):
                stack.enter_context(patch.object(gates,name,return_value=[]))
            code=article._napisz_i_zapisz(None,1,{}, {})
        return code,calls,saved,publish
    def test_bad_article_saved_without_publication(self):
        code,calls,saved,publish=self.run_case(False)
        self.assertEqual(code,article.KOD_ZATRZYMANY);publish.assert_not_called()
        self.assertEqual(calls,['check','save']);self.assertEqual(saved.call_args.args[5],'ZATRZYMANY')
    def test_good_article_checked_saved_published(self):
        code,calls,saved,publish=self.run_case(True)
        self.assertEqual(code,0);publish.assert_called_once()
        self.assertEqual(calls,['check','save','publish'])
    def test_manual_entry_uses_same_preparation(self):
        tree=ast.parse(Path('agent-v2/run.py').read_text(encoding='utf-8'))
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        check=next(n for n in calls if n.func.attr=='przygotuj_artykul_do_publikacji')
        publish=next(n for n in calls if n.func.attr=='wystaw_artykul')
        self.assertLess(check.lineno,publish.lineno)
    def test_manual_publication_failure_is_recorded_as_failed(self):
        topic={'title':'Test title','question':'Test question'}
        draft={'title':'Test title','body':'Supported text. '*200}
        corpus=[{'url':f'https://source{i}.example','host':f'source{i}.example',
                 'class':'PRIMARY','text':'source','excerpts':[],'numbers':[]} for i in range(4)]
        values={'scout':[topic],'feasibility':[{'index':0,'feasible':True}],
                'discovery':corpus,'fetch':corpus,'classify':corpus,'synthesis':{},
                'write':draft,'review':{'sentences':[]},'forma':{}}
        with tempfile.TemporaryDirectory() as directory,contextlib.ExitStack() as stack:
            previous=config.uzyj_katalogu_danych(Path(directory))
            try:
                stack.enter_context(patch.object(sys,'argv',['run.py','--wyslij','--topics','1']))
                stack.enter_context(patch.object(run,'_sygnal_ma_zostawic_slad'))
                stack.enter_context(patch.object(run,'_utf8_stdout'))
                stack.enter_context(patch.object(run.preset,'wymagaj_aktywnego'))
                stack.enter_context(patch.object(run,'odmow_publikacji_z_kopii'))
                stack.enter_context(patch.object(run,'cached',side_effect=lambda stage,*a:values[stage]))
                for name,value in {'pick_topic':(topic,{'depth':'RICH'}),'tematy_do_porownania':[],
                    'ostatnie_notki':[],'warto_pisac':{'werdykt':'PISZ','przekonanie':False,
                        'ile_filarow':0,'filary':{},'powod':'test'},'poprzednie_teksty':[],
                    'swiezosc_karty':[],'przygotuj_artykul_do_publikacji':(draft,{'safe_to_post':True}),
                    'save':Path(directory)/'article.md','grafika':None}.items():
                    stack.enter_context(patch.object(stages,name,return_value=value))
                stack.enter_context(patch.object(stages,'wstaw_date_zrodel',side_effect=lambda text,card:text))
                stack.enter_context(patch.object(browser,'wystaw_artykul',return_value={'wyslane':False,'blad':'not confirmed'}))
                import gates
                for name in ('deterministic_floors','uwagi_z_formy'):
                    stack.enter_context(patch.object(gates,name,return_value=[]))
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(run.main(),1)
                conn=db.connect()
                try:
                    result=conn.execute('SELECT status,stage,note FROM runs ORDER BY id DESC LIMIT 1').fetchone()
                    self.assertEqual((result['status'],result['stage']),('FAILED','publish'))
                    self.assertIn('not confirmed',result['note'])
                finally: conn.close()
            finally: config.przywroc_katalog_danych(previous)

if __name__=='__main__': unittest.main()
