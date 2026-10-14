import io
import zipfile
import xml.dom.minidom

import pytest

from app.voice import report as r

RAW = {'kind': 'internal', 'client': 'Ignored?', 'project': None,
       'participants': {'client': ['Solène'], 'equadis': ['Roméo', '']},
       'fr': {'title': 'API', 'objective': 'Présenter.', 'overview': 'Ça va.',
              'points': ['Un point simple', {'text': 'Erreurs', 'details': ['Logistique rejetée', '']}],
              'decisions': [], 'actions': [{'action': 'Partager le XML', 'owner': 'Equadis', 'status': 'Fait',
                                            'deadline': '20/07/2026'}, {'action': ''}],
              'openQuestions': [], 'nextMeeting': None},
       'en': {'title': 'API', 'objective': 'Present.', 'overview': 'Fine.', 'points': [], 'decisions': ['One file'],
              'actions': [], 'openQuestions': ['When?'], 'nextMeeting': 'Next week'}}


def test_the_user_wins_and_bad_items_are_dropped():
    d = r.clean(RAW, {'client': 'MyOrigines'})
    assert d['kind'] == 'client' and d['client'] == 'MyOrigines'
    assert d['fr']['points'][0] == {'text': 'Un point simple', 'details': []}
    assert d['fr']['points'][1]['details'] == ['Logistique rejetée']
    assert len(d['fr']['actions']) == 1 and d['participants']['equadis'] == ['Roméo']


def test_empty_answer_is_refused():
    with pytest.raises(ValueError):
        r.clean({'fr': {}, 'en': {}})


def test_prompt_asks_for_both_languages_and_the_pv_style():
    p = r.prompt('[00:00:01] مرحبا', {'kind': 'client', 'client': 'MyOrigines'})
    flat = ' '.join(p.split())
    assert '"fr" in French and "en" in English' in flat and 'Faire suite au 2ème workshop' in flat
    assert 'Kind (given): client' in p and p.rstrip().endswith('</transcript>')
    assert '"required"' in p and '"required"' not in r.prompt('x', schema=False)


def test_docx_is_a_valid_word_file_with_both_languages():
    d = r.clean(RAW, {'client': 'MyOrigines'})
    meta = {'date': '17/07/2026', 'time': '10h – 11h', 'author': 'Roméo Saad'}
    z = zipfile.ZipFile(io.BytesIO(r.docx(d, meta)))
    body = z.read('word/document.xml').decode()
    for name in z.namelist():
        if name.endswith('.xml') or name.endswith('.rels'):
            xml.dom.minidom.parseString(z.read(name))          # well-formed
    assert 'RAPPORT DE RÉUNION' in body and 'MEETING REPORT' in body and 'PV – 20260717' in body
    assert r.file_name(d, meta) == 'MyOrigines x Equadis PV-20260717.docx'
    md = r.markdown(d, meta)
    assert '| Partager le XML | Equadis | Fait | 20/07/2026 |' in md and '## Next meeting\nNext week' in md


def test_chunks_respect_the_byte_limit():
    text = '\n'.join('é' * 30 for _ in range(100))
    parts = r.chunks(text, 200)
    assert all(len(p.encode()) <= 200 for p in parts) and '\n'.join(parts) == text
