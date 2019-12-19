from intcode_d2 import Intcode
from sys import exit

with open('input_day2.txt', 'r') as infile:
    program_init = [int(v) for v in infile.read().split(',')]
for noun in range(100):
    for verb in range(100):
        program = program_init.copy()
        program[1] = noun
        program[2] = verb
        intcode = Intcode(program)
        intcode.run()
        if intcode.mem[0] == 19690720:
            print(f'Found. Noun={noun}, verb={verb}, answer={(100*noun) + verb}')
            exit()
