def soundness(nodes, arcs):
    # initial node: node with no input arcs
    # final node: node with no output arcs
    inode = nodes.copy()
    for arc in arcs:
        if arc[1] in inode:
            inode.remove(arc[1])
    fnode = nodes.copy()
    for arc in arcs:
        if arc[0] in fnode:
            fnode.remove(arc[0])

    if len(fnode) > 1 or len(inode) > 1:
        return False, inode, fnode

    if len(fnode) == 0 or len(inode) == 0:
        print("NO SOUND: inode and/or fnode missing!")
        return False

    return True, inode[0], fnode[0]


def fitting(V, W, inode):
    # V -> list of nodes sorted by order of execution
    p = []
    m = []
    n = [inode]
    for ev in V:
        if ev in n:
            n.remove(ev)
            p.append(ev)
            for arc in W:
                if arc[0] == ev and arc[1] not in m:
                    m.append(arc[1])
            n += m
            for p1 in p:
                if p1 in n:
                    n.remove(p1)
        else:
            print('NO FITTING')
            return False
    return True