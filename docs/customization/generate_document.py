"""Generate the customization handover DOCX from its Markdown source (stdlib only)."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
import re

ROOT = Path(__file__).parent
NAME = 'Optix_Complete_Customization_Guide'

def paragraph(text, style='Normal'):
    text = text.replace('`', '')
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def table(rows):
    n = len(rows[0])
    widths = [9360 // n] * n
    parts = ['<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>']
    parts += [f'<w:{s} w:val="single" w:sz="4" w:color="D5DFE8"/>' for s in ['top','left','bottom','right','insideH','insideV']]
    parts += ['</w:tblBorders></w:tblPr><w:tblGrid>', *[f'<w:gridCol w:w="{v}"/>' for v in widths], '</w:tblGrid>']
    for i, row in enumerate(rows):
        parts.append('<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if i == 0 else '') + '</w:trPr>')
        for cell, width in zip(row, widths):
            shade = '<w:shd w:fill="E8F0F7"/>' if i == 0 else ''
            parts.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}</w:tcPr>{paragraph(cell, "TableText")}</w:tc>')
        parts.append('</w:tr>')
    return ''.join(parts) + '</w:tbl>'

lines = (ROOT / f'{NAME}.md').read_text().splitlines()
body = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            cells = [c.strip() for c in lines[i].strip('|').split('|')]
            if not all(re.fullmatch(r'[-: ]+', c) for c in cells):
                rows.append(cells)
            i += 1
        body.append(table(rows))
        continue
    if line.startswith('# '): body.append(paragraph(line[2:], 'Title'))
    elif line.startswith('## '): body.append(paragraph(line[3:], 'Heading1'))
    elif line.startswith('### '): body.append(paragraph(line[4:], 'Heading2'))
    elif line: body.append(paragraph(line, 'ListText' if re.match(r'^(\d+\.|-) ', line) else 'Normal'))
    i += 1
ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
styles = f'''<w:styles xmlns:w="{ns}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="21"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="110" w:line="260" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'''
for name, size, color in [('Normal',21,'243447'),('Title',36,'163D61'),('Heading1',28,'163D61'),('Heading2',24,'246386'),('TableText',19,'243447'),('ListText',21,'243447')]:
    heading = name in ('Title','Heading1','Heading2')
    props = '<w:keepNext/><w:spacing w:before="240" w:after="120"/>' if heading else ''
    outline = '<w:outlineLvl w:val="0"/>' if name == 'Heading1' else '<w:outlineLvl w:val="1"/>' if name == 'Heading2' else ''
    styles += f'<w:style w:type="paragraph" w:styleId="{name}"><w:name w:val="{name}"/><w:pPr>{props}{outline}</w:pPr><w:rPr>{"<w:b/>" if heading else ""}<w:color w:val="{color}"/><w:sz w:val="{size}"/></w:rPr></w:style>'
styles += '</w:styles>'
document = f'<w:document xmlns:w="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>' + ''.join(body) + '<w:sectPr><w:footerReference w:type="default" r:id="rId2"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1080" w:right="1273" w:bottom="1080" w:left="1273" w:footer="540"/></w:sectPr></w:body></w:document>'
footer = f'<w:ftr xmlns:w="{ns}"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:t>Optix Customization Guide | Page </w:t></w:r><w:fldSimple w:instr="PAGE"/></w:p></w:ftr>'
ct = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' + ''.join(f'<Override PartName="/word/{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{typ}+xml"/>' for part,typ in [('document','document.main'),('styles','styles'),('footer1','footer')]) + '</Types>'
rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
docrels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'
with ZipFile(ROOT / f'{NAME}.docx', 'w', ZIP_DEFLATED) as z:
    for path, data in [('word/document.xml',document),('word/styles.xml',styles),('word/footer1.xml',footer),('[Content_Types].xml',ct),('_rels/.rels',rels),('word/_rels/document.xml.rels',docrels)]: z.writestr(path,data)
print(ROOT / f'{NAME}.docx')
