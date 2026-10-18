"""Reviewed sound patterns remain separate from catalog identity and shared names."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
import build_observatory as obs
from test_observatory import fixture
from test_build_site import Page


class NameRhymeTests(unittest.TestCase):
    def rows(self):
        base=obs.project_index(fixture())['projects'][0]
        return [dict(base,id=str(i),name=name,url='https://example.com/'+str(i),
                     rhyme=dict(key='AE1 T',onset=onset,pronunciation=onset+' AE1 T',language='en-US'))
                for i,(name,onset) in enumerate([('OpenChat','CH'),('OpenChat','CH'),('OpenCat','K'),('OpenVat','V')])]

    def test_unique_identity_duplicate_names_and_filter_survivors(self):
        rows=self.rows(); result=obs.rhyming_names(rows+rows)
        self.assertEqual(result['tool_count'],4)
        self.assertEqual(result['reviewed_count'],4)
        self.assertEqual(len(result['groups']),1)
        self.assertEqual(obs.shared_names(rows)['tool_count'],2)
        for selected in [[],rows[:1],rows[:2],rows[2:3]]:
            self.assertEqual(obs.rhyming_names(selected)['tool_count'],0)
        self.assertEqual(obs.rhyming_names(rows[1:3])['tool_count'],2)
        index=obs.project_index(fixture());index['projects']=rows
        self.assertEqual(obs.aggregate(index,rows[:2])['rhyming_names']['tool_count'],0)

    def test_aliases_spellings_and_homophones_never_infer_rhymes(self):
        rows=self.rows()
        for row in rows: row.pop('rhyme');row['aliases']=['OpenCat']
        self.assertEqual(obs.rhyming_names(rows)['tool_count'],0)
        rows=self.rows()[:2];rows[1]['name']='Open Chat'
        self.assertEqual(obs.rhyming_names(rows)['tool_count'],0)
        rows[1]['name']='OpenChatt'
        self.assertEqual(obs.rhyming_names(rows)['tool_count'],0)

    def test_render_is_native_escaped_and_separate(self):
        rows=self.rows();rows[0]['name']='Open<Chat>'
        html=obs.rhyming_names_html(obs.rhyming_names(rows)); page=Page(html)
        self.assertEqual(page.by_id['rhyme-groups'].tag,'details')
        self.assertNotIn('open',page.by_id['rhyme-groups'].attrs)
        self.assertEqual(page.by_id['rhyme-count'].text,'4')
        self.assertNotIn('Open<Chat>',html)
        self.assertIn('not official brand pronunciations',html)
        self.assertIn('not additive',html)
        self.assertIn('No reviewed rhyming names',obs.rhyming_names_html(obs.rhyming_names([])))

    def test_python_browser_group_parity(self):
        rows=self.rows()
        for selected in [rows, rows[:2], rows[1:3], [], rows+rows]:
            script="const obs=require('./site/observatory.js'); process.stdout.write(JSON.stringify(obs.rhymingNames("+json.dumps(selected)+")));"
            actual=json.loads(subprocess.check_output(['node','-e',script],text=True,cwd=Path(__file__).resolve().parents[1]))
            self.assertEqual(actual,obs.rhyming_names(selected))

    def test_review_validation_and_no_input_mutation(self):
        catalog=fixture();catalog['projects']=self.rows()
        row=dict(project_url=catalog['projects'][0]['url'],name='OpenChat',pronunciation='CH AE1 T',key='AE1 T',onset='CH',source_url='https://example.com/source')
        data=dict(schema_version=1,language='en-US',checked_at='2026-10-18',reviewed_by='Test',basis='Editorial assumption',projects=[row])
        before=deepcopy(catalog)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'names.json'
            self.assertEqual(obs.reviewed_rhymes(catalog,path),{})
            path.write_text(json.dumps(data));mapping=obs.reviewed_rhymes(catalog,path)
            self.assertEqual(mapping['0']['key'],'AE1 T');self.assertEqual(catalog,before)
            for change in [dict(name='Other'),dict(project_url='https://example.com/missing'),dict(key='at'),dict(onset='AE1'),dict(pronunciation='K AE1 T'),dict(source_url='http://example.com')]:
                broken=deepcopy(data);broken['projects'][0].update(change);path.write_text(json.dumps(broken))
                with self.subTest(change=change),self.assertRaises(ValueError):obs.reviewed_rhymes(catalog,path)
            broken=deepcopy(data);broken['projects']*=2;path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):obs.reviewed_rhymes(catalog,path)
            broken=deepcopy(data);broken['language']='unknown';path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):obs.reviewed_rhymes(catalog,path)

if __name__=='__main__':unittest.main()
