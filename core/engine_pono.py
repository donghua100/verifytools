import Proc
def run(task):
    cmdline = ''
    if task.mode == 'bmc':
        cmdline = f"{task.exe_path['pono']} -e bmc -k {task.depth} --witness --vcd {task.tracedir}/dump.vcd {task.engine_opt} {task.designdir}/design.btor"
    elif task.mode == 'prove':
        cmdline = f"{task.exe_path['pono']} -e sygus-pdr --witness --vcd {task.tracedir}/dump.vcd {task.engine_opt} {task.designdir}/design.btor"
    Proc.Proc(task,cmdline)
    # proc.run()

