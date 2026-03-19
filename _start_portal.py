import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, r'c:\Users\renhe\CodeBuddy\DEMO\FX_SYSTEM_DEMO')
os.chdir(r'c:\Users\renhe\CodeBuddy\DEMO\FX_SYSTEM_DEMO')

from portal import app
app.run(host='0.0.0.0', port=8899, debug=False)
