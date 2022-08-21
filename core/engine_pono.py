import Proc
import re
def run(task):
    cmdline = ''
    logfilename = 'engine_pono.txt'
    if task.mode == 'bmc':
        cmdline = f"{task.exe_path['pono']} -v1 -e bmc -k {task.depth} --witness --vcd {task.tracedir}/dump.vcd {task.engine_opt} {task.designdir}/{task.filename}.btor"
    elif task.mode == 'prove':
        cmdline = f"{task.exe_path['pono']} -v1 -e ic3sa --witness --show-invar --check-invar --vcd {task.tracedir}/dump.vcd {task.engine_opt} {task.designdir}/{task.filename}.btor"
    proc = Proc.Proc(task,"run engine",cmdline,logfilename=logfilename)

    def output_callback(outs:list):
        status = None
        check_steps = 0
        witness_steps = 0
        witness = []
        wit_start = False
        invar = None
        def handle_line(line):
            nonlocal status,check_steps,witness_steps,wit_start,invar
            if line == 'sat':
                wit_start = True
                status = 'UNSAFE'
            if line == 'unsat':
                status = 'SAFE'
            if line == 'unknown':
                status = 'UNKNOWN'
            if line == 'error':
                status = 'ERROR'
            if wit_start:
                witness.append(line)
                if line == '.':
                    wit_start = False
            match = re.match(r'^Checking bmc at bound: (\d+)',line)
            if match:
                check_steps = int(match.group(1))
            match = re.match(r'^@(\d+)',line)
            if match:
                witness_steps = int(match.group(1))
            match = re.match(r'^INVAR: (.*)',line)
            if match:
                invar = match.group(0)
        for line in outs:
            handle_line(line)
        if status == 'UNSAFE':
            assert check_steps == witness_steps
            with open(f'{task.tracedir}/witness.txt','w') as f:
                for line in witness:
                    print(line,file=f,flush=True)
            task.log(f'witness has benn written in {task.tracedir}/witness.txt')
        elif status == 'SAFE':
            with open(f'{task.tracedir}/invar','w') as f:
                print(invar,file=f,flush=True)
        task.status = status
        task.bmc_steps = check_steps
    proc.output_callback = output_callback





