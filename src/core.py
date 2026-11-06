"""Exact offline grade arithmetic. No UI, database or float arithmetic."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import unicodedata

LABELS = {'优':95, '良':85, '中等':75, '合格':65, '及格':65}

def decimal_value(raw):
    try:
        value = Decimal(unicodedata.normalize('NFKC',str(raw)).strip())
        if not value.is_finite(): raise ValueError('请输入有限数值')
        return value
    except (InvalidOperation, TypeError):
        raise ValueError('请输入有效数字') from None

def score_value(raw):
    raw = unicodedata.normalize('NFKC',str(raw)).strip()
    if raw in LABELS: return LABELS[raw]
    n = decimal_value(raw)
    if n != n.to_integral_value() or not 60 <= n <= 100:
        raise ValueError('成绩须为60–100的整数，或优/良/中等/合格/及格')
    return int(n)

def credit_value(raw):
    n=decimal_value(raw)
    if n<=0 or n*100 != (n*100).to_integral_value():
        raise ValueError('学分须大于0，最多两位小数')
    return Fraction(n)

def points(score):
    return Fraction(min(score_value(score)-50,40),10)

def aggregate(rows):
    p=Fraction(0); c=Fraction(0)
    for credit,score in rows:
        u=credit_value(credit); p+=u*points(score); c+=u
    return p,c

def baseline(credit, value, mode='gpa'):
    c=credit_value(credit); v=Fraction(decimal_value(value))
    if mode=='gpa':
        if not 1<=v<=4: raise ValueError('当前规则下累计GPA须为1.0–4.0')
        return c*v,c
    if mode!='total': raise ValueError('未知绩点输入类型')
    if not c<=v<=4*c: raise ValueError('加权绩点总量须在总学分×1至总学分×4之间')
    return v,c

def gpa(pair):
    if pair[1]<=0: raise ValueError('没有计入GPA的有效学分')
    return pair[0]/pair[1]

def compare(a,b):
    d=gpa(a)-gpa(b)
    return (d>0)-(d<0)

def add(pair,credit,score):
    c=credit_value(credit)
    return pair[0]+c*points(score),pair[1]+c

def solve(a,b,a_credit,b_credit,b_score):
    bf=add(b,b_credit,b_score) if b_credit is not None else b
    found=None
    for score in range(60,101):
        af=add(a,a_credit,score)
        if compare(af,bf)>0:
            found=score; break
    maximum=add(a,a_credit,90)
    rel=compare(maximum,bf)
    return {'minimum':found,'status':'solved' if found is not None else ('tie' if rel==0 else 'impossible'),
            'a':add(a,a_credit,found) if found is not None else maximum,'b':bf,
            'previous':add(a,a_credit,found-1) if found and found>60 else None,
            'gap':found-score_value(b_score) if found is not None and b_credit is not None else None}

def simulate(a,b,rows):
    af,bf=a,b; low,high=a,a
    for row in rows:
        if row['a_take']:
            af=add(af,row['a_credit'],row['a_score'])
            low=add(low,row['a_credit'],60)
            high=add(high,row['a_credit'],90)
        if row['b_take']: bf=add(bf,row['b_credit'],row['b_score'])
    relation=compare(af,bf)
    return dict(a=af,b=bf,minimum=low,maximum=high,relation=relation,
                minimum_relation=compare(low,bf),maximum_relation=compare(high,bf))

def display(value,digits=4):
    value=Fraction(value)
    from decimal import localcontext
    with localcontext() as ctx:
        ctx.prec=max(40,len(str(abs(value.numerator)))+len(str(value.denominator))+digits+5)
        return f'{Decimal(value.numerator)/Decimal(value.denominator):.{digits}f}'
