#!/usr/bin/python

import sys
import re
import uuid
import jinja2

from bs4 import BeautifulSoup
from enum import Enum
from markdown import markdown


TAGS = []


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


def generate_document(translation, greek, notes):
    file_loader = jinja2.FileSystemLoader('.')
    env = jinja2.Environment(loader=file_loader)
    template = env.get_template('template.html')
    text = zip(translation.verses, greek.verses)
    with open('output.html', 'w+', encoding='utf-8') as f:
        f.write(template.render(notes=notes,
                                text=text,
                                tags=[str(t) for t in TAGS]))
    print("Archivo generado: output.html")


def extract_tags(text):
    matches = re.findall('(.*?) (\\\\?\[\\\\?\[(.*)\\\\?\]\\\\?\]+)', text)
    if not matches:
        return [], text
    passage = matches[0][0] 
    tags = matches[0][1]
    tags = re.findall('(\\\\?\[\\\\?\[(.*?)\\\\?\]\\\\?\]+)', tags)
    tags = [t[1] for t in tags]
    for tag in tags:
        if tag not in TAGS:
            TAGS.append(tag)
    return tags, passage


def get_notes_greek():
    notes_source = parse_txt('sources/comentario.md')
    matches = re.findall('v. ([0-9]+), (.*?): (.*)', notes_source)
    notes = []
    count = 1
    for match in matches:
        number = int(match[0])
        passage = match[1].replace('*', '')
        reg = re.compile(r'<.*?>')
        passage = reg.sub('', passage)
        body = match[2]
        tags, body = extract_tags(body)
        body = markdown(body)
        note = Note(number, passage, body, count, tags)
        notes.append(note)
        count += 1
    return notes


def get_notes_text():
    notes_source = parse_txt('sources/notas.md').split('\n')
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
                if '#Referencia' in notes_source[i]:
                    break
                if not notes_source[i].strip():
                    break
                passage, body = notes_source[i].split(':', 1)
                passage = passage.replace('*', '')
                tags, body = extract_tags(body)
                body = markdown(body)
                note = Note(number, passage, body, count, tags)
                notes.append(note)
                count += 1
                i += 1
    return notes


def parse_html(filename):
    def replace_marks(line, style_class, html_tag):
        marks = tag_p.find_all('span', {'class': style_class})
        marks = [m.text.replace(u'\xa0', u' ') for m in marks] if marks else []
        for mark in marks:
            line = line.replace(mark, '<{t}>{m}</{t}>'.format(
                m=mark, t=html_tag), 1)
        return line

    with open(filename, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), features='html.parser')

    cursive_class = soup.find(text='#Referencia cursiva')
    if cursive_class:
        cursive_class = ' '.join(cursive_class.parent.attrs['class'])
    bold_class = soup.find(text='#Referencia negrita')
    if bold_class:
        bold_class = ' '.join(bold_class.parent.attrs['class'])

    lines = []

    for tag_p in soup.find_all('p'):
        line = tag_p.get_text()
        line = line.replace(u'\xa0', u' ')
        if line == '':
            continue

        if bold_class:
            line = replace_marks(line, bold_class, 'strong')
        if cursive_class:
            line = replace_marks(line, cursive_class, 'i')
        lines.append(line)

    return '\n'.join(lines)


def parse_txt(filename):
    with open(filename, encoding='utf-8') as f:
        return f.read()


if __name__ == '__main__':
    translation_text = parse_html('sources/traduccion.html')
    translation = Text(translation_text)

    greek_text = parse_txt('sources/griego.md')
    greek = Text(greek_text)

    notes_greek = get_notes_greek()
    notes_text = get_notes_text()

    greek.add_passages_for_notes(notes_greek)
    translation.add_passages_for_notes(notes_text)

    notes = notes_greek + notes_text
    notes.sort(key=lambda n: n.verse)

    generate_document(translation, greek, notes)
