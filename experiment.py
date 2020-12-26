import model

from matplotlib import style
import matplotlib.pyplot as plt
import numpy as np


def plot(pnodes, instructions):
    n = len(pnodes)
    fig, ax = plt.subplots()

    xlabels = np.empty(n, dtype=object)
    xlevels = np.empty(n, dtype=int)
    xticks = np.arange(start=1, stop=n + 1, step=1)
    x = np.zeros(n)
    bs = 0.4

    dx = np.ones(n)
    dy = np.ones(n)

    for i, msr in enumerate(instructions):
        xlevels[i] = i + 1
        x[i] = xticks[i] - bs

        dx[i] = bs * 2
        dy[i] = msr

    xlevels = np.sort(xlevels)
    for i in range(n):
        xlabels[i] = xlevels[i]

    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)
    ax.bar(x, dy, dx, align='edge')

    title = 'Productivity to pnodes count graph'

    ax.set_title(title)
    ax.set_xlabel('Pnodes')
    plt.show()


if __name__ == '__main__':
    pnodesMax = 20
    pnodes = [x + 1 for x in range(pnodesMax)]
    cache_size = 4000
    read_time = 2
    write_time = 5
    until = 1000 * 1000
    reruns = 3

    results = [0 for x in range(pnodesMax)]
    for i in range(pnodesMax):
        for j in range(reruns):
            results[i] += model.run(pnodes[i], cache_size, read_time, write_time, until)
        results[i] /= reruns
    for res in results:
        print('res', res)

    plot(pnodes, results)
