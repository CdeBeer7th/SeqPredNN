import pathlib as pa
index = []
file = 'config_4J9TAc.txt'
with open(pa.Path(file), 'r') as f:
    for line in f:
        i = line.strip('\n').split(' ')[-1]
        index.append(i)
print(index)
with open(pa.Path(f'a{file}'), 'a') as f:
    for i in index:
        f.write(f'{i}\n')

print(index)