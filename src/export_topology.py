import sys
import typing

from config.export.file_exporter import FileConfigurationExporter
from topo.topo import TopoUtil


def main(argv: typing.List[str]):
    if len(argv) != 2:
        print("Script requires exactly two arguments!")
        exit(1)

    topo = TopoUtil.from_file(argv[0])
    # Export to file
    for name in topo.nodes:
        node = topo.nodes[name]
        config = node.get_configuration_builder(topo).build()
        exporter = FileConfigurationExporter(config, node, argv[1])
        exporter.export()


if __name__ == '__main__':
    main(sys.argv[1:])
