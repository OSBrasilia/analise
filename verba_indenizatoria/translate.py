#!/usr/bin/env python3

from elasticsearch import Elasticsearch
from pathlib import Path
import re
import sys
import textract
import json
import csv
from bisect import bisect_right, bisect_left

class Record(object):
    """This class represents a record extracted from the PDF storing the order of the day."""

    page_footer = re.compile(r'^Página \d+ de \d+$', re.IGNORECASE | re.MULTILINE)

    line_start_pattern = re.compile(r'^\s+')

    def __init__(self):
        self.doc = {}
        self._lines = []
        self._last = None
        self._line_start = None
        self._num = 0

    def _put_section(self, field, section):
        if field in self.doc:
            self.doc[field].append(section)
        else:
            self.doc[field] = [section]

    def _append(self, line):
        self._last = line
        self._num = self._num + 1
        self._lines.append(self._last)
        print('\t>> pushed (%3d) %s' % (self._num, self._last))

    def _take(self, line, join_words=True, ignore=None):
        self._raw_line = line
        words = line.split()
        start = 0
        cols = []
        self._words = []
        for i, w in enumerate(words):
            if ignore is not None and ignore(w, i):
                continue
            idx = line.index(w, start)
            if len(self._words) == 0 or not join_words or cols[-1] + len(self._words[-1]) + 1 < idx:
                cols.append(idx)
                start = cols[-1] + len(w)
                self._words.append(w)
            else:
                self._words[-1] = self._words[-1] + ' ' + w
        self._word_starts = cols
        self._last = line.strip()
        return self._last

    def _take_until(self, txt, matcher):
        """Reads lines until they match the given condition.

           Returns: the line that matched, stripped.
        """
        for line in txt:
            l2 = self._take(line)
            if matcher(l2):
                print('\t>> match found: (%3d) %s' % (self._num + 1, l2))
                return l2
            elif len(l2) > 0:
                self._append(l2)
            else:
                # skip empty string
                pass
        return None

    def _title(self, entry):
        return entry.get('title')

    def _items(self, entry):
        return entry.items()

    def _write_json(self, json_path):
        with json_path.open('w') as out:
            out.write(json.dumps(self.doc, indent=2))
        print('Wrote %s' % (json_path))

    def _write_md(self, processed_path):
        with processed_path.open('w') as out:
            for (field, content) in self.doc.items():
                out.write('\n## %s' % field)
                if isinstance(content, list):
                    for entry in content:
                        if isinstance(entry, dict):
                            title = self._title(entry)
                            if title is not None:
                                out.write('\n### %s' % title)
                            for key, value in self._items(entry):
                                out.write('\n\t* %s: %r' % (key, value))
                        else:
                            out.write('\n%s\n' % entry)
                else:
                    out.write('\n%r\n\n' % content)

            out.write('\n* * *\n')


    def write(self, file_path):
        self._write_json(file_path.with_suffix('.json'))
        self._write_md(file_path.with_suffix('.processed.md'))


class VerbaRecord(Record):

    months = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    month_pattern = re.compile(r'(' + '|'.join(months) + r')', re.IGNORECASE)
    date_pattern = re.compile(r'^\s*(' + '|'.join(months) + r').* de (\d\d\d\d)\s*$', re.IGNORECASE)

    columns = ['Deputado (a)', 'Imóvel', 'Máquina e equipamento', 'Veìculo', 'Combustível e lubrificante',
            'Assesoria ou consultoria', 'Divulgação de atividade parlamentar', 'Outros', 'Total']

    def extract_date(line):
        m = VerbaRecord.date_pattern.fullmatch(line)
        if m is not None:
            (month, year) = m.groups()
            num_month = VerbaRecord.months.index(month.lower()) + 1
            num_year = int(year)
            print('\t>>month: %s (%d)' % (month, num_month))
            print('\t>>year: %d' % num_year)
            return (num_year, num_month)

    def extract_month(line):
        m = VerbaRecord.month_pattern.findall(line)
        if len(m) > 0:
            month = m[0].lower()

    def __init__(self, file_path):
        Record.__init__(self)
        self._file_path = file_path
        self._rows = []
        self._columns = {}

    def _read_row(self, raw_line):
        self._take(raw_line, join_words=True, ignore=lambda w, i: w == '-' or w == 'R$')
        row = []
        line_length = len(raw_line)
        num_cols = len(VerbaRecord.columns)
        column_scheme = self._columns.get(line_length)
        if column_scheme is None:
            col_width = line_length / num_cols
            column_scheme = [(i * col_width) + (col_width / 2) for i in range(num_cols)]
            print('\t>> Creating row scheme for (line=%d,cols=%d): %r' % (line_length, num_cols, column_scheme))
            self._columns[line_length] = column_scheme
        for i_word, w in enumerate(self._words):
            word_start = self._word_starts[i_word]
            word_end = self._word_starts[i_word] + len(w)
            col_start = bisect_left(column_scheme, word_start)
            col_end = bisect_right(column_scheme, word_end)
            if col_start + 1 == col_end:
                # Normal: word overlaps with midpoint.
                # print('Normal: word %d ends after col %d midpoint: "%s" in "%s"' % (i_word, col_start, w, raw_line))
                pass
            elif col_start + 1 < col_end:
                # more than one column?
                print('Attention: word %d spans columns %d-%d: "%s" in "%s"' % (i_word, col_start, col_end, w, raw_line))
            elif col_start == col_end and col_end == 0:
                # word ends before first midpoint.
                print('Attention: word %d ends before col %d midpoint: "%s" in "%s"' % (i_word, col_start, w, raw_line))
                col_end = 1
            row.append(dict(word=w, i_word=i_word, col_start=col_start, col_end=col_end, word_start=word_start))
        row_number = len(self._rows)
        if len(row) == 0:
            print('\t>> Row discarded: %r\n\t   (line="%s")' % (row, raw_line))
            return False
        print('\t>> Row added: %r' % row)
        self._rows.append(row)
        self._append(self._raw_line)
        return True

    def _title(self, entry):
        return entry.get(VerbaRecord.columns[0], 'Sem nome')

    def _items(self, entry):
        for col in VerbaRecord.columns[1:]:
            if col in entry:
                yield col, entry[col]

    def _flush_table(self, field):
        for row in self._rows:
            if len(row) == 0:
                continue
            print('\t>> Row: %s' % row)
            section = { VerbaRecord.columns[col['col_end'] - 1]: col['word'] for col in row}
            print('\t>> Section: %s' % section)
            self._put_section(field, section)
        self._lines.clear()

    def _read_headers(self, lines):
        header_lines = []
        while True:
            self._take(lines.readline())
            if (self._word_starts and self._word_starts[0] == 0) or self._last.endswith(',00'):
                break
            elif self._last.strip().casefold().startswith('atual'):
                self.doc['updted'] = self._last
                self._lines.clear()
            else:
                header_lines.append(self._raw_line)
        return header_lines

    def read(self, lines):
        self._take_until(lines, lambda l: l.strip().casefold().startswith('locação'))
        (year, month) = (None, None)
        parsed_date = VerbaRecord.extract_date(self._lines[-1])
        if parsed_date is None:
            parsed_date = VerbaRecord.extract_date(self._lines[-2])
        if parsed_date is None:
            years = re.findall(r'\b20\d\d\b', self._file_path.name)
            if len(years) > 0:
                year = int(years[0])
            m = VerbaRecord.month_pattern.findall(self._file_path.name)
            if len(m) == 0:
                m = VerbaRecord.month_pattern.findall(self._lines[-2])
            if len(m) > 0:
                month = VerbaRecord.months.index(m[0].lower()) + 1
        else:
            print('\t>>Parsed date: %r' % (parsed_date,))
            (year, month) = parsed_date

        assert year is not None and month is not None, 'Could not determine date for file: %s' % self._file_path
        self.doc['year'] = year
        self.doc['month'] = month
        self.doc['date'] = '%04d-%02d' % (year, month)

        self._lines.clear()
        self._read_headers(lines)
        last = True
        while last and not self._raw_line.startswith('('):
            last = self._read_row(self._raw_line)
            self._raw_line = lines.readline()
        self._flush_table('rows')
        print('\t>> Finished file: %s: year=%d, month=%d, date=%s' % (self._file_path, self.doc['year'], self.doc['month'], self.doc['date']))


    def write(self, file_path):
        Record.write(self, file_path)
        self._write_csv(file_path.with_suffix('.csv'))

    def _write_csv(self, file_path):
        with file_path.open('w') as out:
            writer = csv.writer(out, delimiter=';')
            writer.writerow(VerbaRecord.columns)
            for doc in self.doc['rows']:
                row = [doc.get(col, '') for col in VerbaRecord.columns]
                writer.writerow(row)
        print('Wrote %s' % (file_path))


def extract_text(pdf_path, **args):
    """Extracts the text from the given pdf."""
    text = textract.process(str(pdf_path), **args)
    text_path = pdf_path.with_suffix('.txt')
    with text_path.open('wb') as out:
        out.write(text)
    print('wrote %s' % text_path)
    return text_path

def setup_index():
    """Sets up the index in Elasticsearch."""
    es = Elasticsearch()
    name = 'ordem_do_dia'
    if not es.indices.exists(index=name):
        print('Creating index "%s"...' % name)
        es.indices.create(index=name)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s [setup|order|verba]' % sys.argv[0])
        sys.exit(-1)
    cmd = sys.argv[1]
    file_path = Path(sys.argv[2]) if len(sys.argv) >= 2 else None
    if cmd == 'setup':
        setup_index()
    elif cmd == 'order':
        text_path = sys.argv[2]
        record = OrderRecord()
        record.read(text_path)
        record.write(text_path.with_suffix('.json'))
    elif cmd == 'verba':
        if file_path is None or not file_path.exists():
            raise Exception('You must specify a valid file (got: %r)' % file_path)
        elif file_path.suffix == '.pdf':
            file_path = extract_text(file_path, layout=True)
        with file_path.open('r') as txt:
            record = VerbaRecord(file_path)
            record.read(txt)
            record.write(file_path.with_suffix('.json'))

    else:
        pdf_path = Path(sys.argv[1])
        if not pdf_path.exists():
            raise Exception('You must specify a valid PDF file (got: %r)' % pdf_path)
        extract_text(pdf_path, layout=False)
