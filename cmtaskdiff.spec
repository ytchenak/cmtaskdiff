# -*- mode: python -*-
a = Analysis(['cmtaskdiff.py'],
             pathex=['c:\\Users\\YTCHENAK\\Documents\\GitHub\\cmtaskdiff'],
             hiddenimports=[],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'cmtaskdiff.exe'),
          debug=False,
          strip=None,
          upx=False,
          console=True , icon='cmtaskdiff.ico')
