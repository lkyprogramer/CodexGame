import sys, importlib.util
spec = importlib.util.spec_from_file_location('c', '/data/strata-data/pisim-20261120/c01_counterfactual.py'); c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
old = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]          # long source: ... 6 7 8 -> 9 10 11 12
noise = []
for k in range(6): noise += [100 + k, 6, 7, 8, 50 + k]   # trigram (6,7,8) repeated 6x later with other continuations
prompt = old + noise + [1, 2, 3, 4, 5, 6, 7, 8]
gen = [9, 10, 11, 12]
for eight in (False, True):
    d = c.Drafter(eight); d.append(prompt); print('eight', eight, d.propose(), c.walk(prompt, gen, eight, 2.475))
