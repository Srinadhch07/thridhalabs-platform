import re
path='D:/Learning/Projects/thridhalabs/backend/app/api/routes/seo.py'
with open(path,'r',encoding='utf-8') as f:
    c=f.read()
c2 = re.sub(r'^(?:\s*"Disallow:[^\n]*\n)+', '', c)
with open(path,'w',encoding='utf-8') as f:
    f.write(c2)
print('done')
