from intcode_d2 import Intcode

with open('input_day2.txt', 'r') as infile:
    program = [int(v) for v in infile.read().split(',')]
program[1] = 12
program[2] = 2
intcode = Intcode(program)
intcode.run()
print(intcode.mem[0])