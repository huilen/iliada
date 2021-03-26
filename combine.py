#!/usr/bin/python

import sys
import re
import uuid
import jinja2

from bs4 import BeautifulSoup
from enum import Enum
from markdown import markdown


TAGS = {
    'INTR': 'Notas introductorias a personajes y conceptos clave del mundo homérico.',
    'AVAN': 'Notas con información avanzada sobre el texto y aproximaciones básicas de análisis, dirigidas a lectores familiarizados con la cultura griega antigua interesados en su análisis literario.',
    'TECN': 'Notas sobre problemas específicos del texto en las diferentes categorías, dirigidas a especialistas que quieren aproximarse al poema desde una perspectiva filológica.',
    'CONC': 'Notas sobre conceptos y términos fundamentales en los poemas homéricos.',
    'TEXT': 'Comentarios de crítica textual.',
    'TRAD': 'Comentarios de traducción.',
    'NARR': 'Notas sobre el contenido narrativo.',
    'FORM': 'Notas sobre estilo oral y lenguaje formulaico.',
    'GRAM': 'Notas sobre gramática homérica y discusión de problemas gramaticales específicos.',
    'HIST': 'Notas sobre historia y arqueología.',
    'ESTR': 'Notas sobre estructura de discursos, episodios y el poema.',
    'MITO': 'Notas sobre mitología y religión griegas.',
    'INTP': 'Notas sobre problemas de interpretación del texto o la narración.'
}


class Note:

    def __init__(self, canto, verse, passage, body, number, kind, tags=None):
        self.canto = canto
        self.verse = verse
        self.passage = passage
        self.number = number
        self.body = body
        self.kind = kind
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

    def format_body_with_references(self):
        # TODO: fix to match multiple notes
        # VER [indicio de referencia] ad [Nota al español] / Com. [Nota al griego] 1[canto].1[verso], [para marcar que viene otra, si viene] 2 y [para marcar la última referencia de una secuencia].
        regex = re.compile('VER (<em>ad</em>|Com\.) ([0-9]+)\.([0-9]+)')
        matches = re.findall(regex, self.body)
        body = self.body
        for match in matches:
            kind = match[0]
            label = 'VER ' + kind + ' ' + match[1] + '.' + match[2]
            if 'Com.' != kind:
                kind = 'ad'
            reference = kind[0] + match[1] + '.' + match[2]
            body = body.replace(label, '<a href="#' + reference + '">' + label + '</a>')
        return body


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
        for verse in text.split('\n')[1:]:
            # remove blank spaces
            verse = verse.strip()

            # remove verse numbers if exist
            verse = re.sub('[0-9]+$', '', verse)
            verse = re.sub('^[0-9]+', '', verse)

            if verse == '':
                continue

            verse = markdown(verse).replace('<p>', '').replace('</p>', '')

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


def get_reference_anchor(note):
    if note.kind == 'greek':
        identificator = 'C'
    elif note.kind == 'text':
        identificator = 'a'
    return identificator + str(note.canto) + '.' + str(note.verse)


def generate_document(translation, greek, notes, canto):
    file_loader = jinja2.FileSystemLoader('.')
    env = jinja2.Environment(loader=file_loader)
    template = env.get_template('template.html')
    text = zip(translation.verses, greek.verses)
    name = 'canto' + canto + '.html'
    with open(name, 'w+', encoding='utf-8') as f:
        f.write(template.render(notes=notes,
                                text=text,
                                get_reference_anchor=get_reference_anchor,
                                get_tag_desc=get_tag_description,
                                canto=canto,
                                tags=[str(t) for t in TAGS if t not in ['INTR',
                                                                        'AVAN',
                                                                        'TECN']]))
    print("Archivo generado: " + name)


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
            raise Exception("Tag invalid " + tag)
    return tags, passage


def get_notes_greek(canto):
    notes_source = parse_txt('sources/' + canto + '/comentario.md')
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
        note = Note(1, number, passage, body, count, 'greek', tags)
        notes.append(note)
        count += 1
    return notes


def get_notes_text(canto):
    notes_source = parse_txt('sources/' + canto + '/notas.md').split('\n')
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
                note = Note(1, number, passage, body, count, 'text', tags)
                notes.append(note)
                count += 1
                i += 1
    return notes


def parse_txt(filename):
    with open(filename, encoding='utf-8') as f:
        return f.read()


def get_tag_description(name):
    return TAGS[name]


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Falta indicar número de canto")
        exit(1)

    canto = sys.argv[1]

    print("Procesando canto " + canto)

    translation_text = parse_txt('sources/' + canto + '/traduccion.md')
    translation = Text(translation_text)

    greek_text = parse_txt('sources/' + canto + '/griego.md')
    greek = Text(greek_text)

    notes_greek = get_notes_greek(canto)
    notes_text = get_notes_text(canto)

    greek.add_passages_for_notes(notes_greek)
    translation.add_passages_for_notes(notes_text)

    notes = notes_greek + notes_text
    notes.sort(key=lambda n: n.verse)

    generate_document(translation, greek, notes, canto)
