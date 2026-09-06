"""Local panel operations. Reuses the engine's preset contract and validation."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
INHERITED_ACCOUNT = {k: v for k, v in os.environ.items() if k in ('ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'SUBSTACK_HANDLE', 'NAZWA_MARKI')}
sys.path.insert(0, str(ROOT / 'agent-v2'))
os.environ['AGENT_V2_BEZ_KONFIGURACJI'] = '1'
import config
import konfiguracja
import preset
import style
from dotenv import dotenv_values, set_key

PUBLIC = {'ai', 'hidden-bill', 'SZABLON'}
KEYS = ('ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY')
ACCOUNT = ('SUBSTACK_HANDLE', 'NAZWA_MARKI')
FORMS = ('positive', 'negative', 'corpus')
ASSETS = {'positive': 'styl/profil_pozytywny.md', 'negative': 'styl/profil_negatywny.md', 'corpus': 'styl/korpus.txt'}
SLUG = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')


class PanelError(ValueError):
    """A reviewable validation error rather than an HTTP traceback."""


@contextmanager
def file_lock(path):
    """Use the same lock byte as run.py; never overwrite its contents."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    try:
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise PanelError('Another NIA operation is running. Wait for it to finish.') from exc
        yield
    finally:
        handle.close()


def atomic_json(path, value):
    preset._zapisz_atomowo(Path(path), json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class Panel:
    """One checkout, one active instance. All writes are serialized."""

    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.agent = self.root / 'agent-v2'
        self.presets = self.root / 'presety'
        self.state = self.agent / 'data' / 'panel'
        self.mutex = threading.RLock()
        self.job = None
        self.initial_env = dict(INHERITED_ACCOUNT)
        if (self.state / 'preset-transaction.json').exists():
            with self.editing():
                self.recover_save()

    def recover_save(self):
        """Roll back an interrupted directory swap before accepting another edit."""
        journal = self.state / 'preset-transaction.json'
        if not journal.exists():
            return
        data = json.loads(journal.read_text(encoding='utf-8'))
        target = self.directory(data['name'])
        backup = self.safe_path(self.root / data['backup'])
        if backup.exists() or not data['existed']:
            if target.exists():
                failed = self.safe_path(backup.parent / (data['name'] + '-interrupted-' + uuid.uuid4().hex[:8]))
                os.replace(target, failed)
            if backup.exists():
                os.replace(backup, target)
        if data['pointer']:
            atomic_json(preset.wskaznik(self.agent), data['pointer'])
        journal.unlink()

    def env(self):
        values = {}
        for file in (self.root / '.env', self.agent / '.env'):
            if file.is_file():
                values.update({k: v for k, v in dotenv_values(file).items() if v is not None})
        values.update(self.initial_env)
        # Older private presets can carry their own account instead of .env.
        try:
            pointer = preset.czytaj_wskaznik(self.agent)
            if pointer:
                pr = preset.wczytaj(self.safe_path(self.root / pointer['plik']))
                for env_key, field in [('SUBSTACK_HANDLE', 'konto.uchwyt'), ('NAZWA_MARKI', 'konto.nazwa_marki')]:
                    if env_key not in values:
                        values[env_key] = pr.pola.get(field, '')
        except (ValueError, OSError, preset.BladPresetu):
            pass  # status reports activation errors separately; the editor remains available.
        return values

    def safe_path(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise PanelError('This preset references a file outside the checkout.')
        return path

    def directory(self, name):
        if not isinstance(name, str) or not SLUG.fullmatch(name):
            raise PanelError('Use a name containing lowercase letters, numbers, hyphens or underscores.')
        path = self.safe_path(self.presets / name)
        if path.parent != self.presets.resolve():
            raise PanelError('Invalid preset directory.')
        return path

    def revision(self, directory):
        digest = hashlib.sha256()
        for p in sorted(Path(directory).rglob('*')):
            if p.is_symlink():
                raise PanelError('Linked preset files are not supported by the panel.')
            if p.is_file():
                digest.update(p.relative_to(directory).as_posix().encode())
                digest.update(p.read_bytes().replace(b'\r\n', b'\n'))
        return digest.hexdigest()

    def active(self):
        return preset.aktywacja(self.agent, {})

    def listing(self):
        result = []
        for directory in sorted(self.presets.iterdir()):
            if directory.name == 'SZABLON' or not (directory / 'preset.toml').is_file():
                continue
            try:
                pr = preset.wczytaj(self.safe_path(directory / 'preset.toml'))
                result.append({'id': directory.name, 'name': pr.nazwa, 'description': pr.opis, 'public': directory.name in PUBLIC})
            except (ValueError, preset.BladPresetu):
                result.append({'id': directory.name, 'name': directory.name, 'description': 'Invalid preset; inspect files.', 'public': directory.name in PUBLIC})
        return result

    def read(self, name):
        directory = self.directory(name)
        raw = json.loads(json.dumps(__import__('tomllib').loads((directory / 'preset.toml').read_text(encoding='utf-8'))))
        fields = konfiguracja.splaszcz({k: v for k, v in raw.items() if k != 'preset'}, name)
        pr = preset.wczytaj(directory / 'preset.toml')
        resolved, _ = preset.rozwiaz(pr, config, config.DOMYSLNE_SILNIKA, {})
        assets = {}
        for label, field in [('positive', 'STYLE_PROFILE_POSITIVE'), ('negative', 'STYLE_PROFILE_NEGATIVE'), ('corpus', 'STYLE_CORPUS')]:
            path = self.safe_path(getattr(resolved, field))
            assets[label] = path.read_text(encoding='utf-8') if path.is_file() else ''
        pin_file = self.safe_path(Path(resolved.STYLE_CORPUS).parent / 'przypiecia.json')
        pins = json.loads(pin_file.read_text(encoding='utf-8')) if pin_file.is_file() else {}
        return {'id': name, 'meta': raw['preset'], 'fields': fields, 'prompts': pr.bloki,
                'assets': assets, 'pins': {p['funkcja']: p['akapit'] for p in pins.get('przyklady', [])},
                'revision': self.revision(directory), 'models': dict(resolved.MODEL_FOR), 'public': name in PUBLIC}

    @contextmanager
    def editing(self, instance=None):
        with self.mutex, file_lock(self.state / 'config.lock'):
            if (self.job_status() or {}).get('running'):
                raise PanelError('Wait for the current panel operation before changing configuration.')
            pointer = preset.czytaj_wskaznik(self.agent)
            ids = {str(pointer['instancja'])} if pointer else set()
            if instance:
                ids.add(instance)
            with ExitStack() as stack:
                for name in sorted(ids):
                    if not SLUG.fullmatch(name):
                        raise PanelError('Invalid instance ID.')
                    stack.enter_context(file_lock(self.agent / 'instancje' / name / 'agent.lock'))
                yield

    def stage(self, payload, stage):
        name = payload.get('name', '')
        self.directory(name)
        source = payload.get('source')
        if source:
            source_dir = self.directory(source)
            if payload.get('revision') != self.revision(source_dir):
                raise PanelError('Preset changed on disk. Reload it before saving.')
            shutil.copytree(source_dir, stage, dirs_exist_ok=True, symlinks=False)
        fields = copy.deepcopy(payload.get('fields', {}))
        if not isinstance(fields, dict):
            raise PanelError('Preset fields must be an object.')
        # New copies are neutral. Preserve legacy identity when editing in place;
        # .env overrides it, but older installations may not have those overrides.
        if source == name and source not in PUBLIC:
            original = self.read(source)['fields']
            fields['konto.uchwyt'] = original.get('konto.uchwyt', 'your-handle')
            fields['konto.nazwa_marki'] = original.get('konto.nazwa_marki', 'Your Publication')
        else:
            fields['konto.uchwyt'] = 'your-handle'
            fields['konto.nazwa_marki'] = 'Your Publication'
        assets = payload.get('assets', {})
        for key in FORMS:
            text = assets.get(key, '')
            if not isinstance(text, str):
                raise PanelError('Style assets must contain text.')
            path = stage / ASSETS[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.replace('\r\n', '\n'), encoding='utf-8')
        fields['styl.profil_pozytywny'] = ASSETS['positive']
        fields['styl.profil_negatywny'] = ASSETS['negative']
        fields['styl.korpus'] = ASSETS['corpus'] if assets.get('corpus', '').strip() else ''
        fields['styl.wymagaj_korpusu'] = bool(assets.get('corpus', '').strip())
        if not assets.get('corpus', '').strip():
            (stage / ASSETS['corpus']).unlink(missing_ok=True)
            (stage / 'styl/przypiecia.json').unlink(missing_ok=True)
        else:
            raw = (stage / ASSETS['corpus']).read_bytes()
            paragraphs = style.split_paragraphs(raw)
            chosen = payload.get('pins', {})
            pins = []
            for role in style.FUNKCJE_STYLU:
                n = chosen.get(role)
                if type(n) is not int or n < 0 or n >= len(paragraphs):
                    raise PanelError('Choose a valid paragraph for each of the five style roles.')
                if not style.MIN_EXAMPLE_CHARS <= len(paragraphs[n]) <= style.MAX_EXAMPLE_CHARS:
                    raise PanelError('Each pinned style example must contain 150–900 characters.')
                pins.append({'funkcja': role, 'akapit': n, 'skrot': hashlib.sha256(paragraphs[n].encode()).hexdigest()[:10]})
            atomic_json(stage / 'styl/przypiecia.json', {'plik': 'korpus.txt', 'korpus_sha256': hashlib.sha256(style.bajty_kanoniczne(raw)).hexdigest(), 'akapitow': len(paragraphs), 'przyklady': pins})
        if source:
            previous = self.read(source)
            if previous['assets'].get('corpus') != assets.get('corpus'):
                (stage / 'styl/KORPUS_ZRODLA.md').write_text('Custom writing examples supplied by the operator.\n', encoding='utf-8')
        prompts = payload.get('prompts', {})
        if not isinstance(prompts, dict) or set(prompts) - set(preset.BLOKI):
            raise PanelError('Unknown prompt block.')
        (stage / 'prompty').mkdir(exist_ok=True)
        for key in preset.BLOKI:
            text = prompts.get(key, '')
            if not isinstance(text, str):
                raise PanelError('Prompt blocks must contain text.')
            # Always preserve a delimiter: the loader treats text before --- as a heading.
            (stage / 'prompty' / (key + '.md')).write_text('# ' + key + '\n\n---\n\n' + text, encoding='utf-8')
        try:
            normalized = konfiguracja.sprawdz_plaskie(fields, 'panel')
        except konfiguracja.BledKonfiguracji as exc:
            raise PanelError(str(exc)) from exc
        meta = {'nazwa': name, 'schema': 1, 'opis': str(payload.get('description', '')), 'wersja': '1'}
        (stage / 'preset.toml').write_text(konfiguracja.zapisz_toml(normalized, sekcje_dodatkowe={'preset': meta}), encoding='utf-8')
        pr = preset.wczytaj(stage / 'preset.toml')
        errors, warnings = preset.sprawdz(pr, config, config.DOMYSLNE_SILNIKA, self.env())
        if errors:
            raise PanelError('\n'.join(errors))
        return pr, warnings

    def save(self, payload, validate_only=False):
        name = payload.get('name', '')
        target = self.directory(name)
        if name in PUBLIC:
            raise PanelError('Bundled presets are read-only. Choose a new name for your private copy.')
        with self.editing():
            self.recover_save()
            self.state.mkdir(parents=True, exist_ok=True)
            if target.exists() and payload.get('source') != name:
                raise PanelError('A preset with this name exists. Load it or use a new name.')
            with tempfile.TemporaryDirectory(prefix='stage-', dir=self.state) as temp:
                stage = Path(temp) / name
                stage.mkdir()
                pr, warnings = self.stage(payload, stage)
                if validate_only:
                    return {'valid': True, 'warnings': warnings}
                previous_pointer = preset.czytaj_wskaznik(self.agent)
                active_same = previous_pointer and previous_pointer.get('preset') == name
                if active_same:
                    errors, more = preset.sprawdz(pr, config, config.DOMYSLNE_SILNIKA, self.env(), do_aktywacji=True)
                    if errors:
                        raise PanelError('\n'.join(errors))
                backup = self.safe_path(self.state / 'backups' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]) / name)
                backup.parent.mkdir(parents=True, exist_ok=True)
                journal = self.state / 'preset-transaction.json'
                atomic_json(journal, {'name': name, 'backup': str(backup.relative_to(self.root)),
                                     'existed': target.exists(), 'pointer': previous_pointer})
                if target.exists():
                    os.replace(self.safe_path(target), backup)
                try:
                    os.replace(self.safe_path(stage), target)
                    if active_same:
                        preset.podlacz(target / 'preset.toml', self.agent, config, config.DOMYSLNE_SILNIKA,
                                       instancja=previous_pointer['instancja'], srodowisko=self.env())
                except BaseException:
                    if target.exists():
                        failed = self.safe_path(backup.parent / (name + '-failed'))
                        os.replace(self.safe_path(target), failed)
                    if backup.exists():
                        os.replace(backup, target)
                    if previous_pointer:
                        atomic_json(preset.wskaznik(self.agent), previous_pointer)
                    journal.unlink(missing_ok=True)
                    raise
                journal.unlink()
                return {'preset': self.read(name), 'warnings': warnings, 'reactivated': bool(active_same), 'backup': str(backup.relative_to(self.root)) if backup.exists() else None}

    def activate(self, name, instance):
        self.directory(name)
        if not isinstance(instance, str) or not SLUG.fullmatch(instance):
            raise PanelError('Choose an instance ID using lowercase letters, numbers, hyphens or underscores.')
        with self.editing(instance):
            act, warnings = preset.podlacz(self.directory(name) / 'preset.toml', self.agent, config,
                config.DOMYSLNE_SILNIKA, instancja=instance, srodowisko=self.env())
            return {'active': act.preset.nazwa, 'instance': act.instancja, 'warnings': warnings}

    def account(self, payload):
        allowed = {*KEYS, *ACCOUNT}
        if set(payload) - allowed or not all(isinstance(v, str) for v in payload.values()):
            raise PanelError('Unknown account field.')
        if any('\n' in v or '\r' in v or '\0' in v for v in payload.values()):
            raise PanelError('Account values must occupy one line.')
        if payload.get('SUBSTACK_HANDLE') and not re.fullmatch(r'[a-zA-Z0-9_-]+', payload['SUBSTACK_HANDLE']):
            raise PanelError('Enter the profile handle without @ or a URL.')
        with self.editing():
            pointer = preset.czytaj_wskaznik(self.agent)
            current = self.env()
            if pointer and payload.get('SUBSTACK_HANDLE', current.get('SUBSTACK_HANDLE')) != current.get('SUBSTACK_HANDLE'):
                raise PanelError('An instance is active. Use a separate installation for another account.')
            blocked = set(payload) & set(self.initial_env)
            if blocked:
                raise PanelError('Exported environment values override these fields: ' + ', '.join(sorted(blocked)))
            path = self.agent / '.env'
            self.state.mkdir(parents=True, exist_ok=True)
            if path.exists():
                backup = self.state / 'backups' / ('account-' + uuid.uuid4().hex + '.env')
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            with tempfile.NamedTemporaryFile(dir=self.state, suffix='.env', delete=False) as f:
                temp = Path(f.name)
            try:
                temp.write_text(path.read_text(encoding='utf-8') if path.exists() else 'DRY_RUN=true\n', encoding='utf-8')
                for key, value in payload.items():
                    if key in KEYS and not value.strip():
                        continue  # Blank key fields preserve the current credential.
                    set_key(str(temp), key, value.strip(), quote_mode='always')
                os.chmod(temp, 0o600)
                os.replace(temp, path)
            finally:
                temp.unlink(missing_ok=True)
        return {'saved': True}

    def status(self):
        env = self.env()
        error = ''
        try:
            act = self.active()
        except (ValueError, preset.BladPresetu) as exc:
            act = None
            error = str(exc)
        data = {'active': act.preset.nazwa if act else None, 'instance': act.instancja if act else None,
                'account': {k: env.get(k, '') for k in ACCOUNT}, 'keys': {k: bool(env.get(k)) for k in KEYS},
                'error': error, 'session_saved': bool(act and (act.katalog_danych / 'storage-state.json').is_file()),
                'job': self.job_status(), 'presets': self.listing(),
                'models': sorted(k for k in config.PRICING if k.startswith(('deepseek-', 'claude-'))),
                'roles': {k: v for k, v in config.MODEL_FOR.items() if k != 'obraz'}}
        return data

    def job_status(self):
        record = self.state / 'job.json'
        if record.exists():
            data = json.loads(record.read_text(encoding='utf-8'))
            if self.job and data.get('id') != self.job['id']:
                self.job = None
        if not self.job:
            if not record.exists():
                return None
            data = json.loads(record.read_text(encoding='utf-8'))
            if not re.fullmatch(r'[0-9a-f]{32}', str(data.get('id', ''))):
                raise PanelError('Invalid job record.')
            self.job = {**data, 'log': self.state / (data['id'] + '.log')}
        process = self.job.get('process')
        code = process.poll() if process else None
        finished = self.state / (self.job['id'] + '.result.json')
        if finished.exists():
            code = json.loads(finished.read_text(encoding='utf-8'))['exit_code']
        elif not process:
            try:
                with file_lock(self.state / (self.job['id'] + '.lock')):
                    if time.time() - self.job.get('started', 0) > 10:
                        code = 1  # Interrupted before writing a completion record.
            except PanelError:
                pass
        try:
            raw = self.job['log'].read_bytes()[-24000:].decode('utf-8', errors='replace')
        except OSError:
            raw = ''
        for value in self.env().values():
            if isinstance(value, str) and len(value) >= 16:
                raw = raw.replace(value, '[redacted]')
        raw = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}', '[redacted]', raw)
        return {'id': self.job['id'], 'action': self.job['action'], 'running': code is None, 'exit_code': code, 'log': raw}

    def start(self, action):
        commands = {'check': ['narzedzia/panel_worker.py', 'check'], 'login': ['narzedzia/panel_worker.py', 'login'],
            'session': ['narzedzia/panel_worker.py', 'session'], 'dry': ['narzedzia/panel_worker.py', 'dry'],
            'daily-draft': ['narzedzia/panel_worker.py', 'daily-draft'], 'daily-publish': ['narzedzia/panel_worker.py', 'daily-publish'],
            'article-draft': ['narzedzia/panel_worker.py', 'article-draft'], 'article-publish': ['narzedzia/panel_worker.py', 'article-publish'],
            'costs': ['narzedzia/panel_worker.py', 'costs']}
        if action not in commands:
            raise PanelError('Unknown operation.')
        with self.mutex:
            if (self.job_status() or {}).get('running'):
                raise PanelError('A panel operation is already running.')
            act = self.active()
            if not act:
                raise PanelError('Activate a preset before starting the bot.')
            if action.endswith(('-draft', '-publish')):
                pr, _ = preset.rozwiaz(act.preset, config, config.DOMYSLNE_SILNIKA, self.env())
                required = {preset._dostawca(model) for role, model in pr.MODEL_FOR.items() if role != 'obraz'}
                required.add(preset._dostawca(pr.ZAPASOWY_PISARZ))
                if pr.OBRAZ_WLACZONY:
                    required.add('openai')
                missing = [key for provider, key in [('deepseek', 'DEEPSEEK_API_KEY'), ('anthropic', 'ANTHROPIC_API_KEY'), ('openai', 'OPENAI_API_KEY')] if provider in required and not self.env().get(key)]
                if missing:
                    raise PanelError('Missing API keys: ' + ', '.join(missing))
            with file_lock(self.state / 'config.lock'), file_lock(act.katalog_danych / 'agent.lock'):
                env = dict(os.environ)
                for k in (*KEYS, *ACCOUNT, 'AGENT_V2_BEZ_KONFIGURACJI', 'AGENT_V2_PRESET', 'AGENT_V2_KONFIGURACJA_TOML', 'AGENT_V2_NO_LIMIT'):
                    env.pop(k, None)
                env.update(self.env())
                env.pop('AGENT_V2_BEZ_KONFIGURACJI', None)
                env.pop('AGENT_V2_PRESET', None)
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUNBUFFERED'] = '1'
                env['DRY_RUN'] = 'false' if action.endswith(('-draft', '-publish')) else 'true'
                self.state.mkdir(parents=True, exist_ok=True)
                job_id = uuid.uuid4().hex
                env['NIA_PANEL_JOB'] = job_id
                log = self.state / (job_id + '.log')
                # The subprocess acquires its instance lock after this scope releases it.
                with log.open('wb') as output:
                    child = subprocess.Popen([sys.executable, *commands[action]], cwd=self.root, env=env,
                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                record = {'action': action, 'id': job_id, 'started': time.time()}
                atomic_json(self.state / 'job.json', record)
                self.job = {'process': child, 'log': log, **record}
            return self.job_status()
