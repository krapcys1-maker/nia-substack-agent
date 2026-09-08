"""Offline integration checks for feed recovery, paid-work avoidance and reports."""
from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'agent-v2'))
os.environ['AGENT_V2_BEZ_KONFIGURACJI'] = '1'
import config
import feed_cache
import insights
import interaction_history
import research_tasks
import stages
import statystyki
import llm
import korpus_kanalow
import artykul_z_puli as article

XML = b'<rss><channel><item><title>A useful fixture about agents</title></item></channel></rss>'
NOW = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)


class AuditPorts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.data = patch.object(config, 'DATA_DIR', self.directory)
        self.data.start()
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        self.network.start()
        self.paid = patch.object(llm, 'call', side_effect=AssertionError('No paid call'))
        self.paid_mock = self.paid.start()

    def tearDown(self):
        self.paid.stop()
        self.network.stop()
        self.data.stop()
        self.temp.cleanup()

    def write_rows(self, name, rows):
        (self.directory / name).write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')

    def test_comment_filter_runs_before_both_persona_and_regular_writer_selection(self):
        self.write_rows('dziennik.jsonl', [dict(rodzaj='komentarz',udane=True,gdzie='https://example.org/p/post')])
        posts = [dict(url='https://example.org/p/post?utm_source=email')]
        for persona in (True, False):
            with patch.object(config, 'PERSONA_WLACZONA', persona):
                self.assertEqual(stages.wybierz_cele(None, 1, posts), [])
                # A second batch uses the same gate, not a separate unfiltered route.
                self.assertEqual(stages.wybierz_cele(None, 1, posts), [])
        self.paid_mock.assert_not_called()

    def test_failed_comments_and_new_reply_parents_remain_eligible(self):
        self.write_rows('dziennik.jsonl', [dict(rodzaj='komentarz',udane=False,gdzie='https://example.org/p/post'),
             dict(rodzaj='odpowiedz',udane=True,gdzie='note/c-123')])
        posts = [dict(url='https://example.org/p/post'),dict(url='https://substack.com/@writer/note/c-123'),
                 dict(url='https://substack.com/note/c-456')]
        self.assertEqual(interaction_history.unhandled(posts,self.directory),[posts[0],posts[2]])
        self.assertEqual(interaction_history.unhandled(posts,self.directory/'other'),posts)
        self.assertNotEqual(interaction_history.target_key('https://example.org/item?id=1'),
                            interaction_history.target_key('https://example.org/item?id=2'))

    def test_feed_survives_restart_and_changed_url_cannot_reuse_old_source(self):
        request = Mock(return_value=Mock(status_code=200,content=XML))
        t = NOW.timestamp()
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t)[1], 'network')
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t+60)[1], 'cache')
        self.assertEqual(request.call_count,1)
        feed_cache.fetch(self.directory,'https://example.org/b',request,t+60)
        feed_cache.fetch(self.directory/'other','https://example.org/a',request,t+60)
        self.assertEqual(request.call_count,3)

    def test_retry_after_and_cached_fallback_never_reset_network_failures(self):
        t = NOW.timestamp()
        request = Mock(return_value=Mock(status_code=200,content=XML))
        feed_cache.fetch(self.directory,'https://example.org/a',request,t)
        request.return_value = Mock(status_code=429,content=b'',headers={'retry-after':'7200'})
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t+1801)[1], 'stale')
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t+2000)[1], 'stale')
        self.assertEqual(request.call_count,2)
        feed_cache.fetch(self.directory,'https://example.org/a',request,t+9002)
        state=json.loads(next((self.directory/'feed-cache').glob('*.json')).read_text())
        self.assertEqual(state['failures'],2)
        self.assertEqual(state['fetched_at'],t)
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t+86401)[0],b'')

    def test_invalid_xml_does_not_replace_good_feed_and_recovery_resets_failures(self):
        t = NOW.timestamp()
        request=Mock(return_value=Mock(status_code=200,content=XML))
        feed_cache.fetch(self.directory,'https://example.org/a',request,t)
        request.return_value=Mock(status_code=200,content=b'<html>Consent</html>',headers={})
        body,origin=feed_cache.fetch(self.directory,'https://example.org/a',request,t+1801)
        self.assertEqual((body,origin),(XML,'stale'))
        request.return_value=Mock(status_code=200,content=XML)
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,t+2200)[1],'network')
        state=json.loads(next((self.directory/'feed-cache').glob('*.json')).read_text())
        self.assertEqual(state['failures'],0)

    def test_http_failure_without_cache_is_bounded_and_keeps_other_feeds_available(self):
        request=Mock(side_effect=TimeoutError)
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,NOW.timestamp()),(b'','unavailable'))
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',request,NOW.timestamp()+1),(b'','deferred'))
        request.assert_called_once()
        good=Mock(return_value=Mock(status_code=200,content=XML))
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/b',good,NOW.timestamp())[0],XML)

    def test_corrupt_cache_timing_cannot_defer_a_feed_forever(self):
        good=Mock(return_value=Mock(status_code=200,content=XML))
        feed_cache.fetch(self.directory,'https://example.org/a',good,NOW.timestamp())
        path=next((self.directory/'feed-cache').glob('*.json'))
        state=json.loads(path.read_text());state['retry_at']=float('inf');state['fetched_at']=0
        path.write_text(json.dumps(state))
        self.assertEqual(feed_cache.fetch(self.directory,'https://example.org/a',good,NOW.timestamp())[1],'network')

    def test_missing_database_report_is_read_only_and_returns_unknown_cost(self):
        report=insights.collect(self.directory,now=NOW)
        self.assertIn('no_database',report['warnings'])
        self.assertIn('no_idea_bank',report['warnings'])
        self.assertIsNone(report['bank']['total'])
        self.assertFalse((self.directory/'agent-v2.db').exists())
        self.assertEqual(list(self.directory.iterdir()),[])
        path=self.directory/'indeks_kandydatow.json'
        path.write_text('[]')
        self.assertEqual(insights.collect(self.directory,now=NOW)['bank']['total'],0)
        path.write_text('[unfinished')
        self.assertIn('unreadable_idea_bank',insights.collect(self.directory,now=NOW)['warnings'])
        self.assertEqual(path.read_text(),'[unfinished')

    def test_one_hour_graph_cannot_become_a_day_and_late_first_snapshot_is_unknown(self):
        published=NOW-timedelta(hours=48)
        curve={'graphData':{'series':[{'isPrimary':True,'values':[
            {'timestamp':published.isoformat(),'value':0},
            {'timestamp':(published+timedelta(hours=1)).isoformat(),'value':80}]}]}}
        self.assertEqual(insights.graph_windows(curve,published.isoformat(),NOW.isoformat()),{})
        records=[dict(wyswietlenia=140,ma_karty_zasiegu=True,kiedy=NOW.isoformat())]
        self.assertIsNone(insights.at_window(records,published,24,NOW))
        self.assertEqual(insights.at_window(records,published,48,NOW),140)
        for graph in ({'series':7},{'series':[{'isPrimary':True,'values':7}]}):
            self.assertEqual(insights.graph_windows({'graphData':graph},published.isoformat(),NOW.isoformat()),{})

    def test_zero_is_valid_only_with_a_measured_reach_card(self):
        published=NOW-timedelta(hours=24)
        row=dict(kiedy=NOW.isoformat(),wyswietlenia=0,ma_karty_zasiegu=True)
        self.assertEqual(insights.at_window([row],published,24,NOW),0)
        row['ma_karty_zasiegu']=False
        self.assertIsNone(insights.at_window([row],published,24,NOW))
        row.update(ma_karty_zasiegu=True,zmierzone=(NOW-timedelta(hours=8)).isoformat())
        self.assertIsNone(insights.at_window([row],published,24,NOW))

    def test_mature_curve_uses_the_post_publication_time_and_ignores_benchmark(self):
        published=NOW-timedelta(hours=48)
        values=[{'timestamp':(published+timedelta(hours=h)).isoformat(),'value':v} for h,v in [(0,0),(24,30),(48,70)]]
        curve={'graphData':{'series':[{'isPrimary':True,'values':values},
                  {'isPrimary':False,'values':[dict(p,value=999) for p in values]}]}}
        windows=insights.graph_windows(curve,published.isoformat(),NOW.isoformat())
        self.assertEqual(windows['24']['views'],30)
        self.assertEqual(windows['48']['views'],70)
        record=dict(kiedy=NOW.isoformat(),windows=windows)
        self.assertEqual(insights.at_window([record],published,24,NOW),30)

    def test_cost_period_excludes_tests_keeps_failed_attempts_and_unknown_reservations(self):
        conn=sqlite3.connect(self.directory/'agent-v2.db')
        conn.executescript('CREATE TABLE runs(id INTEGER,tryb TEXT); CREATE TABLE calls(run_id INTEGER,at TEXT,akcja TEXT,cost_usd REAL,ok INTEGER,usage_status TEXT,reserved_usd REAL);')
        conn.executemany('INSERT INTO runs VALUES(?,?)',[(1,'produkcja'),(2,'test')])
        for rid,at,action,price,ok,state,reserved in [(1,NOW,'notka',.1,1,'known',0),(1,NOW,'notka',.2,0,'known',0),
          (2,NOW,'notka',9,1,'known',0),(1,NOW-timedelta(days=8),'notka',50,1,'known',0),(1,NOW,'artykul',0,0,'unknown',.8)]:
            conn.execute('INSERT INTO calls VALUES(?,?,?,?,?,?,?)',(rid,at.isoformat(),action,price,ok,state,reserved))
        conn.commit();conn.close()
        self.write_rows('dziennik.jsonl',[dict(rodzaj='notka',udane=True,nasz_id='1',kiedy=(NOW-timedelta(hours=24)).isoformat()),
            dict(rodzaj='artykul',udane=True,nasz_id='2',kiedy=NOW.isoformat())])
        self.write_rows('statystyki.jsonl',[dict(rodzaj='notka',id='1',kiedy=NOW.isoformat(),ma_karty_zasiegu=True,wyswietlenia=15),
           dict(rodzaj='notka',id='old',kiedy=NOW.isoformat(),ma_karty_zasiegu=True,wyswietlenia=999)])
        report=insights.collect(self.directory,now=NOW)
        self.assertEqual(report['groups']['notka']['recorded_usd'],.3)
        self.assertEqual(report['groups']['notka']['period_usd_per_publication'],.3)
        self.assertEqual(report['groups']['notka']['views_24h'],15)
        self.assertEqual(report['test_recorded_usd'],9)
        self.assertEqual(report['groups']['artykul']['unresolved_reserved_usd'],.8)
        self.assertIsNone(report['groups']['artykul']['period_usd_per_publication'])
        with closing(sqlite3.connect(self.directory/'agent-v2.db')) as conn:
            conn.execute("UPDATE calls SET cost_usd=NULL WHERE run_id=1 AND akcja='notka'")
            conn.commit()
        report=insights.collect(self.directory,now=NOW)
        self.assertEqual(report['groups']['notka']['unknown_attempts'],2)
        self.assertIsNone(report['groups']['notka']['period_usd_per_publication'])

    def test_followup_uses_held_evidence_and_actual_missing_sources_without_any_model(self):
        brief=dict(title='Fixture question',question='What changed?',zrodlo_faktu='https://example.org/lead')
        corpus=[dict(url='https://example.org/held',text='Observed material',**{'class':'PRIMARY'}),
                dict(url='https://example.org/failed',text='',**{'class':'PRIMARY'})]
        text=research_tasks.followup(self.directory,1,brief,corpus,3,2)
        self.assertIn('Need 2 additional retrievable',text)
        self.assertIn('Need 1 additional primary',text)
        self.assertIn('https://example.org/held',text)
        self.assertIn('Observed material',text)
        self.assertIn('https://example.org/failed',text)
        long = research_tasks.followup(self.directory,1,brief,
            [dict(url='https://example.org/'+str(i),text='x'*5000) for i in range(12)],20,2)
        self.assertLess(len(long),6500)
        self.paid_mock.assert_not_called()
        report=insights.collect(self.directory)
        self.assertEqual(report['research'][0]['question'],'What changed?')

    def test_feed_decision_trace_does_not_change_writer_material(self):
        today=datetime.now(timezone.utc).date().isoformat()
        items=[dict(temat='A useful agent news item',url='https://example.org/new',data=today,kanal='Fixture',skrot='Excerpt.'),
               dict(temat='An old agent news item',url='https://example.org/old',data='2000-01-01',kanal='Fixture')]
        with patch.object(korpus_kanalow,'korpus_kanalow',return_value=items):
            original=stages.zaczyn_z_kanalow(ze_skrotem=True)
            traced=stages.zaczyn_z_kanalow(ze_skrotem=True,run_id=1)
        self.assertEqual(original,traced)
        decision=json.loads((self.directory/'editorial-decisions.jsonl').read_text())
        self.assertEqual([i['reason'] for i in decision['items']],['offered_to_writer','outside_date_window'])


if __name__=='__main__':
    unittest.main()
