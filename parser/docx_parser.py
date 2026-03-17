from pathlib import Path
from typing import List
import re
from docx import Document
from docx.oxml.ns import qn
from .base import DocumentChunk

class DocxParser:
    """
    Word 文档解析器。
    策略：按标题段落（Heading样式）切分，表格单独提取为一个 chunk。
    """

    def __init__(self, min_chunk_length: int = 30):
        self.min_chunk_length = min_chunk_length

    def parse(self, file_path: str) -> List[DocumentChunk]:
        path = Path(file_path)
        doc = Document(str(path))
        filename = path.name

        segments = self._extract_segments(doc)
        result = []
        chunk_index = 0

        for seg_type, heading, content in segments:
            if len(content.strip()) < self.min_chunk_length:
                continue
            result.append(DocumentChunk.create(
                content=content.strip(),
                metadata={
                    "source": filename,
                    "file_type": "docx",
                    "chunk_index": chunk_index,
                    "heading": heading,
                    "segment_type": seg_type,  # "text" 或 "table"
                }
            ))
            chunk_index += 1

        return result

    def _extract_segments(self, doc):
        """
        遍历文档所有元素（段落 + 表格），按标题切分。
        返回 [(seg_type, heading, content), ...]
        """
        segments = []
        current_heading = ""
        current_buffer = []

        # 要同时辭历段落和表格，需要按 XML 顺序遍历 body
        body = doc.element.body
        for child in body:
            tag = child.tag.split('}')[-1]  # 取 localname

            if tag == 'p':  # 段落
                para_text = child.text_content() if hasattr(child, 'text_content') else ''.join(
                    t.text or '' for t in child.iter() if t.tag.split('}')[-1] == 't'
                )
                style_name = ''
                pPr = child.find(f'{{{child.nsmap.get("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")}}}pPr')
                if pPr is not None:
                    pStyle = pPr.find(f'{{{child.nsmap.get("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")}}}pStyle')
                    if pStyle is not None:
                        style_name = pStyle.get(f'{{{child.nsmap.get("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")}}}val', '')

                is_heading = style_name.lower().startswith('heading') or style_name in ['1', '2', '3', '4', '5']

                if is_heading and para_text.strip():
                    # 保存上一段
                    if current_buffer:
                        segments.append(("text", current_heading, "\n".join(current_buffer)))
                        current_buffer = []
                    current_heading = para_text.strip()
                elif para_text.strip():
                    current_buffer.append(para_text.strip())

            elif tag == 'tbl':  # 表格
                # 先保存当前文本 buffer
                if current_buffer:
                    segments.append(("text", current_heading, "\n".join(current_buffer)))
                    current_buffer = []
                # 提取表格为独立 chunk
                table_text = self._extract_table(child)
                if table_text.strip():
                    segments.append(("table", current_heading, table_text))

        # 处理最后剩下的 buffer
        if current_buffer:
            segments.append(("text", current_heading, "\n".join(current_buffer)))

        return segments

    def _extract_table(self, tbl_element) -> str:
        """
        将 Word 表格转为 Markdown 风格的文本。
        与其将表格丢弃，不如按行拼接成可读文本。
        """
        rows = []
        w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        for tr in tbl_element.findall(f'{{{w_ns}}}tr'):
            cells = []
            for tc in tr.findall(f'{{{w_ns}}}tc'):
                cell_text = ''.join(
                    t.text or '' for t in tc.iter() if t.tag == f'{{{w_ns}}}t'
                ).strip()
                cells.append(cell_text)
            if any(cells):  # 过滤全空行
                rows.append(' | '.join(cells))
        return "[TABLE]\n" + "\n".join(rows)