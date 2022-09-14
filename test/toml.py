from tomlkit import dumps,parse
import os

print(os.path.abspath(os.curdir))
print(os.getcwd())
print(__file__)
cfg = parse(open('test/config.toml').read())
print(cfg)
ip          = cfg['server']['ip']
port        = cfg['server']['port']
tasks       = cfg['tasks']
srcfile = cfg['file']['name']
print(srcfile)
srcname = os.path.basename(srcfile)
print(srcname)
cfg['file']['name'] = srcname
srcname = os.path.splitext(srcname)[0]
print(srcname)
print(dumps(cfg))
if 'file' in cfg:
    print('jjj')
