from heapq import heappush, heappushpop, heappop
import os
from pathlib import Path
import sys
from typing import List, Tuple


N_LARGEST = 50
"""Number of long file names to list."""


def main():
    try:
        root = sys.argv[1]

    except IndexError:
        root = Path.home() / 'Dropbox (Springboard)'

    lengths: List[Tuple[int, Path]] = []
    sizes: List[Tuple[int, Path]] = []

    print('Walking', root)

    for base, dirs, files in os.walk(root):
        for f in files:
            path = Path(base, f).resolve()

            # Store longest path lengths
            heap_to_max(lengths, (len(str(path)), path))

            # Store largest file sizes
            heap_to_max(sizes, (path.stat().st_size, path))

    print('Path lengths:')
    print_heap(lengths)
    print()

    print('File sizes:')
    print_heap(sizes)
    print()


def heap_to_max(heap, item, max_size=N_LARGEST):
        if len(heap) >= max_size:
            heappushpop(heap, item)

        else:
            heappush(heap, item)


def print_heap(heap, fmt='{0[0]:<8} {0[1]}'):
    while True:
        try:
            item = heappop(heap)
            print(fmt.format(item))
                
        except IndexError:
            break


if __name__ == "__main__":
    main()
