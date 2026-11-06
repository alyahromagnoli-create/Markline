"""Three-page offline desktop UI. Database writes occur only on explicit actions."""
import csv
import json
from fractions import Fraction
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QFont,QIcon,QColor,QPainter,QPixmap,QPen,QDesktopServices
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QStackedWidget,QFrame,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,
    QComboBox,QFormLayout,QDialog,QDialogButtonBox,QCheckBox,QFileDialog,QMessageBox,QInputDialog,
    QScrollArea,QApplication)
from core import aggregate,baseline,gpa,display,points,score_value,credit_value,solve,simulate
from importer import read_transcript,excluded_course

STYLE='''
QWidget {font-family:"Microsoft YaHei UI";font-size:13px;color:#292D2A;}
QMainWindow, QDialog, QWidget#page {background:#FAFAF7;}
QFrame#sidebar {background:#EEF0EA;border-right:1px solid #D8DDD3;}
QFrame#card {background:transparent;border:0;border-top:1px solid #CBD1C6;border-radius:0;}
QLabel#title {font-size:24px;font-weight:600;color:#252C28;}
QLabel#brand {font-family:"Segoe UI";font-size:22px;font-weight:600;color:#2F453B;}
QLabel#subtle {color:#61695F;font-size:12px;}
QLabel#metric {font-size:25px;font-weight:500;color:#293D32;}
QPushButton {background:#FAFAF7;border:1px solid #C5CCC0;border-radius:2px;padding:6px 11px;min-height:20px;}
QPushButton:hover {background:#EBEFE5;border-color:#86957D;}
QPushButton:pressed {background:#DCE4D6;}
QPushButton:disabled {color:#858B80;border-color:#DDDFD8;}
QPushButton#primary {background:#364C3E;color:#FFFFFF;border:1px solid #364C3E;font-weight:500;}
QPushButton#primary:hover {background:#283C30;}
QPushButton#nav {text-align:left;border:0;border-bottom:1px solid transparent;padding:11px 10px;color:#5B6358;font-size:14px;}
QPushButton#nav:checked {background:#E0E6D9;color:#243D2D;border-bottom:1px solid #91A184;font-weight:600;}
QLineEdit,QComboBox {background:#FFFFFF;border:1px solid #C9CFC3;border-radius:1px;padding:6px;min-height:18px;selection-background-color:#DCE6D4;selection-color:#263729;}
QLineEdit:focus,QComboBox:focus {border:1px solid #536E48;}
QTableWidget {background:#FFFFFF;alternate-background-color:#F7F8F3;border:1px solid #D5DBCE;border-radius:0;gridline-color:#E8EBE2;selection-background-color:#E3EADB;selection-color:#263524;}
QHeaderView::section {background:#F1F3EC;color:#4D5846;border:0;border-bottom:1px solid #C9D1C0;padding:8px 5px;font-weight:500;}
QTableWidget::item {padding:5px;}
QScrollArea {border:0;background:transparent;}
QCheckBox {spacing:6px;}
QLabel#result {background:#F0F3E9;border:1px solid #CDD6C1;border-radius:1px;padding:13px;color:#2E412B;}
QStatusBar {background:#EEF0EA;border-top:1px solid #D8DDD3;color:#596151;}
QToolTip {background:#FAFAF7;color:#263524;border:1px solid #9BAB8F;padding:6px;}
'''

def icon():
    pix=QPixmap(128,128); pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor('#334B3D'));p.setPen(Qt.PenStyle.NoPen);p.drawRoundedRect(4,4,120,120,15,15)
    p.setPen(QPen(QColor('#F4F2DF'),9,Qt.PenStyle.SolidLine,Qt.PenCapStyle.SquareCap,Qt.PenJoinStyle.MiterJoin))
    p.drawLine(29,89,29,40);p.drawLine(29,40,58,70);p.drawLine(58,70,97,31)
    p.drawLine(78,31,97,31);p.drawLine(97,31,97,50)
    p.setPen(QPen(QColor('#AFBE9F'),3));p.drawLine(29,103,99,103)
    p.end();return QIcon(pix)

def label(text='',name=None,wrap=False):
    w=QLabel(text)
    if name:w.setObjectName(name)
    w.setWordWrap(wrap);return w

def button(text,callback,primary=False):
    w=QPushButton(text)
    if primary:w.setObjectName('primary')
    w.clicked.connect(callback);return w

def line(text='',placeholder=''):
    w=QLineEdit(text);w.setPlaceholderText(placeholder);return w

def card():
    w=QFrame();w.setObjectName('card');l=QVBoxLayout(w);l.setContentsMargins(18,16,18,16);l.setSpacing(10);return w,l

def table(headers,editable=False):
    w=QTableWidget(0,len(headers));w.setHorizontalHeaderLabels(headers)
    w.verticalHeader().setVisible(False);w.setAlternatingRowColors(True)
    w.verticalHeader().setDefaultSectionSize(40)
    w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    w.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    if not editable:w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return w

def fill(t,rows):
    t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,v in enumerate(row):t.setItem(i,j,QTableWidgetItem(str(v)))

class CourseDialog(QDialog):
    def __init__(self,parent,c=None):
        super().__init__(parent);self.setWindowTitle('课程信息');self.setMinimumWidth(480)
        c=c or {};layout=QVBoxLayout(self);form=QFormLayout();self.inputs={}
        for k,title,default in [('term','学期','未标注学期'),('name','课程名称',''),('code','课程代码',''),('credit','学分','3'),('raw','原始成绩','80')]:
            self.inputs[k]=line(str(c.get(k,default)));form.addRow(title,self.inputs[k])
        self.include=QCheckBox('计入 GPA');self.include.setChecked(bool(c.get('included',1)));form.addRow('',self.include)
        self.reason=line(c.get('reason',''),'不计入时填写原因');form.addRow('排除原因',self.reason)
        layout.addLayout(form);layout.addWidget(label('优95 · 良85 · 中等75 · 合格/及格65\n四六级及零学分课程不参与统计。','subtle',True))
        self.error=label('',wrap=True);layout.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存');buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def validate(self):
        from storage import validate
        c={k:w.text().strip() for k,w in self.inputs.items()}
        c.update(included=int(self.include.isChecked()),reason=self.reason.text().strip(),score=None)
        try:
            try:c['score']=score_value(c['raw'])
            except ValueError:
                if c['included']:raise
            if excluded_course(c['name'],c['code']): c.update(included=0,reason=excluded_course(c['name'],c['code']))
            validate(c);self.value=c;self.accept()
        except ValueError as e:self.error.setText(str(e))

class PreviewDialog(QDialog):
    def __init__(self,parent,batches):
        super().__init__(parent);self.setWindowTitle('确认导入');self.resize(1000,650);self.batches=batches
        l=QVBoxLayout(self);l.addWidget(label('核对后存入本地','title'))
        self.sheets=QComboBox()
        for b in batches:self.sheets.addItem(b['sheet'])
        l.addWidget(self.sheets);self.info=label('',wrap=True);l.addWidget(self.info)
        self.grid=table(['学期','课程','学分','原成绩','换算','处理']);l.addWidget(self.grid,1)
        l.addWidget(label('同学期、课程名称及代码一致的记录会更新；相同记录跳过。请核对被排除的课程。','subtle',True))
        controls=QHBoxLayout();controls.addStretch();controls.addWidget(button('取消',self.reject));controls.addWidget(button('确认导入',self.accept,True));l.addLayout(controls)
        self.sheets.currentIndexChanged.connect(self.render);self.render()

    def render(self):
        batch=self.batches[self.sheets.currentIndex()];rows=batch['courses'];inc=sum(c['included'] for c in rows)
        self.info.setText(f'共识别 {len(rows)} 门 · 计入 {inc} 门 · 排除/待处理 {len(rows)-inc} 门'+(' · 有待处理记录，请导入后检查' if batch['warnings'] else ''))
        fill(self.grid,[[c['term'],c['name'],c['credit'],c['raw'],c['score'] if c['score'] is not None else '—','计入' if c['included'] else c['reason']] for c in rows])

    def selected(self):return self.batches[self.sheets.currentIndex()]

class MainWindow(QMainWindow):
    def __init__(self,store):
        super().__init__();self.store=store;self.exact=None;self.loading=False;self.last_result=None
        self.setWindowTitle('Markline · 成绩档案与试算');self.setWindowIcon(icon());self.resize(1200,840);self.setMinimumSize(1000,700)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.calculate)
        root=QWidget();self.setCentralWidget(root);base=QHBoxLayout(root);base.setContentsMargins(0,0,0,0);base.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(174);sl=QVBoxLayout(sidebar);sl.setContentsMargins(15,25,15,20);sl.setSpacing(7)
        brand=QHBoxLayout();brand.setSpacing(7);mark=QLabel();mark.setPixmap(icon().pixmap(25,25));brand.addWidget(mark);brand.addWidget(label('Markline','brand'));brand.addStretch();sl.addLayout(brand)
        sl.addWidget(label('成绩档案与试算','subtle'));sl.addSpacing(30)
        self.stack=QStackedWidget();self.nav=[]
        for i,name in enumerate(['我的成绩','快速对比','数据设置']):
            b=QPushButton(name);b.setObjectName('nav');b.setCheckable(True);b.clicked.connect(lambda checked=False,n=i:self.navigate(n));sl.addWidget(b);self.nav.append(b)
        sl.addStretch();sl.addWidget(label('Markline 1.0\n本地保存 · 离线使用','subtle',True));base.addWidget(sidebar);base.addWidget(self.stack,1)
        self.build_courses();self.build_compare();self.build_settings();self.navigate(0)
        self.refresh_courses();self.refresh_peers()
        saved=self.store.setting('last_session')
        if saved:
            try:self.load_state(json.loads(saved))
            except (ValueError,KeyError,TypeError):self.statusBar().showMessage('上次试算无法恢复，请重新填写。')
        self.statusBar().showMessage('离线就绪 · 请先导入成绩表，或直接进入快速对比')

    def page(self,title,subtitle):
        page=QWidget();page.setObjectName('page');page.setMinimumHeight(780);l=QVBoxLayout(page);l.setContentsMargins(24,22,24,18);l.setSpacing(12)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page)
        l.addWidget(label(title,'title'));l.addWidget(label(subtitle,'subtle',True));self.stack.addWidget(scroll);return l

    def navigate(self,index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav):b.setChecked(i==index)

    def alert(self,message):QMessageBox.warning(self,'请检查',str(message))

    def build_courses(self):
        l=self.page('我的成绩','导入与维护课程记录。统计仅使用标为“计入”的课程。')
        metrics=QHBoxLayout();self.metrics=[]
        for title in ['累计 GPA','计入学分','加权平均分']:
            w=QFrame();cl=QHBoxLayout(w);cl.setContentsMargins(0,8,14,9);cl.addWidget(label(title,'subtle'));v=label('—','metric');cl.addWidget(v);cl.addStretch();metrics.addWidget(w);self.metrics.append(v)
        l.addLayout(metrics)
        actions=QHBoxLayout()
        for title,cb,primary in [('导入成绩表',self.import_dialog,True),('添加课程',self.add_course,False),('编辑',self.edit_course,False),('删除',self.delete_course,False),('导出 CSV',self.export_csv,False)]:actions.addWidget(button(title,cb,primary))
        actions.addStretch();self.search=line('','搜索课程或学期');self.search.setMaximumWidth(200);self.search.textChanged.connect(self.refresh_courses);actions.addWidget(self.search);l.addLayout(actions)
        self.course_table=table(['学期','课程名称','学分','原成绩','换算成绩','绩点','状态'])
        self.course_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for col in [0,2,3,4,5]:self.course_table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
        self.course_table.doubleClicked.connect(self.edit_course);l.addWidget(self.course_table,1)
        self.course_note=label('',wrap=True);l.addWidget(self.course_note)
        bottom=QHBoxLayout();bottom.addWidget(label('等级成绩自动换算；四六级、形势与政策不计入统计。','subtle',True));bottom.addStretch();bottom.addWidget(button('带入快速对比',self.use_my_courses,True));l.addLayout(bottom)

    def refresh_courses(self):
        all_rows=self.store.courses();term=self.search.text().strip().lower();self.visible_courses=[c for c in all_rows if term in (c['name']+c['term']+c['code']).lower()]
        fill(self.course_table,[[c['term'],c['name'],c['credit'],c['raw'],c['score'] if c['score'] is not None else '—',display(points(c['score']),1) if c['included'] else '—','计入' if c['included'] else c['reason']] for c in self.visible_courses])
        valid=[c for c in all_rows if c['included']];self.course_pair=aggregate([(c['credit'],c['score']) for c in valid])
        self.metrics[0].setText(display(gpa(self.course_pair)) if valid else '—')
        self.metrics[1].setText(display(self.course_pair[1],2) if valid else '—')
        average=sum(credit_value(c['credit'])*c['score'] for c in valid)/self.course_pair[1] if valid else None
        self.metrics[2].setText(display(average,2) if valid else '—')
        pending=sum('待处理' in c['reason'] for c in all_rows)
        text=f'已保存 {len(all_rows)} 门，计入 {len(valid)} 门，排除 {len(all_rows)-len(valid)} 门。'
        if pending:text+=f' 其中 {pending} 门待处理；当前统计仅覆盖有效记录。'
        if not all_rows:text='还没有课程。点击“导入成绩表”，支持 XLS、XLSX、CSV。'
        summary=self.store.setting('import_summary')
        if summary and valid:
            try:
                expected=json.loads(summary).get('gpa')
                if expected and display(gpa(self.course_pair))!=display(Fraction(expected)):
                    text+=f' 原表汇总 GPA {expected} 与本工具重算不同，可能与等级换算、排除范围或学校规则有关。'
            except (ValueError,TypeError):pass
        self.course_note.setText(text)

    def selected_course(self):
        row=self.course_table.currentRow()
        if row<0:raise ValueError('请先选中一门课程')
        return self.visible_courses[row]

    def add_course(self):
        d=CourseDialog(self)
        if d.exec():
            try:self.store.put_course(d.value);self.refresh_courses()
            except Exception as e:self.alert(e)

    def edit_course(self,*args):
        try:
            c=self.selected_course();d=CourseDialog(self,c)
            if d.exec():self.store.put_course(d.value,c['id']);self.refresh_courses()
        except Exception as e:self.alert(e)

    def delete_course(self):
        try:
            c=self.selected_course()
            if QMessageBox.question(self,'删除课程',f'删除“{c["name"]}”？')==QMessageBox.StandardButton.Yes:
                self.store.delete_course(c['id']);self.refresh_courses()
        except Exception as e:self.alert(e)

    def import_dialog(self):
        path,_=QFileDialog.getOpenFileName(self,'导入成绩表',str(self.store.path.parent),'成绩表 (*.xls *.xlsx *.csv)')
        if not path:return
        try:
            d=PreviewDialog(self,read_transcript(path))
            if not d.exec():return
            batch=d.selected();a,u,k=self.store.import_courses(batch['courses']);self.store.set_setting('import_summary',json.dumps(batch['summary']))
            self.refresh_courses();self.statusBar().showMessage(f'导入完成：新增{a}门，更新{u}门，跳过{k}门相同记录。',15000)
        except Exception as e:self.alert(f'导入未完成，原有数据保留。\n{e}')

    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'导出课程',str(self.store.path.parent/'我的成绩.csv'),'CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['学期','课程名称','课程代码','学分','有效成绩','是否计入','排除原因'])
                for c in self.store.courses():w.writerow([c[k] for k in ['term','name','code','credit','raw','included','reason']])
            self.statusBar().showMessage('课程已导出',8000)
        except Exception as e:self.alert(e)

    def build_compare(self):
        l=self.page('快速对比','无需录入对方全部课程。填写当前累计数据，再试算未来课程。GPA 领先以未舍入结果判断。')
        bar=QHBoxLayout();self.peer=QComboBox();self.peer.setMinimumWidth(180);self.peer.currentIndexChanged.connect(self.peer_changed)
        bar.addWidget(self.peer);bar.addWidget(button('保存对象',self.save_peer));bar.addWidget(button('删除对象',self.delete_peer));bar.addStretch();bar.addWidget(button('打开方案',self.open_scenario));bar.addWidget(button('保存为新方案',self.save_scenario));l.addLayout(bar)
        cards=QHBoxLayout()
        for prefix,title in [('a','本人当前数据'),('b','对方当前数据')]:
            w,cl=card();w.setMinimumHeight(190);cl.addWidget(label(title));form=QFormLayout();credit=line('','如 100');value=line('','如 3.5836');mode=QComboBox();mode.addItems(['累计平均 GPA','加权绩点总量'])
            form.addRow('计入 GPA 总学分',credit);form.addRow(mode,value);cl.addLayout(form)
            setattr(self,prefix+'_credit',credit);setattr(self,prefix+'_value',value);setattr(self,prefix+'_mode',mode)
            for widget in [credit,value]:widget.textChanged.connect(lambda _,p=prefix:self.base_changed(p))
            mode.currentIndexChanged.connect(lambda _,p=prefix:self.base_changed(p))
            if prefix=='a':cl.addWidget(button('使用我的成绩',self.use_my_courses))
            else:cl.addWidget(label('只需同一截止时点的汇总数据','subtle'))
            cards.addWidget(w)
        l.addLayout(cards)
        self.basis_note=label('手填平均 GPA 可能已舍入，反推仅基于输入值。双方按各自学分计算，不代表同课程表现或官方排名。','subtle',True);l.addWidget(self.basis_note)
        actions=QHBoxLayout();actions.addWidget(label('后续课程'));actions.addStretch();actions.addWidget(button('添加课程',self.add_future));actions.addWidget(button('删除选中',self.remove_future));actions.addWidget(button('载入示例',self.load_demo));l.addLayout(actions)
        self.future=table(['课程名称','本人修读','本人学分','本人成绩','对方修读','对方学分','对方预期'],True)
        self.future.setMinimumHeight(125);self.future.itemChanged.connect(self.queue_calculate)
        self.future.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for c in range(1,7):self.future.horizontalHeader().setSectionResizeMode(c,QHeaderView.ResizeMode.Fixed);self.future.setColumnWidth(c,95)
        l.addWidget(self.future,1)
        buttons=QHBoxLayout();buttons.addWidget(button('反推选中课程最低成绩',self.solve_selected,True));buttons.addWidget(button('计算多科结果',self.calculate));buttons.addStretch();buttons.addWidget(label('成绩60–100整数；90–100绩点均为4.0','subtle'));l.addLayout(buttons)
        self.result=label('填写双方当前数据，添加后续课程后开始试算。','result',True);self.result.setMinimumHeight(110);l.addWidget(self.result)
        self.add_future()

    def base_changed(self,prefix):
        if self.loading:return
        if prefix=='a':self.exact=None
        self.queue_calculate()

    def queue_calculate(self,*args):
        if not self.loading:
            self.result.setText('输入已变化，正在重新计算…');self.timer.start()

    def add_future(self,row=None):
        if not isinstance(row,dict):row={}
        t=self.future;was=t.blockSignals(True);r=t.rowCount();t.insertRow(r)
        vals=[row.get('name',f'后续课程{r+1}'),row.get('a_take',True),row.get('a_credit','3'),row.get('a_score','80'),row.get('b_take',True),row.get('b_credit','3'),row.get('b_score','80')]
        for col,v in enumerate(vals):
            item=QTableWidgetItem(str(v))
            if col in [1,4]:
                item.setText('修读');item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if v else Qt.CheckState.Unchecked)
            t.setItem(r,col,item)
        t.blockSignals(was);t.selectRow(r);self.queue_calculate()

    def remove_future(self):
        row=self.future.currentRow()
        if row>=0:self.future.removeRow(row);self.queue_calculate()

    def get_rows(self,skip_a=None):
        result=[]
        for r in range(self.future.rowCount()):
            def txt(c):return self.future.item(r,c).text().strip() if self.future.item(r,c) else ''
            row=dict(name=txt(0),a_take=self.future.item(r,1).checkState()==Qt.CheckState.Checked,
                     b_take=self.future.item(r,4).checkState()==Qt.CheckState.Checked,a_credit=txt(2),b_credit=txt(5),a_score=txt(3),b_score=txt(6))
            try:
                if not row['name']:raise ValueError('请填写课程名称')
                excluded=excluded_course(row['name'],'')
                if excluded and (row['a_take'] or row['b_take']):raise ValueError(excluded+'，请删除该行或取消双方修读')
                for p in ['a','b']:
                    if row[p+'_take']:
                        credit_value(row[p+'_credit'])
                        row[p+'_score']=score_value(row[p+'_score']) if not(p=='a' and r==skip_a) else 60
                result.append(row)
            except ValueError as e:raise ValueError(f'第{r+1}门课程：{e}') from None
        return result

    def bases(self):
        try:a=self.exact if self.exact is not None else baseline(self.a_credit.text(),self.a_value.text(),'gpa' if self.a_mode.currentIndex()==0 else 'total')
        except ValueError as e:raise ValueError(f'本人当前数据：{e}') from None
        try:b=baseline(self.b_credit.text(),self.b_value.text(),'gpa' if self.b_mode.currentIndex()==0 else 'total')
        except ValueError as e:raise ValueError(f'对方当前数据：{e}') from None
        return a,b

    def calculate(self):
        self.timer.stop()
        try:
            a,b=self.bases();rows=self.get_rows();r=simulate(a,b,rows);self.last_result=r
            relation={1:'本人严格领先',0:'双方精确并列',-1:'本人仍落后'}[r['relation']]
            feasible='最低60分组合已领先' if r['minimum_relation']>0 else ('存在可反超组合' if r['maximum_relation']>0 else ('最高只能并列' if r['maximum_relation']==0 else '最高仍无法反超'))
            gains=[]
            for row in rows:
                if row['a_take']:
                    s=row['a_score'];gain=credit_value(row['a_credit'])*(points(min(s+1,100))-points(s))/r['a'][1]
                    gains.append(f'{row["name"]}：'+('已到90分平台' if s>=90 else f'再提高1分，累计GPA +{display(gain,5)}'))
            text=f'{relation}  ·  GPA差 {display(gpa(r["a"])-gpa(r["b"]),6)}\n本人最终 {display(gpa(r["a"]),6)}（{display(r["a"][1],2)}学分）    对方最终 {display(gpa(r["b"]),6)}（{display(r["b"][1],2)}学分）\n可行性：{feasible}，对方假设保持不变。'
            if gains:text+='\n'+'；'.join(gains[:2])+('；更多课程请逐项调整查看' if len(gains)>2 else '')
            self.result.setText(text);self.store.set_setting('last_session',json.dumps(self.collect_state(),ensure_ascii=False));return r
        except Exception as e:
            self.last_result=None;self.result.setText('待完善输入：'+str(e));return None

    def solve_selected(self):
        self.timer.stop()
        try:
            index=self.future.currentRow()
            if index<0:raise ValueError('请先选中需要反推的课程')
            rows=self.get_rows(skip_a=index);target=rows[index]
            if not target['a_take']:raise ValueError('选中课程必须由本人修读')
            a,b=self.bases();fixed=simulate(a,b,[r for i,r in enumerate(rows) if i!=index])
            r=solve(fixed['a'],fixed['b'],target['a_credit'],target['b_credit'] if target['b_take'] else None,target['b_score'])
            if r['minimum'] is not None:
                old=self.future.blockSignals(True);self.future.item(index,3).setText(str(r['minimum']));self.future.blockSignals(old)
                gap=r['gap'];difference=''
                if gap is not None:difference=f'比对方高{gap}分' if gap>0 else ('与对方同分即可' if gap==0 else f'可比对方低{-gap}分')
                text=f'{target["name"]}：最低 {r["minimum"]} 分  {difference}\n本人最终 GPA {display(gpa(r["a"]),6)}，对方 {display(gpa(r["b"]),6)}，严格领先。'
                if r['previous']:text+=f'\n边界验证：{r["minimum"]-1}分时本人GPA {display(gpa(r["previous"]),6)}，不能严格领先。'
                else:text+='\n最低允许成绩60分已足够。'
                text+='\n其他后续课程保持表中成绩不变；90分以上继续提分不增加绩点。'
            else:
                text=('当前条件下最高只能并列。' if r['status']=='tie' else '当前条件下，即使考到90–100分仍无法反超。')+f'\n本人最高累计GPA {display(gpa(r["a"]),6)}，对方 {display(gpa(r["b"]),6)}。\n可增加后续课程共同试算，或调整对方预期。'
            self.result.setText(text);self.store.set_setting('last_session',json.dumps(self.collect_state(),ensure_ascii=False));return r
        except Exception as e:self.result.setText('无法反推：'+str(e));return None

    def use_my_courses(self):
        if self.course_pair[1]<=0:self.alert('请先导入或添加计入GPA的课程');return
        self.loading=True;self.a_mode.setCurrentIndex(0);self.a_credit.setText(str(float(self.course_pair[1])).rstrip('0').rstrip('.') if self.course_pair[1].denominator!=1 else str(self.course_pair[1].numerator));self.a_value.setText(display(gpa(self.course_pair),6));self.exact=self.course_pair;self.loading=False
        self.basis_note.setText('本人使用导入课程的精确汇总快照；修改输入后改为手填。对方手填GPA若已舍入，临界结果仍受其精度影响。双方按各自课程学分计算。')
        self.navigate(1);self.queue_calculate()

    def refresh_peers(self,select=None):
        old=self.peer.blockSignals(True);self.peer.clear();self.peer.addItem('临时比较对象',None)
        for p in self.store.peers():self.peer.addItem(p['name'],p['id'])
        if select:self.peer.setCurrentIndex(self.peer.findData(select))
        self.peer.blockSignals(old)

    def peer_changed(self,*args):
        identity=self.peer.currentData()
        if identity is None:return
        for p in self.store.peers():
            if p['id']==identity:
                payload=json.loads(p['payload']);self.loading=True
                self.b_credit.setText(payload['credit']);self.b_value.setText(payload['value']);self.b_mode.setCurrentIndex(payload['mode']);self.loading=False;self.queue_calculate();break

    def save_peer(self):
        try:
            baseline(self.b_credit.text(),self.b_value.text(),'gpa' if self.b_mode.currentIndex()==0 else 'total')
            name,ok=QInputDialog.getText(self,'保存比较对象','名称',text=self.peer.currentText() if self.peer.currentData() else '')
            if ok:
                identity=self.store.save_peer(name.strip(),dict(credit=self.b_credit.text(),value=self.b_value.text(),mode=self.b_mode.currentIndex()),self.peer.currentData());self.refresh_peers(identity)
        except Exception as e:self.alert(e)

    def delete_peer(self):
        identity=self.peer.currentData()
        if identity and QMessageBox.question(self,'删除对象','删除该对象？保存的方案快照会保留。')==QMessageBox.StandardButton.Yes:self.store.delete_peer(identity);self.refresh_peers()

    def collect_state(self):
        rows=[]
        for r in range(self.future.rowCount()):
            vals=[self.future.item(r,c).text() if self.future.item(r,c) else '' for c in range(7)]
            rows.append(dict(name=vals[0],a_credit=vals[2],a_score=vals[3],b_credit=vals[5],b_score=vals[6],a_take=self.future.item(r,1).checkState()==Qt.CheckState.Checked,b_take=self.future.item(r,4).checkState()==Qt.CheckState.Checked))
        return dict(version=1,a_credit=self.a_credit.text(),a_value=self.a_value.text(),a_mode=self.a_mode.currentIndex(),b_credit=self.b_credit.text(),b_value=self.b_value.text(),b_mode=self.b_mode.currentIndex(),peer_name=self.peer.currentText(),exact=[str(x) for x in self.exact] if self.exact else None,rows=rows)

    def load_state(self,payload):
        if payload.get('version')!=1:raise ValueError('不支持的方案版本')
        self.loading=True
        try:
            for p in ['a','b']:
                getattr(self,p+'_credit').setText(payload[p+'_credit']);getattr(self,p+'_value').setText(payload[p+'_value']);getattr(self,p+'_mode').setCurrentIndex(payload[p+'_mode'])
            self.exact=tuple(Fraction(x) for x in payload['exact']) if payload.get('exact') else None
            self.future.setRowCount(0)
            for row in payload['rows']:self.add_future(row)
            name=payload.get('peer_name','临时比较对象');idx=self.peer.findText(name);self.peer.blockSignals(True);self.peer.setCurrentIndex(max(0,idx));self.peer.blockSignals(False)
        finally:self.loading=False
        self.basis_note.setText('已恢复方案/上次试算的快照。导入成绩更新不会改变此基线；需要时点击“使用我的成绩”更新。')
        self.calculate()

    def save_scenario(self):
        if self.calculate() is None:return
        name,ok=QInputDialog.getText(self,'保存为新方案','方案名称',text='试算 '+datetime.now().strftime('%m-%d %H:%M'))
        if ok:
            try:self.store.save_scenario(name.strip(),self.collect_state());self.statusBar().showMessage('方案已保存，可打开后调整并另存为新方案。',10000)
            except Exception as e:self.alert(e)

    def open_scenario(self):
        rows=self.store.scenarios()
        if not rows:self.alert('还没有保存的方案');return
        d=QDialog(self);d.setWindowTitle('打开方案');d.resize(660,420);l=QVBoxLayout(d);grid=table(['名称','保存时间']);fill(grid,[[r['name'],r['created']] for r in rows]);l.addWidget(grid)
        def open_selected():
            i=grid.currentRow()
            if i>=0:
                try:self.load_state(self.store.scenario(rows[i]['id']));d.accept()
                except Exception as e:self.alert(e)
        def remove():
            i=grid.currentRow()
            if i>=0 and QMessageBox.question(d,'删除方案','确定删除选中的方案？')==QMessageBox.StandardButton.Yes:
                self.store.delete_scenario(rows[i]['id']);rows.pop(i);grid.removeRow(i)
        controls=QHBoxLayout();controls.addWidget(button('删除',remove));controls.addStretch();controls.addWidget(button('取消',d.reject));controls.addWidget(button('打开副本并试算',open_selected,True));l.addLayout(controls);grid.doubleClicked.connect(open_selected);grid.selectRow(0);d.exec()

    def load_demo(self):
        if QMessageBox.question(self,'载入合成示例','仅替换当前试算输入，不改动个人成绩。继续？')!=QMessageBox.StandardButton.Yes:return
        self.load_state(dict(version=1,a_credit='12',a_value='3.583333',a_mode=0,b_credit='12',b_value='44.9',b_mode=1,exact=['43','12'],peer_name='临时比较对象',rows=[dict(name='合成示例课程',a_credit='3',a_score=85,b_credit='3',b_score=80,a_take=True,b_take=True)]))

    def build_settings(self):
        l=self.page('数据设置','数据在本地保存。无需账号、服务器或联网服务。')
        l.parentWidget().setMinimumHeight(850)
        w,cl=card();cl.addWidget(label('当前数据文件'));cl.addWidget(label(str(self.store.path),'subtle',True));cl.addWidget(label('便携版数据位于软件旁的 data 文件夹。移动整个软件文件夹即可保留数据。','subtle',True))
        controls=QHBoxLayout();controls.addWidget(button('备份数据',self.backup_dialog,True));controls.addWidget(button('恢复备份',self.restore_dialog));controls.addStretch();cl.addLayout(controls);l.addWidget(w)
        tools=QHBoxLayout();tools.addWidget(button('打开使用说明',lambda:self.open_resource('使用说明.md')));tools.addWidget(button('打开示例成绩表',lambda:self.open_resource('示例成绩.csv')));tools.addWidget(button('第三方许可',lambda:self.open_resource('licenses')));tools.addStretch();l.addLayout(tools)
        w,cl=card();cl.addWidget(label('固定计算规则'))
        cl.addWidget(label('60–89分：(成绩 − 50) ÷ 10\n90–100分：4.0\n优＝95，良＝85，中等＝75，合格/及格＝65。\n四六级、形势与政策和零学分课程不计入；其他不支持的成绩列为待处理。\n所有课程按学分加权。百分制加权平均分与累计GPA分别计算。',wrap=True));l.addWidget(w)
        w,cl=card();cl.addWidget(label('使用说明'))
        cl.addWidget(label('1. 我的成绩：导入表格、确认处理范围，必要时编辑课程。\n2. 快速对比：输入双方相同截止时点的学分和GPA，添加未来课程。\n3. 单科反推：选中一行，其他课程保持表中假设不变。\n4. 多科试算：直接修改各科成绩，查看累计变化与最高可行性。\n5. 保存方案后可打开副本继续调整；保存对象只保存对方当前汇总。\n\n本工具不支持60分以下、不自动执行重修替代或校方规则。发现重修记录时请手动排除不应计入的记录。手填舍入GPA得到的是基于输入值的估算。',wrap=True));l.addWidget(w)
        l.addStretch();l.addWidget(label('Markline 1.0 · 第三方许可见软件包 licenses 文件夹','subtle',True))

    def open_resource(self,name):
        import sys
        root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]/'resources'))
        source=root/name
        if not source.exists():self.alert('未找到该资源');return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(source)))

    def backup_dialog(self):
        path,_=QFileDialog.getSaveFileName(self,'备份数据',str(self.store.path.parent/('Markline_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')),'数据库备份 (*.db)')
        if path:
            try:self.store.backup(path);self.statusBar().showMessage('备份完成',10000)
            except Exception as e:self.alert(e)

    def restore_dialog(self):
        path,_=QFileDialog.getOpenFileName(self,'选择备份',str(self.store.path.parent),'数据库备份 (*.db)')
        if not path:return
        if QMessageBox.question(self,'恢复备份','将恢复整个数据文件；当前数据会先自动备份。继续？')!=QMessageBox.StandardButton.Yes:return
        try:
            self.timer.stop();self.store.restore(path);self.refresh_courses();self.refresh_peers();saved=self.store.setting('last_session')
            if saved:self.load_state(json.loads(saved))
            else:
                self.loading=True
                for w in [self.a_credit,self.a_value,self.b_credit,self.b_value]:w.clear()
                self.exact=None;self.future.setRowCount(0);self.add_future();self.loading=False;self.result.setText('已恢复备份，请填写双方当前数据。')
            self.statusBar().showMessage('恢复完成，恢复前的数据备份保留在data文件夹。',15000)
        except Exception as e:self.alert(e)

    def closeEvent(self,event):
        self.timer.stop()
        try:self.store.set_setting('last_session',json.dumps(self.collect_state(),ensure_ascii=False))
        except Exception as e:
            if QMessageBox.question(self,'保存失败',f'{e}\n仍要退出？')!=QMessageBox.StandardButton.Yes:event.ignore();return
        event.accept()
