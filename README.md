#  CSMC: Distributed Verified Tool Based On Model Checking
CSMC is a tool working with Client/Server architecture for Hardware Model Checking.Once environment configuration has been done on server,one can use it's service to check hardwave design conveniently.
# How  to Build it
## Required Dependence on Server
**Yosys, ABC, PONO and AVR**

-  Building Yosys and  ABC. Note that this will install Yosys and ABC(as yosys-abc):
<https://yosyshq.net/yosys/>
```
git clone https://github.com/YosysHQ/yosys
cd yosys
make -j$(nproc)
sudo make install
```
- Building PONO:
<https://github.com/upscale-project/pono>
Following the PONO README to build PONO.
- Building AVR:
<https://github.com/aman-goel/avr>
Follwing the AVR README to build AVR. 
**NOTE: For more SMT-solver support,you should enable appropriate BACKEND_* flag in src/reach/reach_backend.h to change solver backends in avr project.Look the website carefully .Compile the sorce code and put the binary file in avr build directory .Binary with boolector solver shoud be put in bin_btor, and other solvers is similar. Here is the directory  in avr build directory**
```
build
├── avr
├── bin_btor
├── bin_msat
├── bin_yices
├── bin_z3
```
- python3 environment
`pip install tomlkit`
## Required Dependence on Client
Just python3 environment.
`pip install tomlkit`
# Use it
## On server
 **NOTE: First to use. Modify the core/toolpath.py code,change the variable AVRPATH and PONOPATH to the real path where the avr and pono project you have download,make sure you have build them sucessfully.**
Now you can run `python3 server.py -ip [you ip address] -p [port]`,the verify service will start,and ready to work.Tell you cilent the ip and port to enjoy the service.
## On client
Wite the config file.Don't worry the config is easy to write.We use [toml](https://toml.io/en/) to config verify task.
- First define tasks. E.g. `tasks = ["foo","bar"]` define two tasks named foo and bar. `
- Second for each task you shoul define the verify engine you want to use,the mode(bmc or prove),the solver and the other options if have. For example:
```
[foo]
engine = "avr" # the verify engine
mode = "bmc" # the mode bmc aims to find bug
depth = 100    # the bmc's bound
solver = "btor"  # use boolector as solver
[bar]
engine = "avr"
mode = "prove" # prove mode primarily prove circuit.
solver = "msat"
```
- Then the file section, just put the file name you want to verify and the file type. If the file type is system verilog,top module shoud be declared with key word top.
- Last, server section,the ip and port should be provided.
```
[server]
ip = "127.0.0.1"
port = "2678"
```
An example can be find in test/config.toml
# CSMC Tool Flow
![CSMC](img/CSMC.jpg "CSMC")
