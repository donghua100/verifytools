import os
import re
import Proc
import shutil


def run(task):
    cmdline = ''
    logfilename = 'engine_abc.txt'
    if task.mode == 'bmc':
        cmdline = f"{task.exe_path['yosys_abc']} -c  \"read {task.designdir}/{task.filename}.aig;fold;strash;bmc -F {task.depth}\""
    elif task.mode == 'prove':
        cmdline = f"{task.exe_path['yosys_abc']} -c  \"read {task.designdir}/{task.filename}.aig;fold;strash;pdr\""
    proc = Proc.Proc(task, 'run abc', cmdline, logfilename)
    def output_callback(outs):
        fstr=''.join(outs)
        status = 'UNKNOWN'
        match = re.findall(r'Property proved.*? Time = .*?(\d+\.\d+)', fstr)
        if len(match) > 0:
            status = 'SAFE'
        match = re.findall(r'Output (\d+) .* was asserted .* Time = .*', fstr)
        if len(match) > 0:
            status = 'UNSAFE'
            task.bmc_steps = int(match[0]) 
        task.status = status
    proc.output_callback = output_callback
        



