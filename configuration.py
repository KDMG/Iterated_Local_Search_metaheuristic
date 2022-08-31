def parameters():
    # total trace to analyze
    tot = 20
    # tot = "max"

    # gamma = 0 e beta = 0.75 -> best values by experiments in gap gen and gap move terms
    beta = 0.75
    gamma = 0
    T = 500
    iter = 50
    a = 0.8
    k = 2
    return tot, T, iter, a, k, beta, gamma


def search_path():
    npath = "BPI2012_SE_08.pnml"
    lpath = "BPI2012_SE.xes"
    # npath = "01_testBank2000NoRandomNoise_petriNet.pnml"
    # lpath = "01_testBank2000NoRandomNoise.xes"

    return npath, lpath

def format_final_data(d):
    if type(d) is tuple:
        gen = d.pop()
        res = d.pop()
        if res:
            res = "t_out"
        else:
            res = "no_pt"
    else:
        gen = d
        res = '-'

    return gen, res