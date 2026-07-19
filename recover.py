import subprocess
css = subprocess.check_output(['git', 'show', 'fba065d:static/css/landing.css']).decode('utf-8')
with open('static/css/landing_orig.css', 'w', encoding='utf-8') as f:
    f.write(css)
