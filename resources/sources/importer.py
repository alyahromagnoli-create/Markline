"""Read-only local transcript recognition; spreadsheet content is never executed."""
import csv
import re
from pathlib import Path
from core import score_value, credit_value, decimal_value

ALIASES={'term':['学期','学年学期','开课学期'],'name':['课程名称','课程名'],
         'code':['课程代码','课程编号'],'credit':['学分','课程学分'],
         'raw':['有效成绩','成绩','总评成绩','最终成绩'],
         'included':['是否计入'],'reason':['排除原因']}

def text(x):
    return str(x if x is not None else '').strip()

def is_cet(name,code):
    t=(name+' '+code).upper()
    return bool(re.search(r'CET|英语.*[四六４６46]级|大学英语.*国家[四六]级|大学英语.*[（(][四六46][）)]',t))

def excluded_course(name,code):
    if is_cet(name,code):return '四六级成绩不参与统计'
    if '形势与政策' in ''.join(name.split()):return '形势与政策不参与统计'
    return ''

def parse_rows(rows):
    header=None; mapping={}; summary={}; warnings=[]; courses=[]; term='未标注学期'
    for i,row in enumerate(rows[:50]):
        normalized=[text(x).replace(' ','') for x in row]
        found={k:next((normalized.index(a) for a in aliases if a in normalized),None) for k,aliases in ALIASES.items()}
        if all(found[k] is not None for k in ['name','credit','raw']):
            header=i; mapping=found; break
    if header is None: raise ValueError('未识别到表头，需要课程名称、学分、成绩三列。请使用模板或检查工作表。')
    for index,row in enumerate(rows[header+1:],header+2):
        combined=' '.join(text(x) for x in row)
        if not combined.strip(): continue
        is_summary=bool(re.search(r'加权平均分\s*[:：]|(?:平均绩点|绩点)\s*[:：]|专业排名\s*[:：]|年级排名\s*[:：]',combined))
        if is_summary:
            for key,pattern in [('gpa',r'(?:平均绩点|绩点)\s*[:：]\s*(\d+(?:\.\d+)?)'),('average',r'加权平均分\s*[:：]\s*(\d+(?:\.\d+)?)')]:
                match=re.search(pattern,combined)
                if match: summary[key]=match.group(1)
            continue
        def get(key):
            col=mapping.get(key)
            return text(row[col]) if col is not None and col<len(row) else ''
        name=get('name')
        if not name: continue
        if get('term'): term=get('term')
        code=get('code'); raw=get('raw'); credit=get('credit')
        reason=''; score=None
        if excluded_course(name,code): reason=excluded_course(name,code)
        else:
            try:
                if decimal_value(credit)==0: reason='零学分课程'
                else: credit_value(credit)
            except ValueError as e: reason=f'学分待处理：{e}'
            try: score=score_value(raw)
            except ValueError:
                if not reason: reason='成绩待处理：不支持或缺失的成绩'
        if reason.startswith(('学分待处理','成绩待处理')): warnings.append(f'第{index}行 {name}：{reason}')
        if get('included') in ['0','否','不计入'] and not reason:
            reason=get('reason') or '用户指定不计入'
        courses.append(dict(term=term,name=name,code=code,credit=credit,raw=raw,score=score,
                            included=int(not reason),reason=reason))
    if not courses: raise ValueError('识别到表头，但没有可导入的课程')
    return dict(courses=courses,warnings=warnings,summary=summary)

def read_transcript(path):
    p=Path(path); suffix=p.suffix.lower(); result=[]
    if suffix=='.xls':
        import xlrd
        book=xlrd.open_workbook(str(p))
        tables=[(s.name,[s.row_values(i) for i in range(s.nrows)]) for s in book.sheets()]
    elif suffix=='.xlsx':
        from openpyxl import load_workbook
        book=load_workbook(p,read_only=True,data_only=True,keep_links=False)
        try: tables=[(s.title,list(s.iter_rows(values_only=True))) for s in book.worksheets]
        finally: book.close()
    elif suffix=='.csv':
        try: contents=p.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError: contents=p.read_text(encoding='gb18030')
        tables=[(p.stem,list(csv.reader(contents.splitlines())))]
    else: raise ValueError('仅支持XLS、XLSX、CSV文件')
    failures=[]
    for name,rows in tables:
        try:
            value=parse_rows(rows); value['sheet']=name; result.append(value)
        except ValueError as e: failures.append(f'{name}：{e}')
    if not result: raise ValueError('\n'.join(failures))
    # Multiple valid sheets are presented individually by the UI.
    return result
