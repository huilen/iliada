#!/usr/bin/python

import sys
import re
import uuid
import jinja2

from bs4 import BeautifulSoup
from enum import Enum


class Note:

    def __init__(self, verse, passage, body, number, tags=None):
        self.verse = verse
        self.passage = passage
        self.number = number
        self.body = body
        self.tags = []
        self.identificator = str(verse) + str(uuid.uuid4())

        if tags != None:
            self.tags.extend(tags)

    def get_tags(self):
        return ' '.join([str(t) for t in self.tags])

    def get_notes_for_verse(notes, verse):
        matches = []
        for note in notes:
            if note.verse == verse:
                matches.append(note)
        return matches


class Passage:

    def __init__(self, text, note):
        self.text = text
        self.note = note


class Verse:

    def __init__(self, number, body):
        self.number = number
        self.body = body
        self.passages = []

    def format_with_passages(self):
        verse = self.body
        orig_length = len(verse)
        replacements = {}
        for passage in self.passages:
            verse = verse.replace(passage.text,
                                  '<a href="#{i}" tags="{t}" onclick="show_note(\'{i}\');">{p}</a>'.format(
                                      i=passage.note.identificator,
                                      p=passage.text,
                                      t=passage.note.get_tags()))
        return verse


class Text:

    def __init__(self, text):
        self.verses = []
        number = 1
        for verse in text.split('\n'):
            # remove verse numbers if exist
            verse = re.sub('[0-9]+$', '', verse)
            verse = re.sub('^[0-9]+', '', verse)

            # remove blank spaces
            verse = verse.strip()

            if verse == '':
                continue

            self.verses.append(Verse(number, verse))

            number += 1

    def add_passages_for_notes(self, all_notes):
        for verse in self.verses:
            notes = Note.get_notes_for_verse(all_notes, verse.number)
            for note in notes:
                regexp = note.passage
                regexp = regexp.replace('...', '…')
                regexp = re.escape(regexp)
                regexp = regexp.replace('…', '(.*)')
                regexp = re.compile(regexp, re.IGNORECASE)
                reg = re.compile(r'<.*?>')
                body = reg.sub('', verse.body)
                match = re.search(regexp, body)
                if match == None:
                    print("Error procesando nota en verso {n} {v} -> {p}"
                          .format(n=verse.number, v=body,
                                  p=note.passage), file=sys.stderr)
                    continue
                verse.passages.append(Passage(match.group(0), note))


class Tag(Enum):

    TRANSLATION = 'translation'
    TEXT = 'text'

    def __str__(self):
        return self.value


def generate_document(translation, greek, notes):
    file_loader = jinja2.FileSystemLoader('.')
    env = jinja2.Environment(loader=file_loader)
    template = env.get_template('template.html')
    text = zip(translation.verses, greek.verses)
    with open('texto.html', 'w+', encoding='utf-8') as f:
        f.write(template.render(notes=notes,
                                text=text,
                                tags=[str(t) for t in Tag]))


def get_notes1():
    notes_source = parse_html('notas.html')
    matches = re.findall('v. ([0-9]+), (.*?): (.*)', notes_source)
    notes = []
    count = 1
    for match in matches:
        number = int(match[0])
        passage = match[1]
        reg = re.compile(r'<.*?>')
        passage = reg.sub('', passage)
        body = match[2]
        note = Note(number, passage, body, count, [Tag.TRANSLATION])
        notes.append(note)
        count += 1
    return notes


def get_notes2():
    notes_source = parse_html('notas2.html').split('\n')
    notes = []
    count = 1
    for idx, line in enumerate(notes_source):
        match = re.search('Verso ([0-9]+)', line)
        if match:
            number = int(match[1])
            i = idx + 1
            while len(notes_source) > i:
                if notes_source[i].startswith('Verso '):
                    break
                passage, body = notes_source[i].split(':', 1)
                reg = re.compile(r'<.*?>')
                passage = reg.sub('', passage)
                note = Note(number, passage, body, count, [Tag.TEXT])
                notes.append(note)
                count += 1
                i += 1
    return notes


def parse_html(filename):
    with open(filename) as f:
        soup = BeautifulSoup(f.read(), features='html.parser')

    lines = []

    for tag_p in soup.find_all('p'):
        line = tag_p.get_text()
        line = line.replace(u'\xa0', u' ')
        if line == '':
            continue
        marks = tag_p.find('span', {'class': 'c0'})
        marks = [m.replace(u'\xa0', u' ') for m in marks] if marks else []
        for mark in marks:
            line = line.replace(mark, '<i>{m}</i>'.format(m=mark))
        lines.append(line)

    return '\n'.join(lines)


def parse_txt(filename):
    with open(filename) as f:
        return f.read()


if __name__ == '__main__':
    translation_text = parse_html('traduccion.html')
    translation = Text(translation_text)

    greek_text = parse_txt('griego.txt')
    greek = Text(greek_text)

    notes1 = get_notes1()
    notes2 = get_notes2()

    greek.add_passages_for_notes(notes1)
    translation.add_passages_for_notes(notes2)

    notes = notes1 + notes2
    notes.sort(key=lambda n: n.verse)

    generate_document(translation, greek, notes)
