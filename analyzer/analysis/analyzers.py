import numpy as np
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords as nltk_stopwords

from sklearn.feature_extraction.text import CountVectorizer


class StemmingTokenizer:
    """
    Custom Tokenizer that also performs stemming

    Processing:
      * doc -> words -> lower -> filter punctuation -> stems
    """
    def __init__(self, language, stem=True):
        self.tokenizer = word_tokenize
        self.stemmer = SnowballStemmer(language).stem
        self._stem = stem

    def __call__(self, doc):
        tokenized = [word.lower() for word in
                     self.tokenizer(doc) if word.isalpha()]
        stemmed = []
        # Perform 2 stemming passes for words like
        # `somewhere` (`somewher`, `somewh`)
        for word in tokenized:
            stem_1 = self.stemmer(word)
            stem_2 = self.stemmer(stem_1)
            stemmed.append(stem_1)
            if stem_1 != stem_2:
                stemmed.append(stem_2)
        return stemmed


class TermFrequencyAnalyzer:
    """
    An analyzer that can find occurences of terms (words / stems)
    within a document.

    Uses vectorization. Supports using stopwords for improving the
    quality of the results.
    """

    def __init__(self, file_content, language, stem=False, stopwords=None):
        """
        :param str file_content: The document's content
        :param str language: The language to use when analyzing the
            document
        :param bool stem: Whether to stem words when analyzing or not.
        :param list stopwords: A list of stopwords. Should be pre-processed
            with `StemmingTokenizer` in the same way you wish to process
            the document (stemming etc).

        :raises ValueError: If required arguments are wrong
        """
        if not file_content:
            raise ValueError(
                "`TermFrequencyAnalyzer` needs a valid `file_content` to work"
            )
        if not language:
            raise ValueError(
                "`TermFrequencyAnalyzer` needs a valid `language` to work"
            )
        self._file_content = file_content
        self._language = language
        self._stopwords = stopwords or nltk_stopwords.words(self._language)
        self._stemming_tokenizer = StemmingTokenizer(self._language, stem=stem)
        self._stem = stem

    def analyze_document(self, sort=False):
        """
        Finds frequent terms (words or stems) within the document.

        :raises IOError: If the file specified cannot be opened
        :rtype dict: A dictionary with the following structure:

            {
                'term_1': {
                    'count': <how many times this term was found>,
                    'sentences': [
                        <first sentence that had this term>,
                        <2nd sentence that had this term>,
                        ...
                    ]
                },
                'term_2': {...}
            }

            The dictionary is sorted by the number of each term's
            occurences (descending)


        """

        sentences = np.array([
            sentence for sentence in sent_tokenize(self._file_content)
        ])

        vectorizer = CountVectorizer(tokenizer=self._stemming_tokenizer,
                                     stop_words=self._stopwords)

        # `fit` will pre-process the data, remove stopwords and non-alphas,
        # shift to lower etc to get better results
        # `transform` creates a 2d (sparse) matrix that maps each term of the
        # vocabulary of the document to the sentences it is contained in.
        # `fit_transform` is supposedly faster than doing the 2 steps
        # individually
        terms_map = vectorizer.fit_transform(sentences)

        # Add all rows (each row represents a term) to gather all terms'
        # number of occurences
        terms_counts = terms_map.sum(axis=0)

        # Build a structure that holds:
        # * the term
        # * how many times it was found
        # * the sentences it was found on
        # To get the sentences, we use the non-zero elements of the
        # column with the term's index
        terms_frequencies = {
            term: {
                'count': int(terms_counts[0, index]),
                'sentences': list(sentences[terms_map[:, index].nonzero()[0]])
            }
            for term, index in vectorizer.vocabulary_.items()
        }
        return terms_frequencies
