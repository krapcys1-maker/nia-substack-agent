"""Offline checks for topic selection and the evidence actually given to NIA."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import copy
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'agent-v2'))
os.environ['AGENT_V2_BEZ_KONFIGURACJI'] = '1'
import config
import db
import llm
import stages
import personality
import korpus_kanalow as feeds
import artykul_z_puli as article
import audyt_tematow as audit
from tekst_strony import tekst_z_html


class SourceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.uzyj_katalogu_danych(Path(self.tmp.name))
        self.path = patch.object(stages, 'INDEKS_KANDYDATOW', config.DATA_DIR / 'index.json')
        self.path.start()
        self.net = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        self.net.start()
        self.paid = patch.object(llm, 'call', side_effect=AssertionError('No paid calls'))
        self.paid.start()
        self.conn = db.connect()

    def tearDown(self):
        self.conn.close()
        self.paid.stop(); self.net.stop(); self.path.stop()
        config.przywroc_katalog_danych(self.old)
        self.tmp.cleanup()

    def fact(self, text, **extra):
        return dict(fact=text, url='https://example.org/lead', status='nowy', kiedy=db.now(),
                    source_date=datetime.now(timezone.utc).date().isoformat(),
                    wazny_do=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(), **extra)

    def test_fresh_search_uses_admitted_bank_records_and_does_not_repeat_first(self):
        bad = self.fact('A raw result rejected by the admission gate.'); bad['status'] = 'odrzucony'
        first = self.fact('Alpine robots obtain reliable navigation through calibrated lidar.', z_kanalu=True)
        second = self.fact('Zephyr researchers document hallucinated legal citations in contracts.', z_kanalu=True)
        def search(*args, **kwargs):
            stages._zapisz_indeks([bad, first, second])
            return [bad, first, second]
        with patch.object(stages, 'znajdz_ciekawostki', side_effect=search) as call, \
             patch.object(stages, 'tematy_do_porownania', return_value=[]), \
             patch.object(stages, 'ostatnie_notki', return_value=[]):
            a = article.wybierz_fakt(self.conn, 1)
            b = article.wybierz_fakt(self.conn, 1)
        self.assertEqual([a['fact'], b['fact']], [first['fact'], second['fact']])
        self.assertEqual(call.call_count, 1)
        self.assertEqual([r['status'] for r in stages.wczytaj_indeks()], ['odrzucony','uzyty','uzyty'])

    def test_original_lead_reaches_fetch_without_being_assumed_primary(self):
        lead = self.fact('One supported research lead with a public source.')
        brief = dict(title='A concrete question', question='What did the test show?',
                     second_act='A second measurement followed the first.', zrodlo_faktu=lead['url'])
        seen = []
        def fetch(conn, rid, sources):
            seen.extend(copy.deepcopy(sources))
            return [{**s, 'text':'Retrieved document content.'} for s in sources]
        with patch.object(article, 'wybierz_fakt', return_value=lead), \
             patch.object(article, 'temat_z_faktu', return_value=brief), \
             patch.object(stages, 'discovery', return_value=[{'url':'https://example.net/record','class':'PRIMARY'}]), \
             patch.object(stages, 'fetch', side_effect=fetch), \
             patch.object(stages, 'classify', return_value=[]), \
             patch.object(stages, 'synthesis', return_value={}), \
             patch.object(article, '_napisz_i_zapisz', return_value=0), \
             patch.multiple(config, MIN_ZRODEL_DO_PISANIA=1, MIN_PRIMARY_SOURCES=1), \
             patch.object(sys, 'argv', ['offline-test']):
            self.assertEqual(article._przebieg(self.conn, 1), 0)
        self.assertEqual(seen[0]['url'], lead['url'])
        self.assertEqual(seen[0]['class'], 'UNCLASSIFIED')
        self.assertEqual(len([s for s in seen if s['url']==lead['url']]), 1)

    def test_unfetched_claim_is_retained_in_archive_but_not_writer_evidence(self):
        archive = {'confirmed_claims':[{'claim':'An actual supported claim','url':'https://example.org/a'},
                                      {'claim':'Unverified recalled detail','not_fetched':True}],
                   'source_dates':{}}
        written = stages.karta_dla_pisarza(archive)
        self.assertEqual(len(written['confirmed_claims']), 1)
        self.assertEqual(len(archive['confirmed_claims']), 2)
        self.assertNotIn('Unverified', json.dumps(written))

    def test_marked_article_prose_wins_over_long_irrelevant_page_menus(self):
        prose = 'The release changes setup but leaves security decisions with the operator.'
        for marker in ('class="bodytext large-12"', 'itemprop="articleBody"'):
            page = ('<html><nav>' + 'Other headline. '*100 + '</nav><div '+marker+'>'
                    '<div class="toplist"><ul><li><p>Related story you did not request.</p></li></ul></div>'
                    '<p>'+prose+'</p><p>A <em>second</em> paragraph.</p>'
                    '<ul><li>A real listed finding.</li></ul>'
                    '<script>Track the reader.</script></div></html>')
            self.assertEqual(tekst_z_html(page), prose+'\nA second paragraph.\nA real listed finding.')
            empty = '<div '+marker+'><script>Load article later.</script></div>'
            self.assertEqual(tekst_z_html('<nav>'+'Unrelated story. '*100+'</nav>'+empty), '')

    def test_generic_extraction_still_reads_pages_without_marked_article_bodies(self):
        page = '<html><main><p>' + 'A documented independent observation. '*30 + '</p></main></html>'
        self.assertIn('documented independent observation', tekst_z_html(page))

    def test_hnrss_metadata_is_not_a_description_and_self_post_has_its_own_url(self):
        for intro in ('', '<p>I built a local editor for large CSV files.</p>'):
            xml = ('<rss><channel><item><title>Show HN: A local CSV editor</title>'
                   '<link>https://example.org/editor</link><comments>https://news.ycombinator.com/item?id=900000001</comments>'
                   '<description><![CDATA['+intro+'<p>Article URL: <a href="https://example.org/editor">editor</a></p>'
                   '<p>Points: 12</p><p># Comments: 3</p>]]></description></item></channel></rss>')
            row = feeds.wpisy_z_kanalu('Show HN', xml.encode())[0]
            self.assertNotIn('Points:', row['skrot'])
            self.assertNotIn('Article URL:', row['skrot'])
            self.assertEqual(bool(row['skrot']), bool(intro))
            self.assertEqual(row['url'], 'https://news.ycombinator.com/item?id=900000001' if intro else 'https://example.org/editor')

    def test_article_headlines_are_fresh_and_carry_the_actual_lead_url(self):
        today = datetime.now(timezone.utc).date()
        entries = [dict(temat='A new agent source worth checking',data=today.isoformat(),url='https://example.org/new'),
                   dict(temat='An old source',data=(today-timedelta(days=50)).isoformat(),url='https://example.org/old')]
        with patch.object(feeds, 'korpus_kanalow', return_value=entries):
            text = stages.zaczyn_z_kanalow()
        self.assertIn('https://example.org/new', text)
        self.assertNotIn('https://example.org/old', text)

    def test_explicit_sponsored_categories_do_not_enter_the_news_pool(self):
        rss = b'<rss><channel><item><title>A sponsored claim about new agents</title><category>sponsored</category></item><item><title>A reported new agent incident</title></item></channel></rss>'
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A sponsored claim about new agents</title><category term="Sponsored"/></entry><entry><title>A reported new agent incident</title></entry></feed>'
        for xml in (rss, atom):
            entries = feeds.wpisy_z_kanalu('Fixture', xml)
            self.assertEqual(len(entries), 1)
            self.assertNotIn('sponsored', entries[0]['temat'])

    def test_persona_prioritizes_configured_subject_and_labels_headline_only(self):
        today = datetime.now(timezone.utc).date().isoformat()
        entries = [dict(temat='A woodworking tutorial for beginners',data=today,url='https://example.org/wood'),
                   dict(temat='A new Claude style patch',data=today,url='https://example.org/claude')]
        with patch.object(feeds, 'korpus_kanalow', return_value=entries), \
             patch.object(config, 'ZNAKI_NISZY', ['claude']):
            text = stages.zaczyn_z_kanalow(ile=1, ze_skrotem=True, source_urls={})
        self.assertIn('Claude', text)
        self.assertNotIn('woodworking', text)
        self.assertIn('headline only', text)

    def test_rss_only_audit_accepts_a_short_full_cache(self):
        class EndSection(Exception):
            pass
        checks = []
        cache = copy.deepcopy(feeds._ZAPAS)
        try:
            with patch.multiple(config, KANALY_YOUTUBE={}, KANALY_RSS={'Fixture':'https://example.org/rss'}), \
                 patch.object(audit, 'bank', return_value=[]), \
                 patch.object(audit, 'etap', side_effect=lambda n,*a: (_ for _ in ()).throw(EndSection()) if n==2 else None), \
                 patch.object(audit, 'werdykt', side_effect=lambda title,status,*a: checks.append((title,status))), \
                 patch.object(feeds, 'korpus_kanalow', return_value=[{'kanal':'Fixture','temat':'One supplied item'}]):
                with self.assertRaises(EndSection), redirect_stdout(io.StringIO()):
                    audit.main()
        finally:
            feeds._ZAPAS.clear(); feeds._ZAPAS.update(cache)
        self.assertEqual(len(checks), 3)
        self.assertTrue(all(status=='OK' for _,status in checks), checks)

    def test_prolific_feeds_do_not_crowd_out_a_builder_with_actual_source_text(self):
        today = datetime.now(timezone.utc).date().isoformat()
        entries = [dict(temat='AI corporation announcement '+str(i),kanal='Newsroom',data=today,
                        skrot='A company introduces an agent.',url='https://example.org/news/'+str(i)) for i in range(20)]
        entries += [dict(temat='An AI launch headline',kanal='Builders',data=today,url='https://example.org/launch'),
                    dict(temat='A small architecture checker',kanal='Builders',data=today,
                         skrot='I measured how AI agents change imports and published the results.',url='https://example.org/builder')]
        with patch.object(feeds,'korpus_kanalow',return_value=entries), patch.object(config,'ZNAKI_NISZY',['ai']), \
             patch.object(config,'PERSONA_WLACZONA',True):
            text = stages.zaczyn_z_kanalow(ile=2,ze_skrotem=True,source_urls={})
            article_text = stages.zaczyn_z_kanalow(ile=2)
        self.assertIn('small architecture checker',text)
        self.assertEqual(text.count('corporation announcement'),1)
        self.assertNotIn('launch headline',text)
        self.assertIn('small architecture checker',article_text)
        self.assertIn('https://example.org/builder',article_text)


if __name__ == '__main__':
    unittest.main()
