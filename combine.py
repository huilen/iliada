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

    def __init__(self, span, note):
        self.span = span
        self.note = note


class Verse:

    def __init__(self, number, body, marks):
        self.number = number
        self.body = body
        self.passages = []
        self.marks = marks

    def format_with_passages(self):
        verse = self.body
        orig_length = len(verse)
        replacements = {}
        for passage in sorted(self.passages, key=lambda p: -p.span[1]):
            verse = insert_str(verse, '<a href="#{i}" class="note_number" tags="{t}" onclick="show_note(\'{i}\');">{c}</a>'.format(
                i=passage.note.identificator, c=passage.note.number,
                t=passage.note.get_tags()), passage.span[1])
        for mark in self.marks:
            if mark not in verse:
                print("Error colocando cursivas en verso " + verse.number)
            verse = verse.replace(mark, '<i>{m}</i>'.format(m=mark), 1)
        return verse


class Text:

    def __init__(self, text, marked_parts):
        self.verses = []
        number = 1
        for verse, marks in zip(text, marked_parts):
            # remove verse numbers if exist
            verse = re.sub('[0-9]+$', '', verse)
            verse = re.sub('^[0-9]+', '', verse)

            # remove blank spaces
            verse = verse.strip()

            if verse == '':
                continue

            self.verses.append(Verse(number, verse, marks))

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
                match = re.search(regexp, verse.body)
                if match == None:
                    print("Error procesando nota en verso {n} {v} -> {p}"
                          .format(n=verse.number, v=verse.body,
                                  p=note.passage), file=sys.stderr)
                    continue
                verse.passages.append(Passage(match.span(), note))


class Tag(Enum):

    TRANSLATION = 'translation'
    TEXT = 'text'

    def __str__(self):
        return self.value


def insert_str(string, str_to_insert, index):
    return string[:index] + str_to_insert + string[index:]


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
    with open('notas.txt', encoding='utf-8') as f:
        notes_source = f.read()
    matches = re.findall('v. ([0-9]+), (.*?): (.*)', notes_source)
    notes = []
    count = 1
    for match in matches:
        number = int(match[0])
        passage = match[1]
        body = match[2]
        note = Note(number, passage, body, count, [Tag.TRANSLATION])
        notes.append(note)
        count += 1
    return notes


def get_notes2():
    with open('notas2.txt', encoding='utf-8') as f:
        notes_source = f.read()
    notes_source = notes_source.split('\n')
    notes = []
    count = 1
    for idx, line in enumerate(notes_source):
        match = re.search('Verso ([0-9]+)', line)
        if match:
            number = int(match[1])
            i = idx + 1
            while len(notes_source) > i:
                if notes_source[i] == '':
                    break
                passage, body = notes_source[i].split(': ', 1)
                note = Note(number, passage, body, count, [Tag.TEXT])
                notes.append(note)
                count += 1
                i += 1
    return notes


def parse_html(filename):
    with open(filename) as f:
        soup = BeautifulSoup(f.read(), features='html.parser')

    lines = []
    marked_parts = []

    for tag_p in soup.find_all('p'):
        line = tag_p.get_text()
        line = line.replace(u'\xa0', u' ')
        matches = tag_p.find('span', {'class': 'c0'})
        matches = [m.replace(u'\xa0', u' ') for m in matches] if matches else []
        for match in matches:
            if match == ' ':
                matches.remove(match)
        lines.append(line)
        marked_parts.append(matches)

    return lines, marked_parts


def parse_txt(filename):
    lines = []
    marked_parts = []
    with open(filename) as f:
        line = f.readline()
        while line:
            lines.append(line)
            marked_parts.append([])
            line = f.readline()
    return lines, marked_parts


if __name__ == '__main__':
    translation_text, translation_marked_parts = parse_html('traduccion.html')
    translation = Text(translation_text, translation_marked_parts)

    greek_text, greek_marked_parts = parse_txt('griego.txt')
    greek = Text(greek_text, greek_marked_parts)

    notes1 = get_notes1()
    notes2 = get_notes2()

    greek.add_passages_for_notes(notes1)
    translation.add_passages_for_notes(notes2)

    notes = notes1 + notes2
    notes.sort(key=lambda n: n.verse)

    generate_document(translation, greek, notes)
