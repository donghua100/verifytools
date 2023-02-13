import Proc
import os
import re
import shutil

def run(task):
    cmdline = ''
    logfilename = 'engine_avr.txt'
    avrpath = task.avr_path
    avrbin = f"{avrpath}/build/bin_{task.solver}"
    avrout = f'{task.workdir}/avr'
    name = task.mode
    opts = task.engine_opt
    depth = task.depth
    file = f"{task.designdir}/{task.filename}.btor"
    timeout = 0
    if task.task_timeout is None:
        timeout=3600*24
    else:
        timeout = task.task_timeout + 5*60
    if task.mode == 'bmc':
        cmdline = f"cd {avrpath};python3 avr.py -o {avrout} -n {name} --bin {avrbin} {opts} --bmc -k {depth} --witness --timeout {timeout} {file}"
        proc = Proc.Proc(task,'run avr bmc',cmdline,logfilename)
    elif task.mode == 'prove':
        cmdline = f"cd {avrpath};python3 avr.py -o {avrout} -n {name} --bin {avrbin} {opts} --witness --timeout {timeout} {file}"
        proc = Proc.Proc(task,"run avr prove",cmdline,logfilename)
    else:
        assert 0
    def output_callback(outs):
        avr_workdir = f"{avrout}/work_{name}"
        status = None
        check_steps = 0
        with open(f"{avr_workdir}/result.pr", 'r') as f:
            lines = f.readlines()
            if len(lines) != 0:
                line = lines[0]
                line= line.strip()
                if line == 'avr-v':
                    status = "UNSAFE"
                elif line == 'avr-h':
                    status = 'SAFE'
                elif line == 'avr-f_err':
                    status = 'UNKNOWN'
                else:
                    assert 0,'unknown status'
            else:
                status = 'UNKNOWN'
        if status == 'UNSAFE':
            if not os.path.isfile(f"{avr_workdir}/cex.witness"):
                task.log("can't find witness file")
            else:
                shutil.copy(f"{avr_workdir}/cex.witness",f'{task.tracedir}/witness.txt')
                task.log(f'witness has benn written in {task.tracedir}/witness.txt')
                with open(f'{avr_workdir}/cex.witness','r') as f:
                    for line in f.readlines():
                        line.strip()
                        match = re.match(r'^@(\d+)',line)
                        if match:
                            check_steps = int(match.group(1))
        elif status == 'SAFE':
            with open(f'{task.tracedir}/invar.txt','w') as f:
                inv_txt = open(f"{avr_workdir}/inv.txt",'r')
                f.write(inv_txt.read())
                inv_txt.close()
                f.write('\n\n\n')
                f.write('-'*50)
                f.write('\n')
                f.write(';smt2 format invar\n')
                inv_smt = open(f"{avr_workdir}/inv.smt2",'r')
                f.write(inv_smt.read())
                inv_smt.close()
        elif status in ['UNKNOWN','TIMEOUT']:
            with open(f'{avr_workdir}/avr.err','r') as f:
                for line in f.readlines():
                    line = line.strip()
                    print(line)
                    match = re.search(r'\(bmc: safe till step (\d+)\)', line)
                    if match:
                        check_steps = int(match.group(1))
        else:
            assert False,'unknown status'
        task.status = status
        task.bmc_steps = check_steps

    proc.output_callback = output_callback

if __name__ == '__main__':
    print(os.path.abspath(os.curdir))
