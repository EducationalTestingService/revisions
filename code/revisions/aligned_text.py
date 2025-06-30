"""
`AlignedText` aligns the paragraphs and sentences given two text files and
stores the alignments along with sentence offsets.
"""

from massalign.core import (
    MASSAligner,
    TFIDFModel,
    VicinityDrivenParagraphAligner,
    VicinityDrivenSentenceAligner,
)
from revisions.utils import unicode_normalize
import spacy
from textacy import preprocessing
import re
from pathlib import Path

nlp = spacy.load("en_core_web_sm")


def my_imports(module_name):
    # https://stackoverflow.com/questions/11990556/how-to-make-global-imports-from-a-function
    globals()[module_name] = __import__(module_name)


preproc = preprocessing.make_pipeline(
    preprocessing.normalize.quotation_marks,
    preprocessing.normalize.hyphenated_words,
    preprocessing.normalize.whitespace,
    preprocessing.remove.accents,
)


class AlignedText:
    def __init__(
        self,
        file1,
        file2,
        stop_words,
        visualize=False,
        min_par_sim=0.3,
        min_sent_sim=0.4,
        sim_slack=0.05,
        in_app=False,
        timeout=5,
    ):
        """
        Args:
            file1 (str):        Path to text of first draft.
            file2 (str):        Path to text of second draft.
            stop_words (str):   Path to text file with one stop word on each line.
            min_par_sim (float):    Min similarity score between two paragraphs for alignment.
            min_sent_sim (float):   Min similarity score between two sentences for alignment.
            sim_slack (float):      Max amount of similarity that can be lost.
                after each step of incrementing N when finding for a 1-N or N-1 alignment.
            in_app (bool):  Whether alignment is being done as part of the web app.
            timeout (int):  Timeout for toksent sentence tokenization in seconds.
        """
        self.file1 = file1
        self.file2 = file2

        # When there are only single paragraphs, this causes a bug in the
        # TF-IDF calculation. Solve this by appending a newline to file1.
        # This step must be done before the TF-IDF calculation.
        with open(self.file1, "a") as f:
            f.write("\n")

        self.m = MASSAligner()
        self.in_app = in_app
        self.used_nltk = False

        self.timeout = timeout
        # self.init_tokenization_funcs()

        self.content1, self.p1s, self.sentence_offsets1 = self.read_paragraphs(file1)
        self.content2, self.p2s, self.sentence_offsets2 = self.read_paragraphs(file2)

        self.global_offsets1 = self.get_sentence_offsets(file_num=1)
        self.global_offsets2 = self.get_sentence_offsets(file_num=2)

        self.tfidf = TFIDFModel([file1, file2], stop_words)
        self.visualize = visualize

        par_alignment, aligned_pars = self.align_pars(min_par_sim)
        self.par_alignment = par_alignment
        self.sent_alignments = self.align_sents(aligned_pars, min_sent_sim, sim_slack)

    def get_sentence_offsets(self, file_num):
        """
        Args:
            file_num (int): Either 1 or 2 to represent either
                file1 or file2.
        """
        if file_num == 1:
            paragraphs = self.content1.split("\n")
            sentence_offsets = self.sentence_offsets1
        elif file_num == 2:
            paragraphs = self.content2.split("\n")
            sentence_offsets = self.sentence_offsets2

        offsets = []
        curr_offset = 0
        for i, paragraph in enumerate(paragraphs):
            if i in sentence_offsets:
                offset_list = sentence_offsets[i]

                for begin, end in offset_list:
                    offsets.append((begin + curr_offset, end + curr_offset))

                curr_offset += offset_list[-1][1] + 1  # Count the newline

                if paragraph:
                    if paragraph.endswith(" "):
                        # Count the trailing spaces
                        curr_offset += len(paragraph) - len(paragraph.strip())
            else:
                offsets.append((-1, -1))  # Empty paragraph
                curr_offset += 1
        return offsets

    def sentence_tokenize(self, content: str):
        orig_paragraphs = content.split("\n")
        offsets = dict()
        paragraphs = []
        for i, paragraph in enumerate(orig_paragraphs):
            if paragraph.strip():
                parsed = nlp(paragraph)
                sent_tuples = list()

                for s in parsed.sents:
                    normalized_sentence = unicode_normalize(s.text)
                    start_index = parsed[s.start].idx
                    end_index = parsed[s.end - 1].idx + len(parsed[s.end - 1].text)

                    sent_tuples.append((normalized_sentence, (start_index, end_index)))

                sentences, offset_list = zip(*sent_tuples)
                offsets[i] = offset_list
                paragraphs.append(sentences)
            else:
                paragraphs.append([paragraph])
        return content, paragraphs, offsets

    def read_paragraphs(self, file_path):
        """
        Args:
            file_path (str): The path to the text file within which
                the revision text is contained.
        """
        with open(file_path) as infile:
            content = unicode_normalize(infile.read())
            content = preproc(content)
            content = content.strip()

            if Path(file_path).name.startswith("np"):
                pattern = r"(?<=\d)\.(?=[A-Z])"
                content = re.sub(pattern, ". ", content)
                content = content.replace('."', '. "')
                sents = [sent.text for sent in nlp(content).sents]
                content = "\n".join(sents)

        result = self.sentence_tokenize(content)
        return result

    def align_pars(self, min_par_sim):
        """
        Args:
            min_par_sim (float): Min similarity score between two paragraphs for alignment.
        """
        paragraph_aligner = VicinityDrivenParagraphAligner(
            similarity_model=self.tfidf, acceptable_similarity=min_par_sim
        )

        par_alignment, aligned_pars = self.m.getParagraphAlignments(
            self.p1s, self.p2s, paragraph_aligner
        )

        if self.visualize:
            self.m.visualizeParagraphAlignments(self.p1s, self.p2s, par_alignment)
        return par_alignment, aligned_pars

    def align_sents(self, aligned_pars, min_sent_sim, sim_slack):
        """
        Args:
            aligned_pars (list): Aligned paragraphs from the MASSAlign paragraph aligner.
            min_sent_sim (float): Min similarity score between two sentences for alignment.
            sim_slack (float):  Max amount of similarity that can be lost.
                after each step of incrementing N when finding for a 1-N or N-1 alignment.
        """
        sentence_aligner = VicinityDrivenSentenceAligner(
            similarity_model=self.tfidf,
            acceptable_similarity=min_sent_sim,
            similarity_slack=sim_slack,
        )

        all_sent_alignments = []
        for a in aligned_pars:
            p1 = a[0]
            p2 = a[1]
            sent_alignment, aligned_sentences = self.m.getSentenceAlignments(
                p1, p2, sentence_aligner
            )
            # FIXME: When there is a title in the text, the alignment can be buggy at times
            # The line below can be used to force title alignment
            # sent_alignment = [([0], [0])]

            all_sent_alignments.append(sent_alignment)
            if self.visualize:
                self.m.visualizeSentenceAlignments(p1, p2, sent_alignment)
        return all_sent_alignments
