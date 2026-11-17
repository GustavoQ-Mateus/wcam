from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from av import VideoFrame
from av.filter import Graph
from av.filter.context import FilterContext
from av.video.format import VideoFormat

from wcam.media.color_correction import IDENTITY_TABLE, ColorTables
from wcam.virtualcam.sink import I420Frame

TABLE_ENTRIES = 256
GRAPH_TIME_BASE = Fraction(1, 90_000)
TABLE_FILTER = "lut"
MIRROR_FILTER = "hflip"
SINK_FILTER = "buffersink"


@dataclass(frozen=True, slots=True)
class TranslationKey:
    width: int
    height: int
    pixel_format: str
    tables: ColorTables | None
    mirror: bool


def table_expression(table: bytes, low: int = 0, high: int = TABLE_ENTRIES) -> str:
    # FFmpeg's lut filter takes an expression per plane, so the table becomes an exact binary search over val.
    if high - low == 1:
        return str(table[low])
    middle = (low + high) // 2
    below = table_expression(table, low, middle)
    above = table_expression(table, middle, high)
    return rf"if(lt(val\,{middle})\,{below}\,{above})"


class PlaneTranslator:
    def __init__(self) -> None:
        self._key: TranslationKey | None = None
        self._graph: Graph | None = None
        self.graphs_built = 0

    def translated(self, frame: VideoFrame, tables: ColorTables | None, *, mirror: bool) -> I420Frame:
        graph = self._graph_for(TranslationKey(frame.width, frame.height, frame.format.name, tables, mirror))
        graph.vpush(frame)
        array: I420Frame = np.ascontiguousarray(graph.vpull().to_ndarray(), dtype=np.uint8)
        return array

    def _graph_for(self, key: TranslationKey) -> Graph:
        if self._graph is None or key != self._key:
            self._graph = translation_graph(key)
            self._key = key
            self.graphs_built += 1
        return self._graph


def translation_graph(key: TranslationKey) -> Graph:
    graph = Graph()
    pixel_format = VideoFormat(key.pixel_format, key.width, key.height)
    last = graph.add_buffer(width=key.width, height=key.height, format=pixel_format, time_base=GRAPH_TIME_BASE)
    if key.tables is not None:
        last = linked(graph, last, TABLE_FILTER, table_arguments(key.tables))
    if key.mirror:
        last = linked(graph, last, MIRROR_FILTER)
    linked(graph, last, SINK_FILTER)
    graph.configure()
    return graph


def table_arguments(tables: ColorTables) -> str:
    luma_table, chroma_table = tables
    chroma = table_expression(chroma_table)
    if chroma_table == IDENTITY_TABLE:
        chroma = "val"
    return f"y={table_expression(luma_table)}:u={chroma}:v={chroma}"


def linked(graph: Graph, previous: FilterContext, name: str, arguments: str | None = None) -> FilterContext:
    node = graph.add(name, arguments)
    previous.link_to(node)
    return node
