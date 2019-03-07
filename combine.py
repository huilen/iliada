#!/usr/bin/python

import sys
import re
import uuid
import jinja2

from enum import Enum


class Note:

    def __init__(self, verse, passage, body, tags=None):
        self.verse = verse
        self.passage = passage
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


class Verse:

    def __init__(self, original, translated, number):
        self.original = original
        self.translated = translated
        self.number = number


class Tag(Enum):

    TRANSLATION = 'translation'
    TEXT = 'text'

    def __str__(self):
        return self.value


def insert_str(string, str_to_insert, index):
    return string[:index] + str_to_insert + string[index:]


def combine(text, notes):
    notes_counter = 0

    for verse in text:
        associated_notes = Note.get_notes_for_verse(notes, verse.number)
        for associated_note in associated_notes:
            reg = re.compile(re.escape(associated_note.passage).replace('…', '(.+)'), re.IGNORECASE)
            match = re.search(reg, verse.translated)
            if match == None:
                print("Error procesando verso " + str(verse.number) + "  " + associated_note.passage, file=sys.stderr)
                continue
            span = match.span()
            notes_counter += 1
            delta = len(verse.translated)
            verse.translated = insert_str(
                verse.translated,
                '</span><a href="#{i}" class="note_number" tags="{t}" onclick="show_note(\'{i}\');">{c}</a>'.format(
                    i=associated_note.identificator, c=notes_counter,
                    t=associated_note.get_tags()), span[1])
            verse.translated = insert_str(
                verse.translated,
                '<span id="passage_{i}" class="passage">'.format(
                    i=associated_note.identificator), span[0])

    file_loader = jinja2.FileSystemLoader('.')
    env = jinja2.Environment(loader=file_loader)
    template = env.get_template('template.html')
    with open('texto.html', 'w+', encoding='utf-8') as f:
        f.write(template.render(notes=notes,
                                text=text,
                                tags=[str(t) for t in Tag]))


def get_text(filename):
    text = []
    with open(filename, encoding='utf-8') as f:
        line = f.readline()
        while line:
            line = re.sub('[0-9]+$', '', line)
            line = re.sub('^[0-9]+', '', line)
            text.append(line)
            line = f.readline()
    return text


def get_notes1():
    with open('notas.txt', encoding='utf-8') as f:
        notes_source = f.read()
    matches = re.findall('v. ([0-9]+), (.*?): (.*)', notes_source)
    notes = []
    for match in matches:
        number = int(match[0])
        passage = match[1]
        body = match[2]
        note = Note(number, passage, body, [Tag.TRANSLATION])
        notes.append(note)
    return notes


def get_notes2():
    with open('notas2.txt', encoding='utf-8') as f:
        notes_source = f.read()
    notes_source = notes_source.split('\n')
    notes = []
    for idx, line in enumerate(notes_source):
        match = re.search('Verso ([0-9]+)', line)
        if match:
            number = int(match[1])
            i = idx + 1
            while len(notes_source) > i:
                if notes_source[i] == '':
                    break
                passage, body = notes_source[i].split(': ', 1)
                note = Note(number, passage, body, [Tag.TEXT])
                notes.append(note)
                i += 1
    return notes


if __name__ == '__main__':
    translation = get_text('traduccion.txt')
    greek = get_text('griego.txt')
    text = []
    for i in range(len(translation)):
        text.append(Verse(greek[i], translation[i], i + 1))
    notes = get_notes1()
    notes.extend(get_notes2())
    notes.sort(key=lambda n: n.verse)
    combined_text = combine(text, notes)
