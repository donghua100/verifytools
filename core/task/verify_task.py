import os
import sys
import argparse
import shutil
root_path = os.path.realpath(os.path.dirname(__file__))
sys.path.append(root_path)
from task import VerifTask


AIG_BMC_TASK = 'AIG_BMC_TASK'
AIG_PROVE_TASK = 'AIG_PROVE_TASK'
BTOR_BMC_TASK = 'BTOR_BMC_TASK'
BTOR_PROVE_TASK = 'BTOR_PROVE_TASK'

def verify_task(file_name, workdir, taskname, task_type=AIG_BMC_TASK, config_file='', useconfig=False, logfile=None):
    task = VerifTask(config_file,workdir,taskname,[],logfile,useconfig)
    # print("task_type in verify_task = ",task_type,len(task_type))
    if task_type == AIG_BMC_TASK:
        task.aig_bmc_config()
    elif task_type == AIG_PROVE_TASK:
        task.aig_pdr_config()
    elif task_type == BTOR_BMC_TASK:
        task.btor_bmc_config()
    elif task_type == BTOR_PROVE_TASK:
        task.btor_pdr_config()
    else:
        print("assert error:",task_type)
        assert 0
    srcfile = open(file_name,'rb')
    srcname = os.path.basename(file_name)
    task.filename = os.path.splitext(srcname)[0]
    destfile = open(f"{task.srcdir}/{task.filename}.{task.file_type}","wb")
    destfile.write(srcfile.read())
    srcfile.close()
    destfile.close()
    task.log('crate workdir')
    task.log('crate veriftask')
    task.log(f'write srcfile to {task.srcdir}/{task.filename}.{task.file_type}')
        # shutil.copy('mycounter-false.btor2',f"{task.designdir}/design.btor")
    task.log("run task")
    task.run()
    task.log('task over')
    task.exit_callback()

    return task.status
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


