from collections import namedtuple
import numpy as np
import math


class ChromosomeLabel(namedtuple("ChromosomeLabel", ["major", "minor", "row", "col"])):
    __slots__ = ()

    def __str__(self):
        return f"{self.major:02d}{chr(ord('a') + self.minor)}"

    def __lt__(self, other):
        if isinstance(other, ChromosomeLabel):
            return super().__lt__(other)
        else:
            return str(self) < str(other)

    def __gt__(self, other):
        if isinstance(other, ChromosomeLabel):
            return super().__gt__(other)
        else:
            return str(self) < str(other)

    def __eq__(self, other):
        if isinstance(other, ChromosomeLabel):
            return super().__gt__(other)
        else:
            return str(self) < str(other)


class IndexedInterval(namedtuple("IndexedInterval", ["begin", "end", "index"])):
    __slots__ = ()

    @property
    def empty(self):
        return self.begin >= self.end

    def overlaps(self, other, *, strict=False):
        if self.begin > other.begin:
            return other.overlaps(begin, strict=strict)

        if strict:
            return other.begin < self.end and not self.empty and not other.empty
        else:
            return other.begin <= self.end

    def merge(self, other, merge_index):
        return IndexedInterval(
            min(self.begin, other.begin),
            max(self.end, other.end),
            merge_index(self.index, other.index),
        )


def guess_chromosome_labels(bboxes):
    # Collect rows as bounding boxes that overlap on the y-axis

    # Generate list of intervals with original index
    intervals = list(
        IndexedInterval(bbox[0], bbox[2], i) for i, bbox in enumerate(bboxes)
    )
    # Sort by y-begin (end and index break ties)
    intervals.sort()

    # Merge overlapping intervals into rows collecting indices on the way
    rows = [IndexedInterval(intervals[0].begin, intervals[0].end, [intervals[0].index])]
    for interval in intervals[1:]:
        if rows[-1].overlaps(interval):
            rows[-1] = rows[-1].merge(interval, lambda is_, i: is_ + [i])
        else:
            rows.append(IndexedInterval(interval.begin, interval.end, [interval.index]))

    # Reduce rows to list of indices
    rows = [row.index for row in rows]

    # Cluster chromosome pairs for each row separately
    for i, row in enumerate(rows):
        # Generate list of intervals with original index
        row = list(IndexedInterval(bboxes[i][1], bboxes[i][3], i) for i in row)
        # Sort by x-begin (end and index break ties)
        row.sort()

        cutoff = -np.inf

        if len(row) > 1:
            # Compute distances between objects for clustering
            dists = np.fromiter(
                (int2.begin - int1.end for int1, int2 in zip(row, row[1:])),
                dtype=np.int_,
                count=len(row) - 1,
            )
            dists.sort()

            # find pair of distances
            abs_min = 0.1 * dists[-1]
            rel_min = 2
            for x1, x2 in zip(dists, dists[1:]):
                if x1 >= abs_min and rel_min * x1 >= x2:
                    break
                cutoff = x1

        # Cluster according to cutoff
        rows[i] = [[row[0].index]]
        for int1, int2 in zip(row, row[1:]):
            if int2.begin - int1.end <= cutoff:
                rows[i][-1].append(int2.index)
            else:
                rows[i].append([int2.index])

    # Create labels from clustering into rows and chromsome pairs
    chr_labels = [None] * len(bboxes)
    chr_number = 1
    for i, row in enumerate(rows):
        for j, chr_cluster in enumerate(row):
            for sub_id, label_idx in enumerate(chr_cluster):
                chr_labels[label_idx] = ChromosomeLabel(chr_number, sub_id, i, j)
            chr_number += 1

    return chr_labels


def print_test_example():
    bboxes = [
        (50, 364, 179, 423),
        (51, 551, 160, 612),
        (52, 158, 171, 217),
        (52, 482, 163, 547),
        (54, 84, 179, 153),
        (54, 295, 183, 359),
        (101, 689, 141, 729),
        (101, 735, 142, 775),
        (219, 300, 285, 355),
        (219, 361, 285, 419),
        (220, 86, 293, 148),
        (221, 472, 287, 541),
        (221, 662, 278, 731),
        (221, 908, 284, 961),
        (222, 544, 288, 609),
        (223, 739, 276, 801),
        (226, 153, 291, 210),
        (226, 833, 275, 901),
        (348, 291, 402, 356),
        (349, 909, 386, 967),
        (350, 359, 401, 424),
        (350, 544, 408, 602),
        (350, 671, 403, 730),
        (351, 852, 390, 903),
        (352, 735, 403, 786),
        (357, 480, 408, 541),
        (358, 81, 404, 146),
        (358, 153, 407, 216),
        (458, 677, 507, 728),
        (461, 909, 503, 955),
        (462, 545, 507, 592),
        (463, 360, 500, 411),
        (465, 734, 501, 777),
        (466, 863, 506, 902),
        (467, 492, 505, 537),
        (469, 144, 512, 198),
        (470, 292, 507, 353),
        (471, 87, 508, 140),
        (552, 675, 634, 726),
        (556, 738, 638, 789),
        (567, 933, 596, 972),
        (568, 139, 605, 188),
        (568, 876, 597, 915),
        (570, 96, 609, 134),
        (574, 322, 601, 351),
        (574, 356, 596, 385),
    ]

    lbls = guess_chromosome_labels(bboxes)
    lbls.sort(key=lambda l: (l.row, l.col))

    last_row = 0
    last_major = -1
    for l in lbls:
        if l.row != last_row:
            last_major = -1
            print()

        if last_major < 0:
            pass
        elif last_major == l.major:
            print(",", end="")
        else:
            print("  ", end="")

        print(str(l), end="")

        last_row = l.row
        last_major = l.major
    print()


if __name__ == "__main__":
    print_test_example()
