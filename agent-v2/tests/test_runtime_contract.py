"""Offline contract tests: provider failures, accounting and budget races."""
import json
import io
import contextlib
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config
import db
import llm
import call_runtime as runtime
import run
import browser_reader


class Stream:
    def __init__(self, events): self.events = events
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self): pass
    def iter_lines(self):
        for event in self.events:
            yield 'data: ' + json.dumps(event)
        yield 'data: [DONE]'


class RuntimeContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = config.uzyj_katalogu_danych(pathlib.Path(self.directory.name))
        self.settings = patch.multiple(config, W_TESCIE=True, WOLNO_WOLAC_MODEL=True,
            DRY_RUN=False, KILL_SWITCH=False, DEEPSEEK_API_KEY='offline', ANTHROPIC_API_KEY='offline', OPENAI_API_KEY='offline',
            RUN_LIMIT_USD=5., DAILY_LIMIT_USD=10., TEST_LIMIT_USD=10., MONTHLY_LIMIT_USD=20.,
            PONOWIENIE_ODSTEP_S=0, PONOWIENIA=0)
        self.settings.start()
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden'))
        self.network.start()
        runtime.RUN_DEADLINE = None
        self.conn = db.connect()
        self.rid = db.start_run(self.conn, 'contract')
    def tearDown(self):
        self.conn.close()
        self.network.stop(); self.settings.stop()
        config.przywroc_katalog_danych(self.previous)
        self.directory.cleanup()
    def rows(self): return [dict(r) for r in self.conn.execute('SELECT * FROM calls')]
    def call(self, **kwargs):
        return llm.call('comment', 'system', 'user', conn=self.conn, run_id=self.rid, **kwargs)
    def test_weekend_and_timezone(self):
        self.assertFalse(config.w_szczycie(datetime(2026,9,6,7,tzinfo=timezone.utc)))
        self.assertTrue(config.w_szczycie(datetime(2026,9,7,7,tzinfo=timezone.utc)))
        self.assertFalse(config.w_szczycie(datetime(2026,9,7,10,tzinfo=timezone.utc)))
    def test_missing_usage_is_unknown(self):
        with patch.object(llm.httpx, 'stream', return_value=Stream([{'choices':[{'delta':{'content':'ok'},'finish_reason':'stop'}]}])):
            self.assertEqual(self.call(), 'ok')
        row=self.rows()[0]
        self.assertEqual((row['ok'],row['price_verified'],row['usage_status']), (1,0,'unknown'))
        self.assertGreater(row['reserved_usd'],0)
    def test_chat_uses_configured_reasoning_effort(self):
        event={'choices':[{'delta':{'content':'ok'},'finish_reason':'stop'}],
               'usage':{'prompt_tokens':10,'completion_tokens':10}}
        with patch.object(llm.httpx,'stream',return_value=Stream([event])) as request:
            self.call()
        self.assertEqual(request.call_args.kwargs['json']['reasoning_effort'],config.DEEPSEEK_EFFORT)
    def test_partial_answer_is_not_success(self):
        with patch.object(llm.httpx,'stream',return_value=Stream([{'choices':[{'delta':{'content':'partial'}}]}])):
            with self.assertRaises(llm.httpx.RemoteProtocolError): self.call()
        self.assertEqual(self.rows()[0]['ok'],0)
    def test_truncated_preserves_usage(self):
        event={'choices':[{'delta':{'content':'partial'},'finish_reason':'length'}],
               'usage':{'prompt_tokens':1000,'completion_tokens':2000}}
        with patch.object(llm.httpx,'stream',return_value=Stream([event])):
            with self.assertRaises(llm.Truncated): self.call()
        row=self.rows()[0]
        self.assertEqual((row['tokens_in'],row['tokens_out'],row['usage_status']),(1000,2000,'known'))
        self.assertGreater(row['cost_usd'],0)
        self.assertEqual(row['reserved_usd'],0)
    def test_incomplete_responses_preserves_usage(self):
        event={'type':'response.incomplete','response':{'output_text':'partial',
            'output':[{'type':'message','content':[{'type':'output_text','text':'partial'}]}],
            'usage':{'input_tokens':1000,'output_tokens':2000}}}
        with patch.object(llm.httpx,'stream',return_value=Stream([event])):
            with self.assertRaises(llm.Truncated): self.call(web_search=True)
        self.assertEqual(self.rows()[0]['tokens_out'],2000)
    def test_failed_responses_preserves_usage(self):
        event={'type':'response.failed','response':{'error':{'message':'failed'},
            'usage':{'input_tokens':1000,'output_tokens':2000}}}
        with patch.object(llm.httpx,'stream',return_value=Stream([event])):
            with self.assertRaises(llm.Truncated): self.call(web_search=True)
        row=self.rows()[0]
        self.assertEqual((row['tokens_out'],row['ok'],row['usage_status']),(2000,0,'known'))
    def test_retry_has_distinct_rows_and_preflights(self):
        with patch.object(config,'PONOWIENIA',2), patch.object(llm,'_call_deepseek',side_effect=[
                llm.httpx.ReadTimeout('x'),llm.httpx.ReadTimeout('x'),('ok',100,100,0,0)]), \
                patch.object(llm,'_preflight',wraps=llm._preflight) as pre:
            self.assertEqual(self.call(),'ok')
        rows=self.rows()
        self.assertEqual([r['attempt_no'] for r in rows],[1,2,3])
        self.assertEqual(len({r['operation_id'] for r in rows}),1)
        self.assertGreaterEqual(pre.call_count,3)
        self.assertEqual([r['ok'] for r in rows],[0,0,1])
    def test_request_tokens_fit_available_reservation(self):
        def transport(*args):
            return 'ok',len('systemuser'.encode())+128,runtime.token_limit(99999),0,0
        with patch.object(config,'RUN_LIMIT_USD',.01),patch.object(llm,'_call_deepseek',side_effect=transport):
            self.call()
        self.assertLessEqual(self.rows()[0]['cost_usd'],.01)
    def test_pending_reservation_visible_to_other_connection(self):
        llm._reserve_attempt(self.conn,self.rid,'comment','s','u',False,'one',1)
        other=db.connect()
        try:
            self.assertGreater(db.budget_used(other,run_id=self.rid),0)
            with patch.object(config,'RUN_LIMIT_USD',.001):
                with self.assertRaises(llm.BudgetExceeded):
                    llm._reserve_attempt(other,self.rid,'comment','s','u',False,'two',1)
            self.assertEqual(len(self.rows()),1)
        finally: other.close()
    def test_simultaneous_reservations_cannot_spend_same_balance(self):
        barrier=threading.Barrier(2)
        outcomes=[]
        def reserve(name):
            conn=db.connect()
            try:
                barrier.wait(timeout=5)
                llm._reserve_attempt(conn,self.rid,'comment','s','u',False,name,1)
                outcomes.append('reserved')
            except llm.BudgetExceeded:
                outcomes.append('budget')
            except BaseException as exc:
                outcomes.append(type(exc).__name__)
            finally:
                conn.close()
        with patch.object(config,'RUN_LIMIT_USD',.005),patch.dict(config.MAX_TOKENS,comment=1000000):
            workers=[threading.Thread(target=reserve,args=(str(i),)) for i in range(2)]
            for worker in workers: worker.start()
            for worker in workers: worker.join(timeout=10)
        self.assertCountEqual(outcomes,['reserved','budget'])
        self.assertEqual(len(self.rows()),1)
        self.assertLessEqual(db.budget_used(self.conn,run_id=self.rid),.005)
    def test_instance_lock_excludes_process_and_releases_on_close(self):
        child='''import pathlib,sys
sys.path.insert(0,sys.argv[1])
import config,run
config.DATA_DIR=pathlib.Path(sys.argv[2])
try:
    lock=run.zajmij_zamek()
except run.JuzDziala:
    print('locked')
else:
    print('acquired')
    lock.close()
'''
        args=[sys.executable,'-c',child,str(pathlib.Path(run.__file__).parent),self.directory.name]
        lock=run.zajmij_zamek()
        try:
            lock.seek(0)
            before=lock.read()
            result=subprocess.run(args,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),'locked')
            lock.seek(0)
            self.assertEqual(lock.read(),before)
        finally:
            lock.close()
        result=subprocess.run(args,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'acquired')
    def test_deadline_bounds_blocked_worker_and_has_no_retry(self):
        done=threading.Event()
        def transport(*args): done.wait(2); return 'late',100,100,0,0
        start=time.monotonic()
        try:
            with patch.object(config,'CALL_DEADLINE_S',.05),patch.object(llm,'_call_deepseek',side_effect=transport):
                with self.assertRaises(runtime.DeadlineExceeded): self.call()
            self.assertLess(time.monotonic()-start,.5)
            self.assertEqual(len(self.rows()),1)
            self.assertEqual(self.rows()[0]['usage_status'],'unknown')
        finally: done.set()
    def test_browser_keeps_partial_results_when_child_hangs(self):
        output=pathlib.Path(self.directory.name)/'read.jsonl'
        child='''import json,pathlib,sys,time
pathlib.Path(sys.argv[1]).write_text(json.dumps({'url':'https://one.example','text':'evidence'})+'\\n',encoding='utf-8')
time.sleep(60)
'''
        start=time.monotonic()
        entries=browser_reader._collect([sys.executable,'-c',child,str(output)],
            ['https://one.example','https://two.example'],output,1)
        self.assertLess(time.monotonic()-start,8)
        self.assertEqual(entries[0]['text'],'evidence')
        self.assertTrue(entries[1]['error'])
    def test_cache_usage_prices_all_categories(self):
        state=runtime.Attempt(1000,time.monotonic()+1)
        token=runtime.CURRENT.set(state)
        try:
            runtime.capture(SimpleNamespace(input_tokens=100,output_tokens=50,
                cache_read_input_tokens=10000,cache_creation_input_tokens=5000), 'claude')
        finally: runtime.CURRENT.reset(token)
        self.assertEqual(state.usage['cache_write_5m'],5000)
        self.assertEqual(state.usage['cache_hit'],10000)
        call_id,_,when=llm._reserve_attempt(self.conn,self.rid,'write','s','u',False,'claude',1)
        llm._settle_attempt(self.conn,call_id,state,config.FABLE,when,True)
        self.assertAlmostEqual(self.rows()[0]['cost_usd'],.0685,6)
    def test_image_usage_is_used(self):
        call_id,_,_=llm._reserve_attempt(self.conn,self.rid,'obraz','','s',False,'img',1)
        llm._settle_image(self.conn,call_id,{'usage':{'input_tokens':100,'output_tokens':6000,
            'input_tokens_details':{'text_tokens':100,'image_tokens':0}}},True)
        self.assertAlmostEqual(self.rows()[0]['cost_usd'],.1925)
    def test_cancelled_call_records_attempt(self):
        with patch.object(llm,'_call_deepseek',side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt): self.call()
        self.assertEqual(self.rows()[0]['ok'],0)
    def test_summary_separates_failure_from_unknown_usage(self):
        event={'choices':[{'delta':{'content':'partial'},'finish_reason':'length'}],
               'usage':{'prompt_tokens':100,'completion_tokens':100}}
        with patch.object(llm.httpx,'stream',return_value=Stream([event])):
            with self.assertRaises(llm.Truncated): self.call()
        output=io.StringIO()
        with contextlib.redirect_stdout(output): run._summary(self.conn,self.rid)
        self.assertNotIn('NIEZNANYM',output.getvalue())
        with patch.object(llm.httpx,'stream',return_value=Stream([
                {'choices':[{'delta':{'content':'ok'},'finish_reason':'stop'}]}])):
            self.call()
        output=io.StringIO()
        with contextlib.redirect_stdout(output): run._summary(self.conn,self.rid)
        self.assertIn('NIEZNANYM koszcie: 1',output.getvalue())
        self.assertIn('dodatkowa rezerwacja:',output.getvalue())


if __name__ == '__main__': unittest.main()
