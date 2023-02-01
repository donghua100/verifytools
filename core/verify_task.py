import os
import sys
import argparse
import shutil
from task import verify_task


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    # p.add_argument('configfile', help='config file', type=str)
    p.add_argument('-s', '--srcfile', help='the file to verify', type=str, required=True)
    p.add_argument('-w','--workdir', help='muti task work dir', type=str, required=True)
    p.add_argument('-t','--taskname', help='task name', type=str, required=True)
    p.add_argument('-ty', '--type', help='task type', type=str, required=True)
    p.add_argument('-f', '--force', help='overwrite work dir',action='store_true')

    arg             = p.parse_args()
    workdir         = arg.workdir
    taskname        = arg.taskname
    srcfile         = arg.srcfile
    tasktype        = arg.type
    workdir = os.path.abspath(workdir)
    if not os.path.exists(workdir):
        os.mkdir(workdir)
    else:
        if arg.force:
            shutil.rmtree(workdir,ignore_errors=True)
            os.mkdir(workdir)
        else:
            sys.exit(-1)
    srcname     = os.path.basename(srcfile)
    dst_file    = f"{workdir}/{srcname}"
    shutil.copy(srcfile,dst_file)
    print(tasktype)
    verify_task(dst_file, workdir, taskname, tasktype)


