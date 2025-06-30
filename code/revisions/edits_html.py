"""
`EditsHtml` identifies and formats substitutions, deletions, and insertions.
Stores the contents of the HTML output in `EditsHtml.html1` and `EditsHtml.html2`,
and stores the contents of the JSON output in `EditsHtml.edits_json_dict`.
"""

import os
import uuid
from itertools import chain, zip_longest

from jinja2 import Template
from revisions import diff_wordMode


class EditsHtml:
    def __init__(self, aligned_text, templates_dir):
        self.templates_dir = templates_dir
        self.content1 = aligned_text.content1
        self.content2 = aligned_text.content2

        self.p1s = aligned_text.p1s
        self.p2s = aligned_text.p2s

        self.text1 = list(chain.from_iterable(self.p1s))
        self.text2 = list(chain.from_iterable(self.p2s))

        self.sentence_offsets1 = aligned_text.global_offsets1
        self.sentence_offsets2 = aligned_text.global_offsets2
        self.html1 = [""] * len(self.p1s)  # List of HTML formatted paragraphs
        self.html2 = [""] * len(self.p2s)  # List of HTML formatted paragraphs

        self.num_edits = 0
        dummy_dict = {"text": "", "offset": (-1, -1)}
        self.edits_json_dict = {
            "file1_sentences": [dummy_dict] * len(self.text1),
            "file2_sentences": [dummy_dict] * len(self.text2),
            "alignments": dict(),
        }
        self.get_diff_html(aligned_text.par_alignment, aligned_text.sent_alignments)

    def render_template(self, template_name, **kwargs):
        with open(os.path.join(self.templates_dir, template_name)) as f:
            template = Template(f.read())
        html_text = template.render(kwargs)
        return html_text

    def get_html_text(self, header1="", header2=""):
        html1_list = [s for s in self.html1 if s.strip()]
        html2_list = [s for s in self.html2 if s.strip()]

        if not html1_list:
            html1_list = ["Empty"]
        if not html2_list:
            html2_list = ["Empty"]

        return self.render_template(
            "base.html",
            html1_list=html1_list,
            html2_list=html2_list,
            header1=header1,
            header2=header2,
        )

    def format_edit(self, text, edit_type):
        return self.render_template("{}.html".format(edit_type), text=text)

    def format_hover(self, text, index):
        return self.render_template("hover.html", index=index, text=text)

    def handle_diff(self, diff, char_diff, offsets1, offsets2, s1_indices, s2_indices):
        """
        Args:
            diff (list): Diff-match-patch output
        """
        html1 = []
        html2 = []
        edit_dicts = []

        num_tokens_list = [len(list(s)) for s in list(zip(*char_diff))[1]]
        i = 0
        last_index = len(diff) - 1

        def deque(offset_list, diff_string, num_tokens):
            diff_offsets = offset_list[:num_tokens]
            if not diff_offsets:
                edit_offset = (-1, -1)
            else:
                begin = diff_offsets[0][0]
                end = diff_offsets[-1][-1]

                # Important: double quotes can change the number of
                # characters in a sentence.
                num_double_quotes = diff_string.count("''")
                num_double_quotes += diff_string.count("``")
                # Subtract 1 from the end for every double quote found
                end -= num_double_quotes
                edit_offset = (begin, end)

            return edit_offset, offset_list[num_tokens:]

        while i <= last_index:
            diff_type, diff_string = diff[i]

            diff_string = diff_string.strip()
            num_tokens = num_tokens_list[i]

            is_substitution = False
            if diff_type == -1:
                is_substitution = (i < last_index) and (diff[i + 1][0] == 1)
                if is_substitution:
                    edit_type = "substitution"
                    subbed_string = diff[i + 1][1].strip()

                    if len(diff_string) > 1:
                        html1.append(self.format_edit(diff_string, edit_type))
                        html2.append(self.format_edit(subbed_string, edit_type))

                    edit_offset1, offsets1 = deque(offsets1, diff_string, num_tokens)
                    edit_offset2, offsets2 = deque(
                        offsets2, diff_string, num_tokens_list[i + 1]
                    )
                    self.num_edits += 1
                else:  # Deletion
                    edit_type = "deletion"

                    if len(diff_string) > 1:
                        html1.append(self.format_edit(diff_string, edit_type))

                    edit_offset1, offsets1 = deque(offsets1, diff_string, num_tokens)
                    edit_offset2 = (-1, -1)
                    self.num_edits += 1
            elif diff_type == 1:  # Insertion
                edit_type = "insertion"

                if len(diff_string) > 1:
                    html2.append(self.format_edit(diff_string, edit_type))

                edit_offset2, offsets2 = deque(offsets2, diff_string, num_tokens)
                edit_offset1 = (-1, -1)
                self.num_edits += 1
            elif diff_type == 0:
                edit_type = "same"
                html1.append(diff_string)
                html2.append(diff_string)

                edit_offset1, offsets1 = deque(offsets1, diff_string, num_tokens)
                edit_offset2, offsets2 = deque(offsets2, diff_string, num_tokens)

            begin1, end1 = edit_offset1
            begin2, end2 = edit_offset2
            text1 = self.content1[begin1:end1] if begin1 >= 0 else ""
            text2 = self.content2[begin2:end2] if begin2 >= 0 else ""

            edit_dicts.append(
                {
                    "edit_type": edit_type,
                    "offset1": edit_offset1,
                    "offset2": edit_offset2,
                    "text1": text1,
                    "text2": text2,
                }
            )

            if is_substitution:
                i += 2
            else:
                i += 1

        return " ".join(html1), " ".join(html2), edit_dicts

    def locate_paragraph(self, paragraph_list, sentence_index, paragraphs):
        """
        Given a sentence index, determine which paragraph it belongs to.
        Args:
            paragraph_list (int list)
            sentence_index (int)
            paragraphs (str list)
        """
        begin = -1
        end = -1

        for i, par_index in enumerate(paragraph_list):
            p = paragraphs[par_index]
            if i == 0:
                begin = 0
                end = len(p) - 1  # Last index
            else:
                begin = end + 1
                end = begin + len(p) - 1

            if sentence_index >= begin and sentence_index <= end:
                sent_index_in_par = sentence_index - begin
                sent = paragraphs[par_index][sent_index_in_par]
                return par_index, sent
        raise IndexError("Sentence index {} out of range".format(sentence_index))

    def checkConsecutive(self, l):
        return sorted(l) == list(range(min(l), max(l) + 1))

    def get_sentence(
        self,
        par_index,
        paragraph_list,
        sentence_list,
        paragraphs,
        paragraph_html,
        global_offsets,
        edits_json_key,
        content,
    ):
        """
        Args:
            par_index (int):    Original paragraph index.
            paragraph_list (int list)
            sentence_list (int list)
            paragraphs (str list)
            paragraph_html (str list)
        """
        sentence_list = [j for j in sentence_list if j not in paragraph_html]

        if not sentence_list:
            return (None,) * 5

        if not self.checkConsecutive(sentence_list):
            # Then get the full range
            sentence_list = list(range(min(sentence_list), max(sentence_list) + 1))

        # Holds tuples of (text, paragraph_index, sentence_index)
        sent_indices = self.get_sent_indices(par_index, paragraphs, sentence_list)

        par_indices = set()
        sentence_dicts = []
        sentence_parts = []
        for i, sent_index in enumerate(sentence_list):
            try:
                sent = paragraphs[par_index][sent_index]
            except IndexError:
                par_index, sent = self.locate_paragraph(
                    paragraph_list, sent_index, paragraphs
                )

            sent_index = sent_indices[i]  # Global sentence index
            offset = global_offsets[sent_index]
            sent = content[offset[0] : offset[1]]
            sentence_dict = {
                "text": sent,
                "paragraph_index": par_index,
                "sentence_index": sent_index,
                "offset": offset,
            }

            self.edits_json_dict[edits_json_key][sent_index] = sentence_dict
            sentence_dicts.append(sentence_dict)
            sentence_parts.append(sent)
            par_indices.add(par_index)

        sentence = " ".join(sentence_parts)
        return (sentence, sentence_list, par_indices, sent_indices, sentence_dicts)

    def add_unaligned_sentences(
        self,
        edit_type,
        paragraph_html,
        paragraphs,
        par_index,
        edits_json_key,
        global_offsets,
    ):
        """
        Modify the `paragraph_html` dictionary in place.
        """
        sentence_dicts = []
        paragraph = paragraphs[par_index]
        sent_indices = self.get_sent_indices(
            par_index, paragraphs, range(len(paragraph))
        )
        for i, sentence in enumerate(paragraph):

            if i not in paragraph_html:
                paragraph_html[i] = self.format_edit(sentence, edit_type)
                self.num_edits += 1

                sent_index = sent_indices[i]
                if edit_type == "deletion":
                    self.edits_json_dict["alignments"][sent_index] = {
                        "match": [],
                        "edits": [],
                    }

                if edit_type == "insertion":
                    if -1 not in self.edits_json_dict["alignments"]:
                        self.edits_json_dict["alignments"][-1] = {
                            "match": [],
                            "edits": [],
                        }
                    self.edits_json_dict["alignments"][-1]["match"].append(sent_index)

                self.edits_json_dict[edits_json_key][sent_index] = {
                    "text": sentence,
                    "paragraph_index": par_index,
                    "sentence_index": sent_index,
                    "offset": global_offsets[sent_index],
                }
        return sentence_dicts

    def add_unaligned_paragraphs(self, edit_type, seen_pars, text_html, paragraphs):
        """
        Modify the `text_html` dictionary in place.
        """
        for paragraph_index, paragraph_sentence_list in enumerate(paragraphs):
            par_text = " ".join(paragraph_sentence_list)
            is_unaligned = (paragraph_index not in seen_pars) and (
                not text_html[paragraph_index]
            )
            if is_unaligned:

                # Indices of sentences within this paragraph
                local_sentence_indices = list(range(len(paragraph_sentence_list)))
                global_sent_indices = self.get_sent_indices(
                    par_index=paragraph_index,
                    paragraphs=paragraphs,
                    sentence_list=local_sentence_indices,
                )

                assert edit_type in ("deletion", "insertion")

                for local_sent_index in local_sentence_indices:
                    global_sent_index = global_sent_indices[local_sent_index]

                    if edit_type == "deletion":
                        offset_list = self.sentence_offsets1
                        file_num = 1
                        s1_index = global_sent_index
                        s2_indices = [-1]
                    else:
                        offset_list = self.sentence_offsets2
                        file_num = 2
                        s1_index = -1
                        s2_indices = [global_sent_index]

                    sentence_text = paragraph_sentence_list[local_sent_index]
                    self.edits_json_dict[f"file{file_num}_sentences"][
                        global_sent_index
                    ] = {
                        "text": sentence_text,
                        "paragraph_index": paragraph_index,
                        "sentence_index": global_sent_index,
                        "offset": offset_list[global_sent_index],
                    }

                    self.edits_json_dict["alignments"][s1_index] = {
                        "match": s2_indices,
                        "edits": [
                            {
                                "edit_type": edit_type,
                                "offset1": (
                                    [-1, -1]
                                    if edit_type == "insertion"
                                    else offset_list[global_sent_index]
                                ),
                                "offset2": (
                                    [-1, -1]
                                    if edit_type == "deletion"
                                    else offset_list[global_sent_index]
                                ),
                                "text1": (
                                    "" if edit_type == "insertion" else sentence_text
                                ),
                                "text2": (
                                    "" if edit_type == "deletion" else sentence_text
                                ),
                            }
                        ],
                    }

                paragraph_html = self.format_edit(par_text, edit_type)

                text_html[paragraph_index] = paragraph_html
                self.num_edits += 1

    def add_aligned_paragraph(self, paragraph_dict, found_indices, full_html):
        paragraph_html = " ".join(
            [paragraph_dict[k] for k in sorted(paragraph_dict.keys())]
        )
        if found_indices is not None:
            html_index = min(found_indices)
            if html_index not in full_html:
                full_html[html_index] = paragraph_html

    def get_sent_indices(self, par_index, paragraphs, sentence_list):
        """
        Convert local indices (within paragraph) to global indices.
        Args:
            par_index (int)
            sentence_list (list of ints): The indices of the sentences
                within the paragraph.
        """
        sentence_offset = 0
        i = 0

        while i < par_index:
            if paragraphs[i][0]:
                sentence_offset += len(paragraphs[i])
            else:
                sentence_offset += 1
            i += 1
        return [j + sentence_offset for j in sentence_list]

    def get_token_offsets(self, token_offsets, sent_offset, par_index):
        """
        Convert local offsets (within sentence) to global offsets.
        """
        # If not first paragraph, add one to count newline
        return [
            (begin + sent_offset, end + sent_offset) for (begin, end) in token_offsets
        ]

    def get_diff_html(self, par_alignment, sent_alignments):
        """
        Creates the HTML formatted diff for Draft 1 and Draft 2.
        """
        seen_p1s = set()
        seen_p2s = set()

        for i, (p1_list, p2_list) in enumerate(par_alignment):
            # For each aligned paragraph
            for p1_index, p2_index in zip_longest(p1_list, p2_list):
                if (p1_index is None) or (p2_index is None):
                    continue

                orig_p1_index = p1_index
                orig_p2_index = p2_index

                aligned_par_id = uuid.uuid4()

                par1_html = dict()
                par2_html = dict()

                found_p1_indices = None
                found_p2_indices = None

                seen_p1s.update(p1_list)
                seen_p2s.update(p2_list)

                for aligned_sent_id, el in enumerate(sent_alignments[i]):
                    if not el:
                        continue
                    aligned_sent_id = "{}-{}".format(aligned_par_id, aligned_sent_id)
                    s1_list, s2_list = el

                    s1, s1_list, found_p1_indices, s1_indices, s1_dicts = (
                        self.get_sentence(
                            orig_p1_index,
                            p1_list,
                            s1_list,
                            self.p1s,
                            par1_html,
                            self.sentence_offsets1,
                            "file1_sentences",
                            self.content1,
                        )
                    )

                    s2, s2_list, found_p2_indices, s2_indices, s2_dicts = (
                        self.get_sentence(
                            orig_p2_index,
                            p2_list,
                            s2_list,
                            self.p2s,
                            par2_html,
                            self.sentence_offsets2,
                            "file2_sentences",
                            self.content2,
                        )
                    )

                    if (s1 is None) or (s2 is None):
                        continue

                    diff, char_diff, (offsets1, offsets2) = diff_wordMode(s1, s2)

                    token_offsets1 = self.get_token_offsets(
                        offsets1, s1_dicts[0]["offset"][0], orig_p1_index
                    )
                    token_offsets2 = self.get_token_offsets(
                        offsets2, s2_dicts[0]["offset"][0], orig_p2_index
                    )

                    s1_html, s2_html, edit_dicts = self.handle_diff(
                        diff,
                        char_diff,
                        token_offsets1,
                        token_offsets2,
                        s1_indices,
                        s2_indices,
                    )

                    par1_html[s1_list[0]] = self.format_hover(s1_html, aligned_sent_id)
                    par2_html[s2_list[0]] = self.format_hover(s2_html, aligned_sent_id)

                    # Add sentence indices that we've accounted for to paragraph dict
                    for j in s1_list[1:]:
                        par1_html[j] = ""  # Placeholder
                    for j in s2_list[1:]:
                        par2_html[j] = ""  # Placeholder

                    # Now add the alignments
                    for s1_index in s1_indices:
                        self.edits_json_dict["alignments"][int(s1_index)] = {
                            "match": s2_indices,
                            "edits": edit_dicts,
                        }

                if found_p1_indices is not None and orig_p1_index in found_p1_indices:
                    self.add_unaligned_sentences(
                        "deletion",
                        par1_html,
                        self.p1s,
                        orig_p1_index,
                        "file1_sentences",
                        self.sentence_offsets1,
                    )

                if found_p2_indices is not None and orig_p2_index in found_p2_indices:
                    self.add_unaligned_sentences(
                        "insertion",
                        par2_html,
                        self.p2s,
                        orig_p2_index,
                        "file2_sentences",
                        self.sentence_offsets2,
                    )

                self.add_aligned_paragraph(par1_html, found_p1_indices, self.html1)
                self.add_aligned_paragraph(par2_html, found_p2_indices, self.html2)

        self.add_unaligned_paragraphs("deletion", seen_p1s, self.html1, self.p1s)
        self.add_unaligned_paragraphs("insertion", seen_p2s, self.html2, self.p2s)
