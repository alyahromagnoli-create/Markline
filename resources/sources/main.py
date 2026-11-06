import os
import sys
from pathlib import Path

def main():
    import argparse
    parser=argparse.ArgumentParser(description='Markline offline desktop')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--smoke-test',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--check-import',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    home=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
    data=(args.data_dir or home/'data').resolve()
    try:
        data.mkdir(parents=True,exist_ok=True);probe=data/'.write-check';probe.write_text('ok',encoding='utf-8');probe.unlink()
        (data/'tmp').mkdir(exist_ok=True);os.environ['TEMP']=str(data/'tmp');os.environ['TMP']=str(data/'tmp')
        os.environ['QT_LOGGING_RULES']='qt.qpa.fonts.warning=false'
    except Exception as e:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,f'数据目录不可写：{data}\n{e}\n请把软件移动到可写目录，或使用 --data-dir 指定可写的数据目录。','Markline',16);return 1
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtCore import QLockFile
    from storage import Store
    from ui import MainWindow,STYLE
    app=QApplication(sys.argv[:1]);app.setApplicationName('Markline');app.setStyle('Fusion');app.setStyleSheet(STYLE)
    lock=QLockFile(str(data/'Markline.lock'));lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.information(None,'Markline','该数据文件已在其他Markline窗口中使用。请切回已打开的窗口。');return 0
    try:store=Store(data/'Markline.db');window=MainWindow(store)
    except Exception as e:QMessageBox.critical(None,'启动失败',str(e));lock.unlock();return 1
    window.show()
    if args.smoke_test:
        from PySide6.QtCore import QTimer
        import json
        def smoke():
            from core import baseline,solve
            from importer import read_transcript
            samples=Path(getattr(sys,'_MEIPASS',home/'resources'))/'示例成绩.csv'
            info={'visible':window.isVisible(),'pages':window.stack.count(),'minimum':solve(baseline(3,3),baseline(3,3),3,3,80)['minimum']}
            if samples.exists():info['imported_sample']=len(read_transcript(samples)[0]['courses'])
            if args.check_import:
                batches=read_transcript(args.check_import);info['external_import_rows']=len(batches[0]['courses'])
            window.load_state(dict(version=1,a_credit='3',a_value='3',a_mode=0,b_credit='3',b_value='3',b_mode=0,exact=None,peer_name='临时比较对象',rows=[dict(name='合成验收课程',a_credit='3',a_score=80,b_credit='3',b_score=80,a_take=True,b_take=True)]))
            window.navigate(1);window.future.selectRow(0);answer=window.solve_selected();info['ui_minimum']=answer['minimum']
            sid=store.save_scenario('合成验收',window.collect_state());info['scenario_saved']=store.scenario(sid)['rows'][0]['a_score']=='81'
            backup=data/'smoke-backup.db';store.backup(backup);info['backup_bytes']=backup.stat().st_size
            window.future.item(0,0).setText('形势与政策（验收）');info['policy_blocked']=window.calculate() is None
            window.future.item(0,0).setText('合成验收课程');window.solve_selected()
            window.grab().save(str(args.smoke_test.with_suffix('.png')))
            args.smoke_test.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');window.close()
        QTimer.singleShot(1400,smoke)
    def error_handler(kind,value,tb):
        import traceback
        with (data/'error.log').open('a',encoding='utf-8') as log:traceback.print_exception(kind,value,tb,file=log)
        QMessageBox.critical(window,'操作未完成',f'{value}\n错误已记录在data/error.log，现有数据保留。')
    sys.excepthook=error_handler
    code=app.exec();store.close();lock.unlock();return code

if __name__=='__main__':sys.exit(main())
