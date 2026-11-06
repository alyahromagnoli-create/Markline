import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

def test_ui_workflow(tmp_path):
    from PySide6.QtWidgets import QApplication
    from ui import MainWindow
    from storage import Store
    from core import gpa
    app=QApplication.instance() or QApplication([])
    store=Store(tmp_path/'ui.db')
    window=MainWindow(store)
    c=dict(term='2026春',name='合成课程',code='DEMO',credit='3',raw='80',score=80,included=1,reason='')
    store.import_courses([c]); window.refresh_courses()
    window.use_my_courses()
    assert window.a_credit.text()=='3'
    window.b_credit.setText('3'); window.b_value.setText('3')
    window.future.setRowCount(0); window.add_future({'name':'测试未来','a_credit':'3','b_credit':'3','a_score':80,'b_score':80,'a_take':True,'b_take':True})
    result=window.calculate()
    assert result['relation']==0
    window.future.selectRow(0)
    answer=window.solve_selected()
    assert answer['minimum']==81
    payload=window.collect_state()
    sid=store.save_scenario('测试方案',payload)
    window.a_credit.setText('9')
    window.load_state(store.scenario(sid))
    assert window.a_credit.text()=='3'
    assert window.get_rows()[0]['a_score']==81
    store.save_peer('比较A',{'credit':'3','value':'3','mode':0})
    window.refresh_peers(); assert window.peer.count()==2
    window.a_credit.setText('0')
    assert window.calculate() is None
    assert '学分' in window.result.text()
    window.close(); app.processEvents(); store.close()

def test_small_window_uses_scroll_instead_of_clipping(tmp_path):
    from PySide6.QtWidgets import QApplication,QScrollArea
    from storage import Store
    from ui import MainWindow,STYLE
    app=QApplication.instance() or QApplication([]);app.setStyleSheet(STYLE)
    s=Store(tmp_path/'layout.db');w=MainWindow(s);w.resize(1000,700);w.navigate(1);w.show();app.processEvents()
    page=w.stack.currentWidget()
    assert isinstance(page,QScrollArea)
    assert page.verticalScrollBar().maximum()>0
    assert w.a_credit.parentWidget().height()>=180
    w.close();s.close()

def test_future_policy_cannot_change_gpa(tmp_path):
    from PySide6.QtWidgets import QApplication
    from storage import Store
    from ui import MainWindow
    app=QApplication.instance() or QApplication([]);s=Store(tmp_path/'future-policy.db');w=MainWindow(s)
    w.a_credit.setText('3');w.a_value.setText('3');w.b_credit.setText('3');w.b_value.setText('3')
    w.future.item(0,0).setText('形势与政策（IV）')
    assert w.calculate() is None
    assert '不参与统计' in w.result.text()
    w.close();s.close()
