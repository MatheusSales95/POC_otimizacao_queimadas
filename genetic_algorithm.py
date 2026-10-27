# Basic genetic algorithm implementation
#
# Author: Fabricio Galende Marques de Carvalho. D.Sc.
##


import numpy as np

def bin_2_int(x_bin):
    x_int = 0
    for i, bit in enumerate(x_bin):
        x_int += bit*(2**(len(x_bin)-1 - i))
    return x_int

def int_2_real(x_int, xmax, xmin, N):
    # N: Maximum natural number for this representation
    return (xmax-xmin)*x_int/N + xmin


def fitness(x,fob):
    return 1/(1+fob(x))

class Individual:
    def __init__(self, x_bin,xmax, xmin, fob, fitness):
        self._xmax = xmax
        self._xmin = xmin
        self._fob = fob
        self._fitness = fitness
        self.x_bin = x_bin
        self.x_int = bin_2_int(self.x_bin)
        self.x_r = int_2_real(self.x_int, xmax, xmin, 2**(len(self.x_bin))-1)
        self.fob = fob(self.x_r) 
        self.fitness = fitness(self.x_r, fob)

class Population:
    def __init__(self,pop_size, crom_size, xmin, xmax, fob, fitness):
        self.pop_size = pop_size
        self.individuals = []
        for _ in range(pop_size):
            x_bin = np.random.randint(0, 2, size= crom_size)
            self.individuals.append(Individual(x_bin,xmax, xmin, fob, fitness))
        

class Roulette:
    def __init__(self, population):
        self.roulette_range = []
        total_fit = 0
        for individual in population.individuals:
            total_fit += individual.fitness
        for idx, individual in enumerate(population.individuals):
            if idx == 0:
                self.roulette_range.append(individual.fitness/total_fit)
            else:
                self.roulette_range.append(self.roulette_range[idx-1] + (individual.fitness/total_fit))
        self.roulette_range[-1] = 1.0

    def spin(self):
        r = np.random.uniform(0, 1)
        for i, v in enumerate(self.roulette_range):
            if v > r:
                return i
        return len(self.roulette_range) -1
            

def mutation(individual, pm):
    x_bin_mut = []
    rng = np.random.default_rng()
    for bit in individual.x_bin:
        prob = rng.random()
        if prob > pm:
            x_bin_mut.append(bit)
        else:
            x_bin_mut.append(bit^1)
    new_individual = Individual(x_bin_mut, individual._xmax, individual._xmin, individual._fob, individual._fitness)
    return new_individual

def cross(parent_1, parent_2):
    pc = int(len(parent_1.x_bin)/2)
    child_1_bits = []
    child_2_bits = [] 
    for i in range(len(parent_1.x_bin)):
        if i < pc:
            child_1_bits.append(parent_1.x_bin[i])
            child_2_bits.append(parent_2.x_bin[i])
        else:
            child_1_bits.append(parent_2.x_bin[i])
            child_2_bits.append(parent_1.x_bin[i])

    child_1 = Individual(child_1_bits, parent_1._xmax, parent_1._xmin, parent_1._fob, parent_1._fitness)
    child_2 = Individual(child_2_bits, parent_1._xmax, parent_1._xmin, parent_1._fob, parent_1._fitness)

    return child_1, child_2
    