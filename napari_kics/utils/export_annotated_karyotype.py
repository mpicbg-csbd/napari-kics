import base64
from tempfile import NamedTemporaryFile

from skimage import io

__svg_template = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
 version="1.2"baseProfile="tiny" viewBox="0 0 {width} {height}"
 width="{svg_width}" height="{svg_height}">
    <title>{title}</title>
    <desc>{desc}</desc>
    <style>
        image {{
            image-rendering: crisp-edges;
            image-rendering: -moz-crisp-edges;
            image-rendering: pixelated;
        }}
    </style>
    <rect width="100%" height="100%" style="fill:rgba(0, 0, 0, 0.000000)" />
    <defs>
    </defs>
    <g>
        <g id="karyotype">
            <image x="0" y="0" width="{width}" height="{height}"
             preserveAspectRatio="none"
             xlink:href="data:image/png;base64,{karyotype}"/>
        </g>
        <g id="annotations" fill="{color}" stroke="{color}"
         stroke-width="{stroke_width}"
         font-size="{font_size}">
            {annotations}
        </g>
    </g>
</svg>
"""

__svg_annotation_template = """\
<g>
    <text x="{x}" y="{y}" stroke="none" transform="translate(0 -5)">{tag}: {size}</text>
    <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" />
</g>
"""


def export_svg(
    fname,
    karyotype,
    tags,
    sizes,
    bboxes,
    *,
    svg_width=1000,
    color="red",
    title="Annotated Karyotype",
    desc="Created with napari-kics.",
    stroke_width=1,
    font_size=1,
):
    height = karyotype.shape[0]
    width = karyotype.shape[1]
    scale = svg_width / width
    svg_height = scale * height
    font_size = font_size * 100 / scale
    font_size = f"{font_size}%"
    stroke_width = stroke_width / scale

    with open(fname, "w") as outsvg:
        svg_parts = __svg_template.format(
            svg_width=svg_width,
            svg_height=svg_height,
            width=width,
            height=height,
            title=title,
            desc=desc,
            color=color,
            font_size=font_size,
            stroke_width=stroke_width,
            karyotype=";;;;",
            annotations=";;;;",
        ).split(";;;;")
        assert len(svg_parts) == 3

        outsvg.write(svg_parts[0])
        with NamedTemporaryFile(suffix=".png") as temp_png:
            io.imsave(temp_png.name, karyotype, check_contrast=False)
            outsvg.write(
                str(base64.standard_b64encode(temp_png.read()), encoding="ascii")
            )

        outsvg.write(svg_parts[1])
        for tag, size, (ymin, xmin, ymax, xmax) in zip(tags, sizes, bboxes):
            outsvg.write(
                __svg_annotation_template.format(
                    x=xmin,
                    y=ymin,
                    tag=tag,
                    size=size,
                    width=xmax - xmin,
                    height=ymax - ymin,
                )
            )
        outsvg.write(svg_parts[2])


__test_data = {
    "image": f"{__file__}/../../resources/data/mHomSap_male.jpeg",
    "annotations": [
        ("02a", 7573, (56, 338, 282, 433)),
        ("01b", 7513, (31, 104, 254, 217)),
        ("01a", 7322, (25, 46, 302, 96)),
        ("02b", 6854, (35, 392, 250, 483)),
        ("03a", 6801, (62, 635, 321, 698)),
        ("05a", 6225, (56, 1671, 275, 1718)),
        ("06b", 5864, (457, 112, 666, 179)),
        ("04a", 5787, (60, 1369, 248, 1427)),
        ("03b", 5683, (68, 702, 239, 800)),
        ("04b", 5239, (63, 1437, 259, 1494)),
        ("07a", 5009, (470, 379, 657, 417)),
        ("06a", 4949, (452, 71, 641, 114)),
        ("07b", 4616, (492, 423, 656, 467)),
        ("08b", 4588, (504, 702, 633, 775)),
        ("05b", 4450, (69, 1717, 225, 1786)),
        ("09a", 4339, (514, 936, 641, 1002)),
        ("08a", 4264, (487, 652, 640, 700)),
        ("11b", 4162, (485, 1577, 631, 1642)),
        ("23a", 4123, (1269, 1846, 1415, 1896)),
        ("12a", 4100, (500, 1829, 648, 1893)),
        ("10a", 3920, (506, 1250, 650, 1294)),
        ("10b", 3888, (513, 1296, 658, 1337)),
        ("12b", 3887, (496, 1898, 641, 1950)),
        ("09b", 3754, (496, 996, 637, 1046)),
        ("13a", 3688, (925, 57, 1048, 123)),
        ("13b", 3685, (937, 125, 1042, 200)),
        ("11a", 3583, (523, 1533, 639, 1598)),
        ("14a", 3259, (919, 362, 1043, 409)),
        ("15a", 3006, (925, 665, 1049, 696)),
        ("17a", 2781, (946, 1536, 1039, 1592)),
        ("15b", 2765, (937, 705, 1042, 739)),
        ("14b", 2580, (938, 419, 1014, 500)),
        ("16a", 2531, (935, 1248, 1035, 1286)),
        ("18a", 2501, (942, 1858, 1039, 1892)),
        ("17b", 2496, (952, 1602, 1048, 1646)),
        ("18b", 2231, (941, 1902, 1037, 1933)),
        ("16b", 2186, (936, 1298, 1031, 1333)),
        ("19b", 2040, (1327, 423, 1408, 454)),
        ("20b", 2014, (1310, 704, 1396, 739)),
        ("21b", 1787, (1360, 1298, 1432, 1329)),
        ("19a", 1742, (1333, 387, 1413, 412)),
        ("20a", 1676, (1313, 665, 1389, 694)),
        ("22b", 1674, (1342, 1595, 1416, 1634)),
        ("23b", 1520, (1304, 1906, 1368, 1935)),
        ("22a", 1482, (1358, 1560, 1420, 1590)),
        ("21a", 1326, (1377, 1250, 1433, 1290)),
    ],
}


def __test():
    outsvg = "./anno-test.svg"
    karyotype = io.imread(__test_data["image"])
    tags = [d[0] for d in __test_data["annotations"]]
    areas = [d[1] for d in __test_data["annotations"]]
    bboxes = [d[2] for d in __test_data["annotations"]]

    export_svg(outsvg, karyotype, tags, areas, bboxes)


if __name__ == "__main__":
    __test()
