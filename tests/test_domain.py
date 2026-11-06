import sys
from pathlib import Path
from fractions import Fraction
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

def test_mapping():
    from core import score_value, points
    for raw, score in [('优',95),('良',85),('中等',75),('合格',65),('及格',65),('８９',89)]:
        assert score_value(raw) == score
    assert [points(x) for x in [60,89,90,100]] == [Fraction(1),Fraction(39,10),Fraction(4),Fraction(4)]

@pytest.mark.parametrize('value', ['59','101','89.5','','NaN','inf','-1'])
def test_invalid_scores(value):
    from core import score_value
    with pytest.raises(ValueError): score_value(value)

def test_weighted_and_precision():
    from core import aggregate, baseline, compare
    assert aggregate([('3',80),('1',90)]) == (Fraction(13), Fraction(4))
    assert aggregate([('1',80),('1',100)])[0] / 2 == Fraction(7,2)
    assert compare(baseline('10000','3.50001'), baseline('10000','3.5')) == 1

def test_strict_solver():
    from core import baseline, solve
    assert solve(baseline('3','3'), baseline('3','3'), '3','3',80)['minimum'] == 81
    assert solve(baseline('3','3'), baseline('3','3'), '3','3',90)['status'] == 'tie'
    assert solve(baseline('3','2.9'), baseline('3','3'), '3','3',90)['status'] == 'impossible'
    assert solve(baseline('3','4'), baseline('3','3'), '3','3',80)['minimum'] == 71
    assert solve(baseline('6','3'), baseline('3','4'), '3','3',60)['minimum'] == 66
    assert solve((Fraction(43),Fraction(12)),(Fraction(449,10),Fraction(12)),3,3,80)['minimum'] == 87

def test_simulation_bounds_and_plateau():
    from core import baseline, simulate
    rows = [{'name':'A','a_credit':'3','b_credit':'3','a_score':90,'b_score':80,'a_take':True,'b_take':True}]
    r = simulate(baseline('3','3'), baseline('3','3'), rows)
    assert r['relation'] == 1 and r['maximum_relation'] == 1
    rows[0]['a_score'] = 100
    assert simulate(baseline('3','3'),baseline('3','3'),rows)['a'] == r['a']

@pytest.mark.parametrize('credit', ['0','-1','1.001','NaN','inf'])
def test_invalid_credit(credit):
    from core import credit_value
    with pytest.raises(ValueError): credit_value(credit)

def test_import_semesters_labels_and_exclusions():
    from importer import parse_rows
    rows = [['主修成绩'],['学期','课程名称','课程代码','学分','有效成绩'],
            ['2026春','测试课程','A1','3','优'],['','大学英语（国家四级）','CET4','0','527'],
            ['','另一课程','A2','2','及格'],['','错误课程','A3','2','未知'],
            ['加权平均分: 88','','绩点: 3.5','','']]
    result = parse_rows(rows)
    assert len(result['courses']) == 4
    assert result['courses'][2]['term'] == '2026春'
    assert result['courses'][0]['score'] == 95
    assert result['courses'][1]['included'] == 0
    assert result['courses'][2]['score'] == 65
    assert result['courses'][3]['included'] == 0
    assert result['warnings']
    assert result['summary']['gpa'] == '3.5'

def test_storage_transactions_snapshots_backup(tmp_path):
    from storage import Store
    s = Store(tmp_path/'test.db')
    c = dict(term='春',name='测试',code='A',credit='3',raw='优',score=95,included=1,reason='')
    assert s.import_courses([c]) == (1,0,0)
    assert s.import_courses([c]) == (0,0,1)
    c2 = dict(c,raw='良',score=85)
    assert s.import_courses([c2]) == (0,1,0)
    sid = s.save_scenario('试算',{'a':'3.5','rows':[]})
    assert s.scenario(sid)['a'] == '3.5'
    s.backup(tmp_path/'backup.db')
    s.delete_course(s.courses()[0]['id'])
    assert not s.courses()
    s.restore(tmp_path/'backup.db')
    assert s.courses()[0]['score'] == 85
    s.close()

def test_storage_invalid_batch_rollback(tmp_path):
    from storage import Store
    s=Store(tmp_path/'test.db')
    c=dict(term='春',name='A',code='A',credit='3',raw='80',score=80,included=1,reason='')
    with pytest.raises(ValueError): s.import_courses([c,dict(c,name='B',credit='-1')])
    assert not s.courses()

def test_reimport_preserves_exclusion():
    from importer import parse_rows
    result=parse_rows([['学期','课程名称','课程代码','学分','有效成绩','是否计入','排除原因'],
        ['春','测试','A','3','85','0','重修记录手动排除']])
    assert result['courses'][0]['included']==0
    assert result['courses'][0]['reason']=='重修记录手动排除'

def test_future_empty_peer_and_solver_properties():
    from core import baseline,solve,add,compare
    for a_gpa in ['1','2.3','3.9','4']:
        for b_gpa in ['1','2.5','4']:
            for ac,bc in [(1,3),(3,1),(12,12)]:
                a=baseline(ac,a_gpa);b=baseline(bc,b_gpa)
                answer=solve(a,b,2,None,None)
                legal=[s for s in range(60,101) if compare(add(a,2,s),b)>0]
                assert answer['minimum']==(legal[0] if legal else None)

def test_restore_corrupt_preserves_db(tmp_path):
    from storage import Store
    s=Store(tmp_path/'store.db');s.save_peer('A',dict(credit='3',value='3',mode=0))
    bad=tmp_path/'bad.db';bad.write_bytes(b'bad')
    with pytest.raises(Exception):s.restore(bad)
    assert len(s.peers())==1
    s.close()

def test_policy_course_is_excluded():
    from importer import parse_rows
    r=parse_rows([['学期','课程名称','课程代码','学分','有效成绩'],
        ['春','形势与政策（III）','POLICY','0.25','90'],['春','普通课程','A','3','85']])
    assert r['courses'][0]['included']==0
    assert '形势与政策' in r['courses'][0]['reason']
    assert r['courses'][1]['included']==1

def test_xlsx_reader(tmp_path):
    # Minimal OOXML fixture for the read adapter, not a user-facing workbook.
    from zipfile import ZipFile
    from xml.sax.saxutils import escape
    from importer import read_transcript
    rows=[['学期','课程名称','课程代码','学分','有效成绩'],['2026春','合成课程','X1','3','良']]
    sheet=''.join('<row r="'+str(i)+'">'+''.join('<c r="'+chr(65+j)+str(i)+'" t="inlineStr"><is><t>'+escape(v)+'</t></is></c>' for j,v in enumerate(row))+'</row>' for i,row in enumerate(rows,1))
    path=tmp_path/'sample.xlsx'
    with ZipFile(path,'w') as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="成绩" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+sheet+'</sheetData></worksheet>')
    result=read_transcript(path)[0]
    assert result['courses'][0]['score']==85
