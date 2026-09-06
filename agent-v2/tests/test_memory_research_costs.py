"""Behavioral regressions for lost ideas, unnecessary research and server pauses."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import db
import stages
import llm
import aktualne_modele
import retry_policy
import call_runtime
import audyt_kosztow


class MemoryResearch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = config.uzyj_katalogu_danych(self.root)
        self.settings = patch.multiple(config, W_TESCIE=True, WOLNO_WOLAC_MODEL=True,
            DRY_RUN=False, KILL_SWITCH=False, DEEPSEEK_API_KEY='offline', ANTHROPIC_API_KEY='offline',
            RUN_LIMIT_USD=5., DAILY_LIMIT_USD=10., TEST_LIMIT_USD=10., MONTHLY_LIMIT_USD=20.,
            PONOWIENIA=2, PONOWIENIE_ODSTEP_S=0, STAN_DZIEDZINY_PYTAJ=True)
        self.settings.start()
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('no network'))
        self.network.start()
        self.paths = patch.multiple(stages, INDEKS_KANDYDATOW=self.root/'index.json')
        self.paths.start()
        self.state_path = patch.object(aktualne_modele, 'PLIK', self.root/'field.json')
        self.state_path.start()
        self.conn = db.connect()
        self.rid = db.start_run(self.conn, 'memory-contract')
        call_runtime.RUN_DEADLINE = None

    def tearDown(self):
        self.conn.close()
        self.state_path.stop(); self.paths.stop(); self.network.stop(); self.settings.stop()
        config.przywroc_katalog_danych(self.previous)
        call_runtime.RUN_DEADLINE = None
        self.temp.cleanup()

    def candidate(self, fact='A named provider changed its metered billing rule today.'):
        return dict(fact=fact, status='nowy', kiedy=db.now(), url='https://example.org/document',
            source_date=datetime.now(timezone.utc).date().isoformat(),
            decision='The provider changed the contract to charge for unused capacity.',
            consequence='Customers pay for capacity that they do not use.',
            wrong_belief='Only used capacity is billed.', actually='The contract includes idle capacity.',
            control_date=datetime.now(timezone.utc).date().isoformat(),
            control_url='https://example.org/current', control_verdict='CONFIRMS',
            control_fact='The current contract still charges for idle capacity.', domain='billing')

    def put(self, items):
        stages._zapisz_indeks(items)

    def note_plan(self, types, promotion=None, writer=None):
        with patch.object(config,'NOTE_MIX_OTHER_DAY',types), \
             patch.object(stages,'artykul_do_promocji',return_value=promotion), \
             patch.object(stages,'pamiec_wystawionych',return_value=[]), \
             patch.object(stages,'teksty_ostatnich_notek',return_value=[]), \
             patch.object(stages,'zaczyn_z_kanalow',return_value='existing RSS context'), \
             patch.object(stages,'note',side_effect=writer or (lambda *a,**k: {'candidates':[]})):
            return stages.notki_dnia(self.conn,self.rid)

    def test_promotion_never_orders_unrelated_bank_research(self):
        promotion=dict(tytul='Already published',tekst='Published article',url='https://example.org/p/a',wystawione=0)
        with patch.object(stages,'posortuj_bank',side_effect=AssertionError('ranking waste')), \
             patch.object(stages,'wez_kandydatow',side_effect=AssertionError('borrow waste')), \
             patch.object(stages,'znajdz_ciekawostki',side_effect=AssertionError('research waste')):
            self.assertEqual(len(self.note_plan(['CIEKAWOSTKA'],promotion)),1)

    def test_reflection_and_empty_plan_do_not_order_bank_research(self):
        with patch.object(stages,'posortuj_bank',side_effect=AssertionError('ranking waste')), \
             patch.object(stages,'znajdz_ciekawostki',side_effect=AssertionError('research waste')):
            self.assertEqual(len(self.note_plan(['MYSL'])),1)
            self.assertEqual(self.note_plan([]),[])

    def test_generation_failure_returns_all_borrowed_ideas_but_not_old_used(self):
        items=[self.candidate('Alpine freight terminals change warehouse reservation contracts.'),
               self.candidate('Zephyr aircraft engines now carry an extended warranty.')]
        old=self.candidate('Earlier publication used this fact.');old['status']='uzyty'
        self.put(items+[old])
        with patch.object(stages,'posortuj_bank',return_value={}), \
             patch.object(stages,'swiezosc_faktu',return_value=(True,'')), \
             patch.object(stages,'wybierz_material',side_effect=lambda pool,*a,**k: pool.pop(0)):
            with self.assertRaises(llm.BudgetExceeded):
                self.note_plan(['CIEKAWOSTKA'],writer=lambda *a,**k: (_ for _ in ()).throw(llm.BudgetExceeded('quota')))
        self.assertEqual([x['status'] for x in stages.wczytaj_indeks()],['nowy','nowy','uzyty'])

    def test_complete_evidence_survives_bank_and_publication_mark(self):
        fact=self.candidate('A source establishes this qualified factual statement. '*13)
        fact['url']='https://example.org/document?reference='+'x'*430
        fact['control_fact']='Detailed qualified evidence. '*35
        with patch.object(stages,'bramka_kandydata',return_value=(True,'')):
            stages.dopisz_kandydatow([fact])
        stored=stages.wczytaj_indeks()[0]
        for key in ('fact','url','control_fact'):
            self.assertEqual(stored[key],fact[key])
        self.assertEqual(stages.oznacz_uzyty(fact),1)

    def test_rejected_update_does_not_remove_valid_prior_evidence(self):
        old=self.candidate('Acme Atlas billing threshold is 100 units for registered clients.')
        new=self.candidate('Acme Atlas billing threshold is 200 units for registered clients.')
        self.put([old])
        with patch.object(stages,'bramka_kandydata',return_value=(False,'missing evidence')), \
             patch.object(stages,'_to_aktualizacja',return_value=True):
            stages.dopisz_kandydatow([new])
        self.assertEqual([x['status'] for x in stages.wczytaj_indeks()],['nowy','odrzucony'])

    def test_expired_bank_does_not_pay_for_ranking(self):
        items=[self.candidate(str(i)) for i in range(3)]
        for x in items:x['wazny_do']='2000-01-01 00:00'
        self.put(items)
        with patch.object(llm,'call',side_effect=AssertionError('expired ranking waste')):
            self.assertEqual(stages.posortuj_bank(self.conn,self.rid)['ocenione'],0)

    def test_ranking_out_of_range_id_cannot_crash_or_reject_another_idea(self):
        self.put([self.candidate('one'),self.candidate('two')])
        answer={'kolejnosc':[0,1],'oceny':[{'id':999,'wyrzuc':True,'kod_wyrzucenia':'NO_MECHANISM'}]}
        with patch.object(llm,'call',return_value=json.dumps(answer)),patch.object(stages,'co_zadzialalo',return_value=''):
            self.assertEqual(stages.posortuj_bank(self.conn,self.rid)['ocenione'],2)
        self.assertTrue(all(x['status']=='nowy' for x in stages.wczytaj_indeks()))

    def test_empty_ranking_does_not_mark_entries_as_evaluated(self):
        self.put([self.candidate('one'),self.candidate('two')])
        before=stages.INDEKS_KANDYDATOW.read_bytes()
        with patch.object(llm,'call',return_value='{}'),patch.object(stages,'co_zadzialalo',return_value=''):
            self.assertEqual(stages.posortuj_bank(self.conn,self.rid)['ocenione'],0)
        self.assertEqual(stages.INDEKS_KANDYDATOW.read_bytes(),before)

    def test_repeated_article_drafts_do_not_multiply_the_evidence_bank(self):
        evidence={'unused_evidence':[{'url':'https://example.org/a','excerpts':['A detailed source excerpt on the contractual mechanism. '*3]}]}
        for _ in range(3):
            self.conn.execute("INSERT INTO articles(run_id,created_at,title,evidence,status) VALUES(?,?,?,?,?)",
                              (self.rid,db.now(),'draft',json.dumps(evidence),'SAVED'))
        self.conn.commit()
        self.assertEqual(len(stages.bank_fragmentow(self.conn)),1)

    def test_failed_daily_refresh_is_not_reordered_by_each_caller(self):
        with patch.object(llm,'call',side_effect=RuntimeError('temporary failure')) as call:
            self.assertEqual(aktualne_modele.pobierz(self.conn,self.rid),{})
            self.assertEqual(aktualne_modele.pobierz(self.conn,self.rid),{})
            self.assertEqual(call.call_count,1)
            aktualne_modele.pobierz(self.conn,self.rid,wymus=True)
            self.assertEqual(call.call_count,2)

    def test_stale_context_is_labeled_and_future_timestamp_is_not_fresh(self):
        old={'_pobrane':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),
             'aktualne':[{'model':'Example','wydany':'2026-01-01'}]}
        self.assertIn('STALE CONTEXT',aktualne_modele.jako_tekst(old))
        old['_pobrane']=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        self.assertFalse(aktualne_modele._swieze(old))

    def test_retry_after_seconds_date_and_invalid_values(self):
        self.assertEqual(retry_policy.retry_after({'retry-after':'45'},now=1000),45)
        date=format_datetime(datetime.fromtimestamp(1060,timezone.utc),usegmt=True)
        self.assertEqual(retry_policy.retry_after({'retry-after':date},now=1000),60)
        for value in ('NaN','inf','nonsense'):
            self.assertIsNone(retry_policy.retry_after({'retry-after':value}))

    def test_provider_pause_blocks_later_calls_without_new_cost_reservation(self):
        import httpx
        response=httpx.Response(429,headers={'Retry-After':'600'},request=httpx.Request('POST','https://api.deepseek.com/test'))
        error=httpx.HTTPStatusError('rate limited',request=response.request,response=response)
        with patch.dict(config.MODEL_FOR,{'comment':config.DEEPSEEK}), \
             patch.object(llm,'_call_deepseek',side_effect=error) as transport:
            with self.assertRaises(call_runtime.DeadlineExceeded):
                llm.call('comment','system','user',conn=self.conn,run_id=self.rid)
            with self.assertRaises(llm.ProviderDeferred):
                llm.call('comment','system','user',conn=self.conn,run_id=self.rid)
            self.assertEqual(transport.call_count,1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM calls').fetchone()[0],1)

    def test_source_429_defers_same_host_without_browser_retry(self):
        import httpx
        response=httpx.Response(429,headers={'Retry-After':'600'},text='busy')
        sources=[{'url':'https://example.org/a'},{'url':'https://example.org/b'}]
        with patch.object(httpx.Client,'get',return_value=response) as get, \
             patch.object(stages,'_dobierz_przegladarka',return_value=[]) as browser:
            self.assertEqual(stages.fetch(self.conn,self.rid,sources),[])
            self.assertEqual(stages.fetch(self.conn,self.rid,sources),[])
            self.assertEqual(get.call_count,1)
            self.assertTrue(all(not c.args[2] for c in browser.call_args_list))
        self.assertEqual(self.conn.execute('SELECT fail_reason FROM sources').fetchall()[0][0],'HTTP 429')

    def test_source_duplicate_is_fetched_once(self):
        import httpx,trafilatura
        source={'url':'https://example.org/a','class':'PRIMARY'}
        with patch.object(httpx.Client,'get',return_value=httpx.Response(200,text='html')) as get, \
             patch.object(trafilatura,'extract',return_value='Verified source document. '*100):
            self.assertEqual(len(stages.fetch(self.conn,self.rid,[source,source])),1)
            self.assertEqual(get.call_count,1)


    def test_audit_is_read_only_and_reports_unknown_usage_separately(self):
        self.conn.execute("INSERT INTO calls(run_id,at,provider,model,purpose,ok,cost_usd,usage_status,reserved_usd) VALUES(?,?,?,?,?,?,?,?,?)",
            (self.rid,db.now(),'test','test','research',0,0.,'unknown',.25))
        self.conn.commit()
        before=(self.root/'agent-v2.db').read_bytes()
        result=audyt_kosztow.collect(self.root)
        self.assertEqual(result['recorded_usd'],0.)
        self.assertEqual(result['unresolved_reserved_usd'],.25)
        self.assertEqual(result['usage_states'],{'unknown':1})
        self.assertEqual((self.root/'agent-v2.db').read_bytes(),before)
        missing=self.root/'absent'
        with self.assertRaises(Exception):
            audyt_kosztow.collect(missing)
        self.assertFalse(missing.exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
