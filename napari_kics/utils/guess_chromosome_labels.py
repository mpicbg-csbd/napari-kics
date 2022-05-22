import re
from collections import namedtuple

import numpy as np


class ChromosomeLabel(namedtuple("ChromosomeLabel", ["major", "minor", "row", "col"])):
    __slots__ = ()
    label_re = re.compile(r"^0*(?P<major>[0-9]+)(?P<minor>[a-z])$")

    def __new__(cls, major, minor, row=None, col=None):
        return super().__new__(cls, major, minor, row, col)

    @staticmethod
    def from_string(string):
        match = ChromosomeLabel.label_re.fullmatch(string)

        if not match:
            raise ValueError("invalid string format")

        major = int(match["major"])
        minor = ord(match["minor"]) - ord("a")

        return ChromosomeLabel(major, minor)

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
            return super().__eq__(other)
        else:
            return str(self) == str(other)


class IndexedInterval(namedtuple("IndexedInterval", ["begin", "end", "index"])):
    __slots__ = ()

    @property
    def size(self):
        return self.end - self.begin

    @property
    def empty(self):
        return self.begin >= self.end

    def overlaps(self, other, *, strict=False):
        if self.begin > other.begin:
            return other.overlaps(self, strict=strict)
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


def guess_chromosome_labels(bboxes, *, debug=False):
    # Collect rows as bounding boxes that overlap on the y-axis
    if debug:
        print(f"[guess_chromosome_labels] bboxes={bboxes}")

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

            if debug:
                print(f"[guess_chromosome_labels] dists={dists}")
            rel_min = 4
            try:
                cutoff = max(
                    x1 for x1, x2 in zip(dists, dists[1:]) if x1 * rel_min <= x2
                )
            except Exception:
                cutoff = -np.inf

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


def run_guess_tests():
    test_cases = [
        {
            "name": "first",
            "bboxes": [
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
            ],
            "expected": [
                ChromosomeLabel(1, 0, 0, 0),
                ChromosomeLabel(1, 1, 0, 0),
                ChromosomeLabel(2, 0, 0, 1),
                ChromosomeLabel(2, 1, 0, 1),
                ChromosomeLabel(3, 0, 0, 2),
                ChromosomeLabel(3, 1, 0, 2),
                ChromosomeLabel(4, 0, 0, 3),
                ChromosomeLabel(4, 1, 0, 3),
                ChromosomeLabel(5, 0, 1, 0),
                ChromosomeLabel(5, 1, 1, 0),
                ChromosomeLabel(6, 0, 1, 1),
                ChromosomeLabel(6, 1, 1, 1),
                ChromosomeLabel(7, 0, 1, 2),
                ChromosomeLabel(7, 1, 1, 2),
                ChromosomeLabel(8, 0, 1, 3),
                ChromosomeLabel(8, 1, 1, 3),
                ChromosomeLabel(9, 0, 1, 4),
                ChromosomeLabel(9, 1, 1, 4),
                ChromosomeLabel(10, 0, 2, 0),
                ChromosomeLabel(10, 1, 2, 0),
                ChromosomeLabel(11, 0, 2, 1),
                ChromosomeLabel(11, 1, 2, 1),
                ChromosomeLabel(12, 0, 2, 2),
                ChromosomeLabel(12, 1, 2, 2),
                ChromosomeLabel(13, 0, 2, 3),
                ChromosomeLabel(13, 1, 2, 3),
                ChromosomeLabel(14, 0, 2, 4),
                ChromosomeLabel(14, 1, 2, 4),
                ChromosomeLabel(15, 0, 3, 0),
                ChromosomeLabel(15, 1, 3, 0),
                ChromosomeLabel(16, 0, 3, 1),
                ChromosomeLabel(16, 1, 3, 1),
                ChromosomeLabel(17, 0, 3, 2),
                ChromosomeLabel(17, 1, 3, 2),
                ChromosomeLabel(18, 0, 3, 3),
                ChromosomeLabel(18, 1, 3, 3),
                ChromosomeLabel(19, 0, 3, 4),
                ChromosomeLabel(19, 1, 3, 4),
                ChromosomeLabel(20, 0, 4, 0),
                ChromosomeLabel(20, 1, 4, 0),
                ChromosomeLabel(21, 0, 4, 1),
                ChromosomeLabel(21, 1, 4, 1),
                ChromosomeLabel(22, 0, 4, 2),
                ChromosomeLabel(22, 1, 4, 2),
                ChromosomeLabel(23, 0, 4, 3),
                ChromosomeLabel(23, 1, 4, 3),
            ],
        },
        {
            "name": "human1",
            "bboxes": [
                (25, 46, 302, 97),
                (30, 104, 254, 216),
                (35, 392, 249, 483),
                (56, 338, 282, 433),
                (56, 1670, 276, 1718),
                (59, 1369, 248, 1428),
                (62, 635, 322, 698),
                (63, 1436, 259, 1493),
                (68, 701, 239, 799),
                (69, 1717, 226, 1787),
                (452, 71, 641, 114),
                (457, 112, 665, 180),
                (470, 380, 657, 417),
                (484, 1577, 631, 1642),
                (487, 651, 640, 700),
                (492, 423, 655, 467),
                (496, 995, 638, 1046),
                (496, 1898, 641, 1950),
                (499, 1830, 649, 1893),
                (504, 701, 634, 776),
                (506, 1251, 650, 1294),
                (513, 1296, 658, 1337),
                (514, 936, 641, 1002),
                (523, 1533, 639, 1597),
                (920, 361, 1043, 410),
                (926, 57, 1049, 123),
                (926, 665, 1049, 697),
                (935, 1248, 1036, 1287),
                (936, 125, 1042, 201),
                (936, 1298, 1032, 1333),
                (937, 419, 1014, 500),
                (937, 705, 1043, 739),
                (941, 1902, 1037, 1933),
                (942, 1857, 1040, 1892),
                (946, 1536, 1039, 1593),
                (951, 1602, 1049, 1647),
                (1269, 1845, 1415, 1897),
                (1305, 1906, 1368, 1935),
                (1309, 704, 1396, 739),
                (1313, 665, 1389, 694),
                (1326, 423, 1408, 454),
                (1332, 387, 1413, 412),
                (1342, 1595, 1416, 1634),
                (1358, 1560, 1420, 1591),
                (1360, 1298, 1433, 1329),
                (1377, 1251, 1433, 1290),
            ],
            "expected": [
                ChromosomeLabel(1, 0, 0, 0),
                ChromosomeLabel(1, 1, 0, 0),
                ChromosomeLabel(2, 0, 0, 1),
                ChromosomeLabel(2, 1, 0, 1),
                ChromosomeLabel(3, 0, 0, 2),
                ChromosomeLabel(3, 1, 0, 2),
                ChromosomeLabel(4, 0, 0, 3),
                ChromosomeLabel(4, 1, 0, 3),
                ChromosomeLabel(5, 0, 0, 4),
                ChromosomeLabel(5, 1, 0, 4),
                ChromosomeLabel(6, 0, 1, 0),
                ChromosomeLabel(6, 1, 1, 0),
                ChromosomeLabel(7, 0, 1, 1),
                ChromosomeLabel(7, 1, 1, 1),
                ChromosomeLabel(8, 0, 1, 2),
                ChromosomeLabel(8, 1, 1, 2),
                ChromosomeLabel(9, 0, 1, 3),
                ChromosomeLabel(9, 1, 1, 3),
                ChromosomeLabel(10, 0, 1, 4),
                ChromosomeLabel(10, 1, 1, 4),
                ChromosomeLabel(11, 0, 1, 5),
                ChromosomeLabel(11, 1, 1, 5),
                ChromosomeLabel(12, 0, 1, 6),
                ChromosomeLabel(12, 1, 1, 6),
                ChromosomeLabel(13, 0, 2, 0),
                ChromosomeLabel(13, 1, 2, 0),
                ChromosomeLabel(14, 0, 2, 1),
                ChromosomeLabel(14, 1, 2, 1),
                ChromosomeLabel(15, 0, 2, 2),
                ChromosomeLabel(15, 1, 2, 2),
                ChromosomeLabel(16, 0, 2, 3),
                ChromosomeLabel(16, 1, 2, 3),
                ChromosomeLabel(17, 0, 2, 4),
                ChromosomeLabel(17, 1, 2, 4),
                ChromosomeLabel(18, 0, 2, 5),
                ChromosomeLabel(18, 1, 2, 5),
                ChromosomeLabel(19, 0, 3, 0),
                ChromosomeLabel(19, 1, 3, 0),
                ChromosomeLabel(20, 0, 3, 1),
                ChromosomeLabel(20, 1, 3, 1),
                ChromosomeLabel(21, 0, 3, 2),
                ChromosomeLabel(21, 1, 3, 2),
                ChromosomeLabel(22, 0, 3, 3),
                ChromosomeLabel(22, 1, 3, 3),
                ChromosomeLabel(23, 0, 3, 4),
                ChromosomeLabel(23, 1, 3, 4),
            ],
        },
        {
            "name": "human2",
            "bboxes": [
                (28, 169, 214, 219),
                (37, 453, 227, 494),
                (54, 912, 214, 950),
                (55, 654, 218, 691),
                (55, 959, 203, 998),
                (59, 71, 214, 159),
                (66, 698, 214, 747),
                (72, 1236, 211, 1274),
                (73, 376, 214, 440),
                (93, 1158, 197, 1229),
                (323, 93, 463, 131),
                (334, 41, 463, 84),
                (342, 438, 462, 469),
                (346, 290, 463, 338),
                (350, 667, 455, 709),
                (350, 1019, 463, 1054),
                (351, 478, 463, 515),
                (351, 617, 460, 656),
                (353, 1065, 463, 1099),
                (355, 231, 461, 281),
                (361, 868, 462, 918),
                (361, 1199, 462, 1239),
                (376, 811, 462, 857),
                (382, 1249, 446, 1304),
                (570, 284, 670, 318),
                (573, 62, 671, 96),
                (577, 552, 672, 589),
                (578, 103, 671, 138),
                (587, 334, 672, 368),
                (588, 965, 670, 999),
                (589, 773, 671, 807),
                (592, 509, 672, 543),
                (597, 731, 671, 764),
                (600, 1199, 670, 1230),
                (605, 1240, 672, 1275),
                (608, 1009, 671, 1054),
                (780, 1010, 896, 1043),
                (830, 117, 894, 147),
                (836, 310, 898, 344),
                (836, 1231, 897, 1263),
                (837, 68, 896, 109),
                (837, 350, 896, 382),
                (843, 768, 895, 799),
                (843, 809, 896, 840),
                (845, 579, 894, 611),
                (850, 539, 896, 572),
            ],
            "expected": [
                ChromosomeLabel(1, 0, 0, 0),
                ChromosomeLabel(1, 1, 0, 0),
                ChromosomeLabel(2, 0, 0, 1),
                ChromosomeLabel(2, 1, 0, 1),
                ChromosomeLabel(3, 0, 0, 2),
                ChromosomeLabel(3, 1, 0, 2),
                ChromosomeLabel(4, 0, 0, 3),
                ChromosomeLabel(4, 1, 0, 3),
                ChromosomeLabel(5, 0, 0, 4),
                ChromosomeLabel(5, 1, 0, 4),
                ChromosomeLabel(6, 0, 1, 0),
                ChromosomeLabel(6, 1, 1, 0),
                ChromosomeLabel(7, 0, 1, 1),
                ChromosomeLabel(7, 1, 1, 1),
                ChromosomeLabel(8, 0, 1, 2),
                ChromosomeLabel(8, 1, 1, 2),
                ChromosomeLabel(9, 0, 1, 3),
                ChromosomeLabel(9, 1, 1, 3),
                ChromosomeLabel(10, 0, 1, 4),
                ChromosomeLabel(10, 1, 1, 4),
                ChromosomeLabel(11, 0, 1, 5),
                ChromosomeLabel(11, 1, 1, 5),
                ChromosomeLabel(12, 0, 1, 6),
                ChromosomeLabel(12, 1, 1, 6),
                ChromosomeLabel(13, 0, 2, 0),
                ChromosomeLabel(13, 1, 2, 0),
                ChromosomeLabel(14, 0, 2, 1),
                ChromosomeLabel(14, 1, 2, 1),
                ChromosomeLabel(15, 0, 2, 2),
                ChromosomeLabel(15, 1, 2, 2),
                ChromosomeLabel(16, 0, 2, 3),
                ChromosomeLabel(16, 1, 2, 3),
                ChromosomeLabel(17, 0, 2, 4),
                ChromosomeLabel(17, 1, 2, 4),
                ChromosomeLabel(18, 0, 2, 5),
                ChromosomeLabel(18, 1, 2, 5),
                ChromosomeLabel(19, 0, 3, 0),
                ChromosomeLabel(19, 1, 3, 0),
                ChromosomeLabel(20, 0, 3, 1),
                ChromosomeLabel(20, 1, 3, 1),
                ChromosomeLabel(21, 0, 3, 2),
                ChromosomeLabel(21, 1, 3, 2),
                ChromosomeLabel(22, 0, 3, 3),
                ChromosomeLabel(22, 1, 3, 3),
                ChromosomeLabel(23, 0, 3, 4),
                ChromosomeLabel(24, 0, 3, 5),
            ],
        },
    ]

    for test_case in test_cases:
        lbls = guess_chromosome_labels(test_case["bboxes"])
        combined = list(zip(lbls, test_case["bboxes"]))
        combined.sort(key=lambda x: (x[0].row, x[0].col, x[1][1]))

        if [label for label, _ in combined] != test_case["expected"]:
            print(f"test case {test_case['name']} failed:")
            print()
            print(str(combined[0][0]), end="")
            for (last_label, last_bbox), (curr_label, curr_bbox) in zip(
                combined, combined[1:]
            ):
                dist = curr_bbox[1] - last_bbox[3]
                if last_label.row != curr_label.row:
                    print()
                elif last_label.major == curr_label.major:
                    print(f"[{dist}]", end="")
                else:
                    print(f"  <{dist}>  ", end="")

                print(str(curr_label), end="")
            print()


def run_from_string_test():
    assert ChromosomeLabel.from_string("00a") == ChromosomeLabel(0, 0)
    assert ChromosomeLabel.from_string("000001337z") == ChromosomeLabel(1337, 25)
    try:
        ChromosomeLabel.from_string("32")
        assert False
    except ValueError:
        pass

    try:
        ChromosomeLabel.from_string("A")
        assert False
    except ValueError:
        pass


def run_to_string_test():
    assert str(ChromosomeLabel(0, 0)) == "00a"
    assert str(ChromosomeLabel(1337, 25)) == "1337z"


if __name__ == "__main__":
    run_guess_tests()
    run_from_string_test()
    run_to_string_test()
