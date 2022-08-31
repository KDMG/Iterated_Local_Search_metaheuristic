from _csv import writer


def division(num, den, dec):
    if den == 0:
        return 0
    else:
        return round(num / den, dec)


def file_print(path, text, mode='a'):
    # text = list of any type of data I want to save on file
    if type(text) is list or type(text) is tuple:
        string = ''
        for t in text:
            string += str(t) + ';'
    else:
        string = str(text)
    string = string.replace('.', ',')
    with open(path, mode, newline='') as filep:
        writer_object = writer(filep, delimiter = ";")
        writer_object.writerow([string])
        filep.close()


def save_graph(fname, nodes, arcs, check=False):
    if check:
        file_print(fname, 'XP', 'w')
    else:
        file_print(fname, 'XP', 'a')
    for v in nodes:
        string = 'v ' + str(v[0]) + ' ' + v[1]
        file_print(fname, string)
    for w in arcs:
        string = 'e ' + str(w[0][0]) + ' ' + str(w[1][0]) + ' ' + w[0][1] + ' ' + w[1][1]
        file_print(fname, string)


def import_graph(path):
    print("\nRead ig from file ")
    with open(path) as file:
        node_id = 0
        nodes = []
        edges = []
        while True:
            line = file.readline()
            if not line:
                break
            elif line.strip() == 'XP' or line.strip() == '':
                continue
            else:
                line = line.strip().replace("\n", '')
                dat = line.split(' ')
                if dat[0] == 'v':
                    nodes.append((node_id, dat[2]))
                    node_id += 1
                elif dat[0] == 'e':
                    n_in_id = int(dat[1]) - 1
                    n_out_id = int(dat[2]) - 1
                    n_in = nodes[n_in_id]
                    n_out = nodes[n_out_id]
                    edges.append((n_in, n_out))
    return nodes, edges
